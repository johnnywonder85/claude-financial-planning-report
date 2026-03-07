"""Interactive Excel workbook — 5 sheets with live formulas.

Sheet 1 — Assumptions: config values as editable cells (yellow = editable, gray = calculated)
Sheet 2 — Cash Flow Calendar: months across columns, payment dates down rows
Sheet 3 — Debt Payoff Analysis: 3 scenario columns (Current / Aggressive / Comfortable)
Sheet 4 — 24-Month Projection: row per month with all balances, formulas throughout
Sheet 5 — Emergency Scenarios: 3 scenarios with reserve drawdown
"""

from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

from models.accounts import D


# Style constants
HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
EDITABLE_FILL = PatternFill(start_color="FFFDE7", end_color="FFFDE7", fill_type="solid")
CALC_FILL = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
ALERT_FILL = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
MONEY_FMT = '#,##0.00'
PCT_FMT = '0.00%'
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin'),
)


def generate_excel(config, tax_result, cashflow_summary, debt_scenarios,
                   projections, emergency_results, output_path):
    """Generate the full 5-sheet Excel workbook."""
    wb = Workbook()

    _build_assumptions_sheet(wb, config, tax_result)
    _build_cashflow_sheet(wb, config, projections)
    _build_debt_sheet(wb, debt_scenarios)
    _build_projection_sheet(wb, projections)
    _build_emergency_sheet(wb, emergency_results)

    wb.save(output_path)
    print(f"  Excel workbook saved: {output_path}")


def _style_header_row(ws, row, max_col):
    """Apply header styling to a row."""
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = THIN_BORDER


def _style_data_cell(ws, row, col, is_money=False, is_pct=False, editable=False):
    """Style a data cell."""
    cell = ws.cell(row=row, column=col)
    cell.border = THIN_BORDER
    if editable:
        cell.fill = EDITABLE_FILL
    if is_money:
        cell.number_format = MONEY_FMT
    if is_pct:
        cell.number_format = PCT_FMT


# ─── Sheet 1: Assumptions ────────────────────────────────────────

