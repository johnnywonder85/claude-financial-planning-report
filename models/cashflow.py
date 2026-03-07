"""Cash Flow Calendar — builds day-by-day cash position for each month.

Tracks running chequing balance throughout month.
Flags if balance drops below configurable safety threshold.
The $5,000 chequing buffer is critical: expenses hit Days 1-6 but income arrives Day 21.
"""

from decimal import Decimal
from datetime import date
from calendar import monthrange
from models.accounts import D


DEFAULT_SAFETY_THRESHOLD = D(1000)


def build_monthly_cashflow(month_num, year, month, opening_chequing, config,
                           extra_loc_payment=Decimal("0"), phase="Phase 1"):
    """Build day-by-day cash flow for a single month.

    Returns dict with:
      - daily_events: list of (day, description, amount, running_balance)
      - closing_balance: Decimal
      - min_balance: Decimal (lowest point in month)
      - below_threshold: bool
      - total_outflows: Decimal
      - total_inflows: Decimal
    """
    income_cfg = config["income"]
    expenses_cfg = config["expenses"]
    debts_cfg = config["debts"]
    savings_cfg = config.get("savings", {})

    events = []  # (day, description, amount, running_balance)
    balance = D(opening_chequing)
    min_balance = balance
    total_outflows = D(0)
    total_inflows = D(0)

    # Collect all events by day
    day_events = {}  # day -> list of (description, amount)

    def add_event(day, desc, amount):
        if day not in day_events:
            day_events[day] = []
        day_events[day].append((desc, D(amount)))

    # --- Day 1: Fixed expenses ---
    for exp in expenses_cfg.get("fixed", []):
        if exp["day"] == 1:
            add_event(1, exp["name"], -D(exp["amount"]))

    # --- Day 6: Credit card statement ---
    cc = expenses_cfg.get("credit_card", {})
    if cc:
        add_event(cc.get("payment_day", 6),
                   "CC Statement (all discretionary)", -D(cc.get("average_statement", 1750)))

    # --- Day 15: Mid-month fixed ---
    for exp in expenses_cfg.get("fixed", []):
        if exp["day"] == 15:
            add_event(15, exp["name"], -D(exp["amount"]))

    # --- Day 21: Income + LOC autopay + tax holdback ---
    add_event(income_cfg.get("payment_day", 21),
              "Income", D(income_cfg.get("gross_monthly", 10000)))

    # LOC interest-only autopay (mandatory, Day 21)
    loc = debts_cfg.get("loc", {})
    if loc and loc.get("balance", 0) > 0:
        loc_balance = D(loc.get("balance", 6450))
        monthly_interest = D(loc_balance * Decimal(str(loc.get("interest_rate", 0.0449))) / 12)
        add_event(loc.get("autopay_day", 21),
                   "LOC Interest Autopay", -monthly_interest)

    # Tax holdback
    holdback = D(config.get("holdback_monthly", 2897))
    add_event(income_cfg.get("payment_day", 21),
              "Tax Holdback", -holdback)

    # --- Day 24: LOC voluntary principal ---
    if extra_loc_payment > 0:
        add_event(loc.get("voluntary_principal_day", 24),
                   "LOC Voluntary Principal", -extra_loc_payment)

    # --- Savings contributions ---
    safety = savings_cfg.get("safety_fund", {})
    if safety.get("target", 0) > 0:
        add_event(25, "Safety Fund", -D(safety["target"]))

    tfsa = savings_cfg.get("tfsa", {})
    if tfsa:
        add_event(25, "TFSA Contribution", -D(tfsa.get("monthly", 100)))

    # Phase-specific savings
    if phase == "Phase 4" or "Phase 4" in phase:
        rrsp_monthly = D(savings_cfg.get("phase_a_rrsp", 1200))
        tfsa_extra = D(savings_cfg.get("phase_a_tfsa", 625)) - D(tfsa.get("monthly", 100))
        if rrsp_monthly > 0:
            add_event(25, "RRSP Contribution", -rrsp_monthly)
        if tfsa_extra > 0:
            add_event(25, "TFSA Extra", -tfsa_extra)

    # Process events in day order
    num_days = monthrange(year, month)[1]
    for day in range(1, num_days + 1):
        if day in day_events:
            for desc, amount in day_events[day]:
                balance = D(balance + amount)
                if amount < 0:
                    total_outflows += abs(amount)
                else:
                    total_inflows += amount
                events.append((day, desc, amount, balance))
                if balance < min_balance:
                    min_balance = balance

    safety_threshold = D(config.get("safety_threshold", DEFAULT_SAFETY_THRESHOLD))

    return {
        "daily_events": events,
        "closing_balance": balance,
        "min_balance": min_balance,
        "below_threshold": min_balance < safety_threshold,
        "total_outflows": total_outflows,
        "total_inflows": total_inflows,
        "month_num": month_num,
    }


def get_typical_month_summary(config):
    """Return a summary table of a typical month's cash flow."""
    expenses = config["expenses"]
    fixed = expenses.get("fixed", [])
    cc = expenses.get("credit_card", {})

    day1_total = sum(D(e["amount"]) for e in fixed if e["day"] == 1)
    day6_total = D(cc.get("average_statement", 1750))
    day15_total = sum(D(e["amount"]) for e in fixed if e["day"] == 15)

    rows = []
    rows.append(("1", "Fixed expenses (rent, student loan, car, etc.)", f"-${day1_total:,.2f}"))
    rows.append(("6", f"CC statement (all discretionary)", f"-${day6_total:,.2f}"))
    rows.append(("15", "Mid-month fixed (car half 2)", f"-${day15_total:,.2f}"))
    rows.append(("21", "Income arrives, LOC autopay, tax holdback", f"+$10,000 net"))
    rows.append(("24", "LOC voluntary principal (~$700 target)", "-$700"))
    rows.append(("25", "Savings contributions", "varies by phase"))

    monthly_fixed = D(day1_total + day6_total + day15_total)

    return {
        "rows": rows,
        "day1_total": day1_total,
        "day6_total": day6_total,
        "day15_total": day15_total,
        "monthly_fixed_outflows": monthly_fixed,
    }
