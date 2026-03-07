"""24-Month Projections + Emergency Scenarios.

generate_projection(months, opening_balances, config):
- Iterates month-by-month: tax → cashflow → debt payments → savings → update balances
- Returns list of MonthlySnapshot with all account balances
- Tracks phase transitions and milestones

Emergency scenarios:
- Delayed payment (1 month): Income arrives Month N+1 instead of N
- Contract loss (2 months): Zero income for 2 months
- Contract loss (4 months): Worst case
"""

from decimal import Decimal
from datetime import date
from models.accounts import D, MonthlySnapshot, EmergencyResult
from models.tax import calculate_total_tax
from models.debt import _determine_phase, _is_balloon_due, _add_months


def generate_projection(months, opening_balances, config):
    """Generate month-by-month projection.

    Args:
        months: number of months to project
        opening_balances: dict of account name -> Decimal balance
        config: full config dict

    Returns:
        list of MonthlySnapshot
    """
    debts = config["debts"]
    income_cfg = config["income"]
    expenses_cfg = config["expenses"]
    savings_cfg = config.get("savings", {})

    # Initialize balances
    balances = {k: D(v) for k, v in opening_balances.items()}

    # Ensure all expected keys exist
    for key in ["Chequing", "LOC", "Car Loan", "Student Loan",
                 "Safety Fund", "Emergency Fund", "TFSA", "RRSP"]:
        if key not in balances:
            balances[key] = D(0)

    # Annual tax calculation for monthly holdback reference
    annual_income = D(income_cfg["gross_monthly"]) * 12
    tax_result = calculate_total_tax(annual_income, config)
    monthly_tax = D(tax_result.total / 12)
    configured_holdback = D(config.get("holdback_monthly", 2897))

    snapshots = []
    start_date = date.fromisoformat(config.get("start_date", "2026-01-01"))

    for m in range(1, months + 1):
        current_date = _add_months(start_date, m)
        income = D(income_cfg["gross_monthly"])

        # Phase determination
        phase = _determine_phase(
            balances["LOC"], balances["Car Loan"],
            balances["Safety Fund"], balances["Emergency Fund"],
            D(debts["car_loan"].get("balloon_amount", 10500)),
            D(savings_cfg.get("emergency_target", 18000)),
            m
        )

        # --- Fixed expenses ---
        fixed_total = D(0)
        for exp in expenses_cfg.get("fixed", []):
            fixed_total += D(exp["amount"])

        # --- Credit card ---
        cc = expenses_cfg.get("credit_card", {})
        cc_payment = D(cc.get("average_statement", 1750))

        # --- Debt payments ---
        debt_payments = {}
        extra_debt = D(0)

        # LOC
        loc_cfg = debts["loc"]
        if balances["LOC"] > 0:
            loc_interest = D(balances["LOC"] * Decimal(str(loc_cfg["interest_rate"])) / 12)
            loc_principal = min(D(loc_cfg.get("target_payment", 700)), balances["LOC"])
            debt_payments["LOC Interest"] = loc_interest
            debt_payments["LOC Principal"] = loc_principal
            balances["LOC"] = D(balances["LOC"] - loc_principal)
            extra_debt = loc_principal

        # Car Loan
        car_cfg = debts["car_loan"]
        if balances["Car Loan"] > 0:
            car_interest = D(balances["Car Loan"] * Decimal(str(car_cfg["interest_rate"])) / 12)
            car_payment_amt = D(car_cfg["payment"])

            if balances["Car Loan"] <= D(car_cfg["balloon_amount"]) and _is_balloon_due(m, config):
                # Balloon: final payment clears to nil
                debt_payments["Car Balloon"] = balances["Car Loan"]
                balances["Car Loan"] = D(0)
            else:
                principal = min(D(car_payment_amt - car_interest), balances["Car Loan"])
                debt_payments["Car Payment"] = car_payment_amt
                balances["Car Loan"] = D(balances["Car Loan"] - principal)

        # Student Loan
        sl_cfg = debts["student_loan"]
        if balances["Student Loan"] > 0:
            sl_pay = min(D(sl_cfg["payment"]), balances["Student Loan"])
            debt_payments["Student Loan"] = sl_pay
            balances["Student Loan"] = D(balances["Student Loan"] - sl_pay)

        # --- Savings ---
        savings_contributions = {}

        safety_amount = D(savings_cfg.get("safety_fund", {}).get("target", 500))
        tfsa_amount = D(savings_cfg.get("tfsa", {}).get("monthly", 100))

        if "Phase 1" in phase:
            savings_contributions["Safety Fund"] = safety_amount
            savings_contributions["TFSA"] = tfsa_amount
        elif "Phase 2" in phase:
            # Redirect LOC payments to safety fund for balloon
            redirect = D(loc_cfg.get("target_payment", 700))
            savings_contributions["Safety Fund"] = D(safety_amount + redirect)
            savings_contributions["TFSA"] = tfsa_amount
        elif "Phase 3" in phase:
            savings_contributions["Safety Fund"] = safety_amount
            savings_contributions["TFSA"] = tfsa_amount
            savings_contributions["RRSP"] = D(625)
            remaining = max(D(0), D(savings_cfg.get("emergency_target", 18000)) - balances["Emergency Fund"])
            savings_contributions["Emergency Fund"] = min(D(1140), remaining)
        elif "Phase 4" in phase:
            savings_contributions["Safety Fund"] = safety_amount
            savings_contributions["TFSA"] = D(savings_cfg.get("phase_a_tfsa", 625))
            savings_contributions["RRSP"] = D(savings_cfg.get("phase_a_rrsp", 1200))

        # Update fund balances
        for fund, amount in savings_contributions.items():
            if fund in balances:
                balances[fund] = D(balances[fund] + amount)

        # --- Chequing balance ---
        total_debt_payments = sum(debt_payments.values())
        total_savings = sum(savings_contributions.values())
        net = D(income - configured_holdback - fixed_total - cc_payment
                - total_debt_payments - total_savings)
        balances["Chequing"] = D(balances["Chequing"] + net)

        snapshot = MonthlySnapshot(
            month=m,
            date=current_date,
            income=income,
            tax_holdback=configured_holdback,
            fixed_expenses=fixed_total,
            debt_payments=dict(debt_payments),
            extra_debt_payment=extra_debt,
            savings_contributions=dict(savings_contributions),
            ending_balances=dict(balances),
            phase=phase,
            chequing_balance=balances["Chequing"],
            net_cashflow=net,
            credit_card_payment=cc_payment,
        )
        snapshots.append(snapshot)

    return snapshots