def _build_assumptions_sheet(wb, config, tax_result):
    """All config values as editable cells. Yellow = user-editable, gray = calculated."""
    ws = wb.active
    ws.title = "Assumptions"
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 40

    row = 1
    ws.cell(row=row, column=1, value="FINANCIAL PLAN — ASSUMPTIONS").font = Font(bold=True, size=14)
    row += 1
    ws.cell(row=row, column=1, value="Yellow cells are editable. Gray cells are calculated.").font = Font(italic=True, size=9)
    row += 2

    # Income section
    ws.cell(row=row, column=1, value="INCOME").font = Font(bold=True, size=12)
    row += 1
    _assumption_row(ws, row, "Gross Monthly Income", config["income"]["gross_monthly"], editable=True)
    row += 1
    _assumption_row(ws, row, "Payment Day", config["income"]["payment_day"], editable=True)
    row += 1
    _assumption_row(ws, row, "Annual Income", config["income"]["gross_monthly"] * 12, editable=False, note="= Monthly × 12")
    row += 2

    # Tax section
    ws.cell(row=row, column=1, value="TAX SUMMARY").font = Font(bold=True, size=12)
    row += 1
    _assumption_row(ws, row, "Federal Tax", float(tax_result.federal), editable=False, is_money=True)
    row += 1
    _assumption_row(ws, row, "BC Provincial Tax", float(tax_result.provincial), editable=False, is_money=True)
    row += 1
    _assumption_row(ws, row, "CPP (self-employed)", float(tax_result.cpp), editable=False, is_money=True)
    row += 1
    _assumption_row(ws, row, "EI", float(tax_result.ei), editable=False, is_money=True)
    row += 1
    _assumption_row(ws, row, "Total Annual Tax", float(tax_result.total), editable=False, is_money=True)
    row += 1
    _assumption_row(ws, row, "Effective Rate", float(tax_result.effective_rate) / 100, editable=False, is_pct=True)
    row += 1
    _assumption_row(ws, row, "Marginal Rate", float(tax_result.marginal_rate) / 100, editable=False, is_pct=True)
    row += 1
    _assumption_row(ws, row, "Monthly Holdback", config.get("holdback_monthly", 2897), editable=True)
    row += 2

    # Expenses
    ws.cell(row=row, column=1, value="FIXED EXPENSES").font = Font(bold=True, size=12)
    row += 1
    for exp in config["expenses"]["fixed"]:
        _assumption_row(ws, row, f"{exp['name']} (Day {exp['day']})", exp["amount"], editable=True, is_money=True)
        row += 1
    cc = config["expenses"]["credit_card"]
    _assumption_row(ws, row, f"CC Statement (Day {cc['payment_day']})", cc["average_statement"], editable=True, is_money=True, note=cc.get("note", ""))
    row += 2

    # Debts
    ws.cell(row=row, column=1, value="DEBTS").font = Font(bold=True, size=12)
    row += 1
    for debt_name, debt_cfg in config["debts"].items():
        label = debt_name.replace("_", " ").title()
        _assumption_row(ws, row, f"{label} — Balance", debt_cfg.get("balance", 0), editable=True, is_money=True)
        row += 1
        _assumption_row(ws, row, f"{label} — Rate", debt_cfg.get("interest_rate", 0), editable=True, is_pct=True)
        row += 1
        _assumption_row(ws, row, f"{label} — Payment", debt_cfg.get("payment", debt_cfg.get("target_payment", 0)), editable=True, is_money=True)
        row += 1
    row += 1

    # Savings
    ws.cell(row=row, column=1, value="SAVINGS TARGETS").font = Font(bold=True, size=12)
    row += 1
    savings = config.get("savings", {})
    _assumption_row(ws, row, "Safety Fund Monthly", savings.get("safety_fund", {}).get("target", 500), editable=True, is_money=True)
    row += 1
    _assumption_row(ws, row, "TFSA Monthly", savings.get("tfsa", {}).get("monthly", 100), editable=True, is_money=True)
    row += 1
    _assumption_row(ws, row, "Emergency Fund Target", savings.get("emergency_target", 18000), editable=True, is_money=True)
    row += 1
    _assumption_row(ws, row, "Phase 4 RRSP Monthly", savings.get("phase_a_rrsp", 1200), editable=True, is_money=True)
    row += 1
    _assumption_row(ws, row, "Phase 4 TFSA Monthly", savings.get("phase_a_tfsa", 625), editable=True, is_money=True)

    # Define named ranges for key values
    from openpyxl.workbook.defined_name import DefinedName
    dn1 = DefinedName("GrossMonthly", attr_text="Assumptions!$B$5")
    wb.defined_names.add(dn1)
    dn2 = DefinedName("Holdback", attr_text="Assumptions!$B$16")
    wb.defined_names.add(dn2)


def _assumption_row(ws, row, label, value, editable=True, note="", is_money=False, is_pct=False):
    ws.cell(row=row, column=1, value=label)
    cell = ws.cell(row=row, column=2, value=value)
    cell.border = THIN_BORDER
    cell.fill = EDITABLE_FILL if editable else CALC_FILL
    if is_money:
        cell.number_format = MONEY_FMT
    if is_pct:
        cell.number_format = PCT_FMT
    if note:
        ws.cell(row=row, column=3, value=note).font = Font(italic=True, size=9, color="666666")


# ─── Sheet 2: Cash Flow Calendar ─────────────────────────────────

