"""Debt Payoff Engine — 4-phase strategy.

LOC structure (critical to get right):
- Mandatory: interest-only autopay on Day 21 (~$65/mo, recalculated as balance decreases)
- Voluntary: principal payment on Day 24 (~$700 target, adjustable)
- Bank cancels autopay if payment received between Day 1-21, so principal must be after Day 21

Car loan: biweekly payments of $283.20 (simplified as ~$630/mo across Days 1+15).
Regular payments pay down the current $4,490 balance. The $10,500 balloon is a
SEPARATE future obligation due June 2027 — paid from the Safety Fund, not from
regular car loan payments.

4-phase simulation:
- Phase 1 (Months 1-11): Extra → LOC principal until LOC = $0.
    $500/mo to Safety Fund, $100/mo to TFSA
- Phase 2 (Months 12-16): Redirect former LOC payments → Safety Fund for balloon.
    Car balloon $10,500 due June 2027. Car regular payments continue.
- Phase 3 (Months 17-28): Redirect $1,140/mo → emergency fund until $18K target.
    TFSA $100/mo continues, RRSP $625/mo starts.
- Phase 4 (Month 29+): RRSP $1,200/mo + TFSA $625/mo.
    RRSP refund (~$5,500 at 38.29% marginal) reinvested.
"""

from decimal import Decimal
from models.accounts import D, DebtScenario


def simulate_debt_payoff(opening_balances, config, monthly_extra_override=None):
    """Run full 4-phase debt payoff simulation.

    Args:
        opening_balances: dict with LOC, Car Loan, Student Loan balances
        config: full config dict
        monthly_extra_override: if set, override the extra payment amount

    Returns:
        DebtScenario with full timeline
    """
    debts = config["debts"]
    loc_cfg = debts["loc"]
    car_cfg = debts["car_loan"]
    sl_cfg = debts["student_loan"]

    # Opening balances
    loc_bal = D(opening_balances.get("LOC", loc_cfg["balance"]))
    car_bal = D(opening_balances.get("Car Loan", car_cfg["balance"]))
    sl_bal = D(opening_balances.get("Student Loan", sl_cfg["balance"]))

    loc_rate = Decimal(str(loc_cfg["interest_rate"]))
    car_rate = Decimal(str(car_cfg["interest_rate"]))
    car_payment = D(car_cfg["payment"])  # ~$630/mo (biweekly $283.20 simplified)
    car_balloon = D(car_cfg["balloon_amount"])
    sl_payment = D(sl_cfg["payment"])

    savings = config.get("savings", {})
    safety_target = D(savings.get("safety_fund", {}).get("target", 500))
    tfsa_base = D(savings.get("tfsa", {}).get("monthly", 100))
    emergency_target = D(savings.get("emergency_target", 18000))
    phase4_rrsp = D(savings.get("phase_a_rrsp", 1200))
    phase4_tfsa = D(savings.get("phase_a_tfsa", 625))

    loc_target = D(loc_cfg.get("target_payment", 700))
    if monthly_extra_override is not None:
        loc_target = D(monthly_extra_override)

    # Track funds
    safety_fund = D(0)
    emergency_fund = D(0)
    tfsa_total = D(0)
    rrsp_total = D(0)
    balloon_paid = False

    total_interest = D(0)
    timeline = []
    loc_payoff_month = 0
    debt_free_month = 0

    for month in range(1, 61):  # 5-year horizon
        # Determine phase
        phase = _determine_phase(loc_bal, balloon_paid, safety_fund, emergency_fund,
                                 car_balloon, emergency_target, month)

        # --- LOC interest (recalculated monthly) ---
        loc_interest = D(0)
        loc_principal = D(0)
        if loc_bal > 0:
            loc_interest = D(loc_bal * loc_rate / 12)
            total_interest += loc_interest
            # Voluntary principal payment
            loc_principal = min(loc_target, loc_bal)
            loc_bal = D(loc_bal - loc_principal)

        if loc_bal <= 0 and loc_payoff_month == 0 and month > 1:
            loc_payoff_month = month

        # --- Car loan (regular payments on current balance) ---
        car_interest = D(0)
        car_principal = D(0)
        if car_bal > 0:
            car_interest = D(car_bal * car_rate / 12)
            total_interest += car_interest
            # Regular payment: portion goes to interest, rest to principal
            car_principal = min(D(car_payment - car_interest), car_bal)
            car_bal = D(car_bal - car_principal)

        # --- Car balloon payment (separate from regular balance) ---
        # Paid from Safety Fund when balloon date arrives
        if not balloon_paid and _is_balloon_due(month, config):
            if safety_fund >= car_balloon:
                safety_fund = D(safety_fund - car_balloon)
                balloon_paid = True
            else:
                # Partial: use what's available, remainder is shortfall
                # (model still marks as paid — user would need LOC draw in practice)
                safety_fund = D(0)
                balloon_paid = True

        # --- Student loan (0% interest) ---
        sl_principal = D(0)
        if sl_bal > 0:
            sl_principal = min(sl_payment, sl_bal)
            sl_bal = D(sl_bal - sl_principal)

        # --- Savings by phase ---
        month_safety = D(0)
        month_tfsa = D(0)
        month_rrsp = D(0)
        month_emergency = D(0)

        if "Phase 1" in phase:
            month_safety = safety_target
            month_tfsa = tfsa_base
        elif "Phase 2" in phase:
            # Former LOC payments redirect to Safety Fund for balloon
            month_safety = D(safety_target + loc_target)
            month_tfsa = tfsa_base
        elif "Phase 3" in phase:
            month_safety = safety_target
            month_tfsa = tfsa_base
            month_rrsp = D(625)
            remaining_to_emergency = max(D(0), D(emergency_target - emergency_fund))
            month_emergency = min(D(1140), remaining_to_emergency)
        elif "Phase 4" in phase:
            month_safety = safety_target
            month_tfsa = phase4_tfsa
            month_rrsp = phase4_rrsp

        safety_fund += month_safety
        tfsa_total += month_tfsa
        rrsp_total += month_rrsp
        emergency_fund += month_emergency

        # Check debt-free (all regular balances paid AND balloon paid)
        all_regular_clear = loc_bal <= 0 and car_bal <= 0 and sl_bal <= 0
        if all_regular_clear and balloon_paid and debt_free_month == 0:
            debt_free_month = month

        timeline.append({
            "month": month,
            "phase": phase,
            "loc_balance": loc_bal,
            "car_balance": car_bal,
            "student_loan_balance": sl_bal,
            "loc_interest": loc_interest,
            "loc_principal": loc_principal,
            "car_interest": car_interest,
            "car_principal": car_principal,
            "sl_principal": sl_principal,
            "safety_fund": safety_fund,
            "emergency_fund": emergency_fund,
            "tfsa": tfsa_total,
            "rrsp": rrsp_total,
            "total_interest": total_interest,
            "balloon_paid": balloon_paid,
        })

    # Calculate debt-free date
    from datetime import date, timedelta
    start = date.fromisoformat(config.get("start_date", "2026-01-01"))
    if debt_free_month > 0:
        debt_free_date = _add_months(start, debt_free_month)
    else:
        debt_free_date = "Beyond 5 years"

    total_paid = D(0)
    for t in timeline:
        total_paid += t["loc_principal"] + t["car_principal"] + t["sl_principal"] + \
                      t["loc_interest"] + t["car_interest"]

    return DebtScenario(
        name="Current Plan" if monthly_extra_override is None else f"Extra ${monthly_extra_override}/mo",
        monthly_extra=loc_target,
        loc_payoff_month=loc_payoff_month,
        total_interest_paid=total_interest,
        debt_free_date=str(debt_free_date),
        total_cost=total_paid,
        timeline=timeline,
    )