def run_emergency_scenarios(opening_balances, config):
    """Run all 3 emergency scenarios."""
    scenarios = []

    # Scenario A: Payment delayed 1 month
    scenarios.append(_run_delayed_payment(opening_balances, config))

    # Scenario B: Contract loss 2 months
    scenarios.append(_run_contract_loss(opening_balances, config, lost_months=2))

    # Scenario C: Contract loss 4 months
    scenarios.append(_run_contract_loss(opening_balances, config, lost_months=4))

    return scenarios


def _run_delayed_payment(opening_balances, config):
    """Scenario A: Income arrives Month N+1 instead of N.

    Shows chequing dip, whether LOC autopay gets missed.
    """
    # Modify config to delay first month's income
    import copy
    modified_config = copy.deepcopy(config)

    balances = {k: D(v) for k, v in opening_balances.items()}
    for key in ["Chequing", "LOC", "Car Loan", "Student Loan",
                 "Safety Fund", "Emergency Fund", "TFSA", "RRSP"]:
        if key not in balances:
            balances[key] = D(0)

    expenses_cfg = config["expenses"]
    debts = config["debts"]

    # Month 1: no income
    fixed_total = sum(D(e["amount"]) for e in expenses_cfg.get("fixed", []))
    cc_payment = D(expenses_cfg.get("credit_card", {}).get("average_statement", 1750))
    month1_outflows = D(fixed_total + cc_payment)
    balances["Chequing"] = D(balances["Chequing"] - month1_outflows)

    missed = []
    if balances["Chequing"] < 0:
        missed.append("Month 1: Chequing negative — LOC autopay may bounce")

    # Month 2: double income (delayed + current)
    income = D(config["income"]["gross_monthly"])
    holdback = D(config.get("holdback_monthly", 2897))
    balances["Chequing"] = D(balances["Chequing"] + income * 2 - holdback * 2
                              - month1_outflows)

    return EmergencyResult(
        scenario_name="Payment Delayed 1 Month",
        description="Income arrives Month 2 instead of Month 1. Shows chequing dip.",
        months=[],
        reserves_exhausted_month=None if balances["Chequing"] >= 0 else 1,
        missed_payments=missed,
        recovery_months=1 if missed else 0,
    )


def _run_contract_loss(opening_balances, config, lost_months):
    """Scenario B/C: Zero income for N months.

    Shows reserve drawdown, which debts miss payments, recovery path.
    """
    balances = {k: D(v) for k, v in opening_balances.items()}
    for key in ["Chequing", "LOC", "Car Loan", "Student Loan",
                 "Safety Fund", "Emergency Fund", "TFSA", "RRSP"]:
        if key not in balances:
            balances[key] = D(0)

    expenses_cfg = config["expenses"]
    fixed_total = sum(D(e["amount"]) for e in expenses_cfg.get("fixed", []))
    cc_min = D(500)  # Minimum CC payment in emergency
    monthly_min = D(fixed_total + cc_min)

    missed = []
    exhausted_month = None

    for m in range(1, lost_months + 1):
        # Draw from chequing first, then safety fund, then emergency fund
        remaining = monthly_min

        if balances["Chequing"] >= remaining:
            balances["Chequing"] = D(balances["Chequing"] - remaining)
            remaining = D(0)
        else:
            remaining = D(remaining - balances["Chequing"])
            balances["Chequing"] = D(0)

        if remaining > 0 and balances.get("Safety Fund", D(0)) > 0:
            draw = min(balances["Safety Fund"], remaining)
            balances["Safety Fund"] = D(balances["Safety Fund"] - draw)
            remaining = D(remaining - draw)

        if remaining > 0 and balances.get("Emergency Fund", D(0)) > 0:
            draw = min(balances["Emergency Fund"], remaining)
            balances["Emergency Fund"] = D(balances["Emergency Fund"] - draw)
            remaining = D(remaining - draw)

        if remaining > 0:
            if exhausted_month is None:
                exhausted_month = m
            missed.append(f"Month {m}: Cannot cover ${remaining:.2f} in expenses")

    # Recovery: how many months of income to rebuild
    total_drawn = monthly_min * lost_months
    income = D(config["income"]["gross_monthly"])
    holdback = D(config.get("holdback_monthly", 2897))
    surplus = D(income - holdback - monthly_min)
    recovery = 0
    if surplus > 0:
        recovery = int((total_drawn / surplus).quantize(Decimal("1"), rounding="ROUND_UP"))

    return EmergencyResult(
        scenario_name=f"Contract Loss ({lost_months} months)",
        description=f"Zero income for {lost_months} months. Shows reserve drawdown.",
        months=[],
        reserves_exhausted_month=exhausted_month,
        missed_payments=missed,
        recovery_months=recovery,
    )