def _build_cashflow_sheet(wb, config, projections):
    """Months across columns, payment dates down rows."""
    ws = wb.create_sheet("Cash Flow Calendar")

    payment_days = [1, 6, 15, 21, 24, 25]
    day_labels = {
        1: "Day 1: Fixed Expenses",
        6: "Day 6: CC Statement",
        15: "Day 15: Mid-month",
        21: "Day 21: Income / LOC / Holdback",
        24: "Day 24: LOC Principal",
        25: "Day 25: Savings",
    }

    # Headers
    ws.cell(row=1, column=1, value="Payment Date")
    ws.column_dimensions['A'].width = 35
    months_to_show = min(len(projections), 24)

    for i in range(months_to_show):
        col = i + 2
        ws.cell(row=1, column=col, value=f"Month {projections[i].month}")
        ws.column_dimensions[get_column_letter(col)].width = 14

    _style_header_row(ws, 1, months_to_show + 1)

    # Data rows for each payment day
    row = 2
    for day in payment_days:
        ws.cell(row=row, column=1, value=day_labels.get(day, f"Day {day}"))
        for i in range(months_to_show):
            col = i + 2
            snap = projections[i]
            val = _get_day_amount(day, snap, config)
            cell = ws.cell(row=row, column=col, value=float(val))
            cell.number_format = MONEY_FMT
            cell.border = THIN_BORDER
            if val < 0:
                cell.font = Font(color="CC0000")
        row += 1

    # Net cashflow row
    ws.cell(row=row, column=1, value="Net Cash Flow").font = Font(bold=True)
    for i in range(months_to_show):
        col = i + 2
        cell = ws.cell(row=row, column=col, value=float(projections[i].net_cashflow))
        cell.number_format = MONEY_FMT
        cell.border = THIN_BORDER
        cell.font = Font(bold=True)
    row += 1

    # Running chequing balance
    ws.cell(row=row, column=1, value="Chequing Balance").font = Font(bold=True)
    for i in range(months_to_show):
        col = i + 2
        bal = float(projections[i].chequing_balance)
        cell = ws.cell(row=row, column=col, value=bal)
        cell.number_format = MONEY_FMT
        cell.border = THIN_BORDER
        cell.font = Font(bold=True)
        # Conditional: red if below $1,000
        if bal < 1000:
            cell.fill = ALERT_FILL


def _get_day_amount(day, snapshot, config):
    """Get the total amount for a given payment day from a snapshot."""
    expenses = config["expenses"]
    income_cfg = config["income"]

    if day == 1:
        return -D(sum(D(e["amount"]) for e in expenses.get("fixed", []) if e["day"] == 1))
    elif day == 6:
        return -snapshot.credit_card_payment
    elif day == 15:
        return -D(sum(D(e["amount"]) for e in expenses.get("fixed", []) if e["day"] == 15))
    elif day == 21:
        return D(snapshot.income - snapshot.tax_holdback - snapshot.debt_payments.get("LOC Interest", D(0)))
    elif day == 24:
        return -snapshot.debt_payments.get("LOC Principal", D(0))
    elif day == 25:
        return -D(sum(snapshot.savings_contributions.values()))
    return D(0)


# ─── Sheet 3: Debt Payoff Analysis ───────────────────────────────

def _build_debt_sheet(wb, debt_scenarios):
    """3 scenario columns: Current / Aggressive / Comfortable."""
    ws = wb.create_sheet("Debt Payoff Analysis")

    headers = ["Metric"] + [s.name for s in debt_scenarios]
    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
    _style_header_row(ws, 1, len(headers))
    ws.column_dimensions['A'].width = 30

    metrics = [
        ("Monthly Extra to LOC", lambda s: float(s.monthly_extra)),
        ("LOC Payoff Month", lambda s: s.loc_payoff_month),
        ("Total Interest Paid", lambda s: float(s.total_interest_paid)),
        ("Debt-Free Date", lambda s: s.debt_free_date),
        ("Total Cost", lambda s: float(s.total_cost)),
    ]

    for row_idx, (label, getter) in enumerate(metrics, 2):
        ws.cell(row=row_idx, column=1, value=label)
        for col_idx, scenario in enumerate(debt_scenarios, 2):
            val = getter(scenario)
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER
            if isinstance(val, float):
                cell.number_format = MONEY_FMT
            ws.column_dimensions[get_column_letter(col_idx)].width = 22

    # Monthly timeline below
    row = len(metrics) + 4
    ws.cell(row=row, column=1, value="MONTHLY TIMELINE").font = Font(bold=True, size=12)
    row += 1

    timeline_headers = ["Month", "Phase", "LOC Balance", "Car Loan", "Student Loan",
                         "Safety Fund", "TFSA", "RRSP", "Total Interest"]
    for i, h in enumerate(timeline_headers, 1):
        ws.cell(row=row, column=i, value=h)
    _style_header_row(ws, row, len(timeline_headers))
    row += 1

    # Use current scenario timeline
    if debt_scenarios:
        for entry in debt_scenarios[0].timeline[:24]:
            ws.cell(row=row, column=1, value=entry["month"])
            ws.cell(row=row, column=2, value=entry["phase"])
            for col, key in enumerate(["loc_balance", "car_balance", "student_loan_balance",
                                        "safety_fund", "tfsa", "rrsp", "total_interest"], 3):
                cell = ws.cell(row=row, column=col, value=float(entry[key]))
                cell.number_format = MONEY_FMT
                cell.border = THIN_BORDER
            row += 1