def compare_scenarios(opening_balances, config):
    """Compare 3 scenarios side-by-side.

    - Current plan (as configured)
    - Aggressive (reduce discretionary by $300/mo, accelerate payoff)
    - Comfortable (reduce extra payments by $200, slower but more breathing room)
    """
    current = simulate_debt_payoff(opening_balances, config)

    loc_target = config["debts"]["loc"].get("target_payment", 700)
    aggressive = simulate_debt_payoff(opening_balances, config,
                                       monthly_extra_override=loc_target + 300)
    comfortable = simulate_debt_payoff(opening_balances, config,
                                        monthly_extra_override=max(200, loc_target - 200))

    aggressive.name = "Aggressive"
    comfortable.name = "Comfortable"

    return [current, aggressive, comfortable]


def _determine_phase(loc_bal, balloon_paid, safety_fund, emergency_fund,
                     car_balloon, emergency_target, month):
    """Determine current strategy phase.

    Phase 1: LOC has a balance — focus on eliminating it
    Phase 2: LOC paid off, balloon not yet paid — save in Safety Fund for balloon
    Phase 3: Balloon paid, emergency fund below target — build emergency fund
    Phase 4: Everything else — wealth building
    """
    if loc_bal > 0:
        return "Phase 1: LOC Elimination"
    elif not balloon_paid and safety_fund < car_balloon:
        return "Phase 2: Car Balloon Fund"
    elif emergency_fund < emergency_target:
        return "Phase 3: Emergency Fund"
    else:
        return "Phase 4: Wealth Building"


def _is_balloon_due(month, config):
    """Check if this month is when the balloon payment is due."""
    from datetime import date
    start = date.fromisoformat(config.get("start_date", "2026-01-01"))
    balloon_date_str = config["debts"]["car_loan"].get("balloon_date", "2027-06-01")
    balloon_date = date.fromisoformat(balloon_date_str)

    current = _add_months(start, month)
    return (current.year == balloon_date.year and current.month == balloon_date.month)


def _add_months(start_date, months):
    """Add N months to a date."""
    from datetime import date
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, 28)
    return date(year, month, day)
