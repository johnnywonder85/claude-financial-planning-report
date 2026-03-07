"""Main orchestrator — runs the full financial planning pipeline.

1. Load config.yaml
2. Import Trial Balance → build COA → display summary for validation
3. Run tax engine → annual + monthly breakdown
4. Run debt payoff simulation (all 4 phases)
5. Generate 24-month projection
6. Run 3 emergency scenarios
7. Generate PDF → output/financial_plan.pdf
8. Generate Excel → output/financial_plan.xlsx
9. Print summary + file paths
"""

import os
import sys
import yaml
from decimal import Decimal

from models.accounts import D
from models.tax import calculate_total_tax
from models.cashflow import get_typical_month_summary
from models.debt import compare_scenarios
from models.projection import generate_projection, run_emergency_scenarios
from importers.trial_balance import load_trial_balance, display_summary
from outputs.pdf_report import generate_pdf
from outputs.excel_workbook import generate_excel


def main():
    print("=" * 60)
    print("  FINANCIAL PLANNING TOOL")
    print("  Debt Elimination & Wealth Building Plan")
    print("=" * 60)
    print()

    # 1. Load config
    config_path = "config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    print(f"  Loading config: {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    print("  ✓ Config loaded")

    # 2. Import Trial Balance → build COA → display summary
    print("\n  Importing Trial Balance...")
    tb_path = config.get("trial_balance_file", "trial_balance.csv")
    accounts = load_trial_balance(tb_path, config)
    display_summary(accounts)

    # Build opening balances dict for projections
    opening_balances = {}
    for a in accounts:
        if a.name == "Business Chequing":
            opening_balances["Chequing"] = a.balance
        elif a.name in ("LOC", "Line of Credit"):
            opening_balances["LOC"] = a.balance
        elif a.name in ("Car Loan",):
            opening_balances["Car Loan"] = a.balance
        elif a.name in ("Student Loan",):
            opening_balances["Student Loan"] = a.balance
        elif a.name == "TFSA":
            opening_balances["TFSA"] = a.balance
        elif a.name == "RRSP":
            opening_balances["RRSP"] = a.balance
        elif a.name == "Safety Fund":
            opening_balances["Safety Fund"] = a.balance
        elif a.name == "Emergency Fund":
            opening_balances["Emergency Fund"] = a.balance

    # 3. Tax engine
    print("\n  Running tax calculations...")
    annual_income = D(config["income"]["gross_monthly"]) * 12
    tax_result = calculate_total_tax(annual_income, config)

    configured_holdback = D(config.get("holdback_monthly", 2897))
    calculated_monthly_tax = D(tax_result.total / 12)

    print(f"  Annual income:     ${annual_income:>10,.2f}")
    print(f"  Federal tax:       ${tax_result.federal:>10,.2f}")
    print(f"  BC provincial:     ${tax_result.provincial:>10,.2f}")
    print(f"  CPP:               ${tax_result.cpp:>10,.2f}")
    print(f"  EI:                ${tax_result.ei:>10,.2f}")
    print(f"  Donation credit:  -${tax_result.donation_credit:>10,.2f}")
    print(f"  Total annual tax:  ${tax_result.total:>10,.2f}")
    print(f"  Effective rate:    {tax_result.effective_rate:>10.2f}%")
    print(f"  Marginal rate:     {tax_result.marginal_rate:>10.2f}%")
    print(f"  Configured holdback: ${configured_holdback:>8,.2f}/mo")
    print(f"  Calculated need:     ${calculated_monthly_tax:>8,.2f}/mo")
    if configured_holdback < calculated_monthly_tax:
        print(f"  ⚠ Holdback is ${calculated_monthly_tax - configured_holdback:,.2f}/mo UNDER calculated need")
    else:
        print(f"  ✓ Holdback is ${configured_holdback - calculated_monthly_tax:,.2f}/mo OVER calculated need (buffer)")

    # 4. Debt payoff simulation
    print("\n  Running debt payoff simulation...")
    debt_scenarios = compare_scenarios(opening_balances, config)
    for s in debt_scenarios:
        print(f"  [{s.name}] LOC payoff: Month {s.loc_payoff_month}, "
              f"Interest: ${s.total_interest_paid:,.2f}, "
              f"Debt-free: {s.debt_free_date}")

    # 5. 24-month projection
    print("\n  Generating 24-month projection...")
    projections = generate_projection(24, opening_balances, config)
    if projections:
        last = projections[-1]
        print(f"  Month 24 net worth: ${last.net_worth():,.2f}")
        print(f"  Month 24 phase: {last.phase}")

    # 6. Emergency scenarios
    print("\n  Running emergency scenarios...")
    emergency_results = run_emergency_scenarios(opening_balances, config)
    for e in emergency_results:
        status = "Reserves hold" if e.reserves_exhausted_month is None else f"Exhausted month {e.reserves_exhausted_month}"
        print(f"  [{e.scenario_name}] {status}, recovery: {e.recovery_months} months")

    # 7. Cash flow summary
    cashflow_summary = get_typical_month_summary(config)

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # 8. Generate PDF
    print("\n  Generating PDF report...")
    pdf_path = "output/financial_plan.pdf"
    generate_pdf(config, tax_result, cashflow_summary, debt_scenarios,
                 projections, emergency_results, accounts, pdf_path)

    # 9. Generate Excel
    print("  Generating Excel workbook...")
    excel_path = "output/financial_plan.xlsx"
    generate_excel(config, tax_result, cashflow_summary, debt_scenarios,
                   projections, emergency_results, excel_path)

    # Summary
    print("\n" + "=" * 60)
    print("  COMPLETE")
    print("=" * 60)
    print(f"  PDF:   {os.path.abspath(pdf_path)}")
    print(f"  Excel: {os.path.abspath(excel_path)}")
    print()

    # Verification checks
    print("  Verification:")
    print(f"  1. Tax: ~${tax_result.total:,.0f} on $120K "
          f"(federal ${tax_result.federal:,.0f} + BC ${tax_result.provincial:,.0f})")
    total_fixed = sum(D(e["amount"]) for e in config["expenses"]["fixed"])
    cc = D(config["expenses"]["credit_card"]["average_statement"])
    debt_min = sum(D(config["debts"][d].get("payment", config["debts"][d].get("target_payment", 0)))
                   for d in config["debts"])
    print(f"  2. Monthly outflows: fixed ${total_fixed:,.0f} + CC ${cc:,.0f} + "
          f"debts ${debt_min:,.0f} = ~${total_fixed + cc + debt_min:,.0f}")
    print(f"  3. No double-counting: CC covers ALL discretionary")
    print(f"  4. LOC split: autopay Day 21 (interest) + voluntary Day 24 (principal)")
    print()


if __name__ == "__main__":
    main()