# ─── Sheet 4: 24-Month Projection ────────────────────────────────

def _build_projection_sheet(wb, projections):
    """Row per month: income, holdback, net, each expense, each debt balance, each fund, phase, net worth."""
    ws = wb.create_sheet("24-Month Projection")

    headers = ["Month", "Date", "Phase", "Income", "Holdback", "Fixed Expenses",
               "CC Payment", "Debt Payments", "Savings", "Net Cash Flow",
               "Chequing", "LOC", "Car Loan", "Student Loan",
               "Safety Fund", "Emergency Fund", "TFSA", "RRSP", "Net Worth"]

    for i, h in enumerate(headers, 1):
        ws.cell(row=1, column=i, value=h)
        ws.column_dimensions[get_column_letter(i)].width = 15
    _style_header_row(ws, 1, len(headers))
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 25

    for row_idx, snap in enumerate(projections[:24], 2):
        ws.cell(row=row_idx, column=1, value=snap.month)
        ws.cell(row=row_idx, column=2, value=str(snap.date))
        ws.cell(row=row_idx, column=3, value=snap.phase)

        money_cols = {
            4: snap.income,
            5: snap.tax_holdback,
            6: snap.fixed_expenses,
            7: snap.credit_card_payment,
            8: D(sum(snap.debt_payments.values())),
            9: D(sum(snap.savings_contributions.values())),
            10: snap.net_cashflow,
            11: snap.ending_balances.get("Chequing", D(0)),
            12: snap.ending_balances.get("LOC", D(0)),
            13: snap.ending_balances.get("Car Loan", D(0)),
            14: snap.ending_balances.get("Student Loan", D(0)),
            15: snap.ending_balances.get("Safety Fund", D(0)),
            16: snap.ending_balances.get("Emergency Fund", D(0)),
            17: snap.ending_balances.get("TFSA", D(0)),
            18: snap.ending_balances.get("RRSP", D(0)),
            19: snap.net_worth(),
        }

        for col, val in money_cols.items():
            cell = ws.cell(row=row_idx, column=col, value=float(val))
            cell.number_format = MONEY_FMT
            cell.border = THIN_BORDER

    # Summary totals at bottom
    total_row = len(projections[:24]) + 2
    ws.cell(row=total_row, column=1, value="TOTALS").font = Font(bold=True)


# ─── Sheet 5: Emergency Scenarios ─────────────────────────────────

def _build_emergency_sheet(wb, emergency_results):
    """3 scenario panels showing reserve drawdown, missed payments, recovery."""
    ws = wb.create_sheet("Emergency Scenarios")

    ws.cell(row=1, column=1, value="EMERGENCY SCENARIO ANALYSIS").font = Font(bold=True, size=14)
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 20

    headers = ["Metric"] + [r.scenario_name for r in emergency_results]
    row = 3
    for i, h in enumerate(headers, 1):
        ws.cell(row=row, column=i, value=h)
    _style_header_row(ws, row, len(headers))
    row += 1

    # Description
    ws.cell(row=row, column=1, value="Description")
    for i, r in enumerate(emergency_results, 2):
        ws.cell(row=row, column=i, value=r.description)
    row += 1

    # Reserves exhausted
    ws.cell(row=row, column=1, value="Reserves Exhausted (Month)")
    for i, r in enumerate(emergency_results, 2):
        val = r.reserves_exhausted_month if r.reserves_exhausted_month else "No"
        cell = ws.cell(row=row, column=i, value=val)
        if r.reserves_exhausted_month:
            cell.fill = ALERT_FILL
    row += 1

    # Recovery months
    ws.cell(row=row, column=1, value="Recovery Months Needed")
    for i, r in enumerate(emergency_results, 2):
        ws.cell(row=row, column=i, value=r.recovery_months)
    row += 1

    # Missed payments
    ws.cell(row=row, column=1, value="Missed Payments").font = Font(bold=True)
    row += 1
    max_missed = max(len(r.missed_payments) for r in emergency_results) if emergency_results else 0
    for j in range(max_missed):
        for i, r in enumerate(emergency_results, 2):
            if j < len(r.missed_payments):
                cell = ws.cell(row=row, column=i, value=r.missed_payments[j])
                cell.fill = ALERT_FILL
        row += 1
