"""Professional PDF Report — ReportLab platypus flowables.

Clean professional style: navy headers, light gray alternating table rows, minimal color accents.
Built with ReportLab platypus flowables (no HTML intermediary — prevents artifact issues).

Pages:
1. Title Page — "Debt Elimination & Wealth Building Plan", date, client summary
2. Executive Summary — 1-page key numbers: net worth, debt-free date, effective tax rate, monthly surplus, phase timeline
3. Current Financial Position — Assets/debts table from TB, net worth calculation
4. Cash Flow Calendar — Day-by-day typical month, running balance, buffer analysis
5. Three-Phase Strategy — Phase descriptions with timeline, milestones, monthly allocations
6. Windfall Decision Framework — Decision tree as formatted table
7. 24-Month Projection — Condensed month-by-month table (key columns only)
8. Post-Debt Wealth Projection — RRSP/TFSA growth, tax refund compounding, 5-year outlook
"""

from decimal import Decimal
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)

from models.accounts import D


# Color palette
NAVY = colors.HexColor("#1F4E79")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MEDIUM_GRAY = colors.HexColor("#E0E0E0")
DARK_TEXT = colors.HexColor("#333333")
ACCENT_GREEN = colors.HexColor("#2E7D32")


def generate_pdf(config, tax_result, cashflow_summary, debt_scenarios,
                 projections, emergency_results, accounts, output_path):
    """Generate the full professional PDF report."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = _build_styles()
    story = []

    # 1. Title Page
    _add_title_page(story, styles, config)

    # 2. Executive Summary
    _add_executive_summary(story, styles, config, tax_result, debt_scenarios, projections)

    # 3. Current Financial Position
    _add_financial_position(story, styles, accounts, config)

    # 4. Cash Flow Calendar
    _add_cashflow_page(story, styles, cashflow_summary, config)

    # 5. Strategy Phases
    _add_strategy_page(story, styles, config, debt_scenarios)

    # 6. Windfall Decision Framework
    _add_windfall_page(story, styles, config)

    # 7. 24-Month Projection
    _add_projection_page(story, styles, projections)

    # 8. Post-Debt Wealth Projection
    _add_wealth_projection(story, styles, config, tax_result, projections)

    doc.build(story)
    print(f"  PDF report saved: {output_path}")


def _build_styles():
    """Build custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='TitleMain',
        parent=styles['Title'],
        fontSize=28,
        textColor=NAVY,
        spaceAfter=20,
        alignment=1,  # center
    ))
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=DARK_TEXT,
        spaceAfter=10,
        alignment=1,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=NAVY,
        spaceBefore=20,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name='SubSection',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_TEXT,
        spaceAfter=6,
        leading=14,
    ))
    return styles


def _make_table(data, col_widths=None, has_header=True):
    """Reusable table helper for consistent styling across all tables."""
    table = Table(data, colWidths=col_widths)

    style_commands = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK_TEXT),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
    ]

    if has_header:
        style_commands.extend([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
        ])

    # Alternating row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))

    table.setStyle(TableStyle(style_commands))
    return table


def _fmt(val):
    """Format a Decimal/float as currency string."""
    if isinstance(val, (Decimal, float, int)):
        return f"${float(val):,.2f}"
    return str(val)


# ─── Page builders ────────────────────────────────────────────────

def _add_title_page(story, styles, config):
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Debt Elimination &<br/>Wealth Building Plan", styles['TitleMain']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="60%", thickness=2, color=NAVY))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Prepared: {date.today().strftime('%B %d, %Y')}", styles['Subtitle']))
    story.append(Paragraph("Self-Employed Contractor — Vancouver, BC", styles['Subtitle']))
    story.append(Paragraph(f"Annual Gross Income: $120,000", styles['Subtitle']))
    story.append(PageBreak())


def _add_executive_summary(story, styles, config, tax_result, debt_scenarios, projections):
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    # Key numbers
    current = debt_scenarios[0] if debt_scenarios else None

    data = [
        ["Metric", "Value"],
        ["Annual Gross Income", "$120,000"],
        ["Total Annual Tax", _fmt(tax_result.total)],
        ["Effective Tax Rate", f"{tax_result.effective_rate:.1f}%"],
        ["Marginal Tax Rate", f"{tax_result.marginal_rate:.1f}%"],
        ["Monthly Holdback", _fmt(config.get("holdback_monthly", 2897))],
    ]

    if current:
        data.extend([
            ["LOC Payoff Month", str(current.loc_payoff_month)],
            ["Debt-Free Date", current.debt_free_date],
            ["Total Interest Paid", _fmt(current.total_interest_paid)],
        ])

    if projections:
        last = projections[min(23, len(projections) - 1)]
        data.append(["Net Worth (Month 24)", _fmt(last.net_worth())])

    table = _make_table(data, col_widths=[3.5 * inch, 3 * inch])
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    # Phase timeline summary
    story.append(Paragraph("Strategy Timeline", styles['SubSection']))
    phases = config.get("strategy", {}).get("phases", [])
    for p in phases:
        story.append(Paragraph(
            f"<b>{p['name']}</b> (Months {p['months']}): {p['description']}",
            styles['BodyText2']
        ))
    story.append(PageBreak())


def _add_financial_position(story, styles, accounts, config):
    story.append(Paragraph("Current Financial Position", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    data = [["Account", "Type", "Balance"]]
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")

    for a in sorted(accounts, key=lambda x: x.account_type):
        bal_str = _fmt(a.balance)
        if a.account_type == "Liability":
            bal_str = f"-{_fmt(a.balance)}"
            total_liabilities += a.balance
        elif a.account_type == "Asset":
            total_assets += a.balance
        data.append([a.name, a.account_type, bal_str])

    data.append(["", "", ""])
    data.append(["Total Assets", "", _fmt(total_assets)])
    data.append(["Total Liabilities", "", f"-{_fmt(total_liabilities)}"])
    data.append(["Net Worth", "", _fmt(total_assets - total_liabilities)])

    table = _make_table(data, col_widths=[2.5 * inch, 2 * inch, 2 * inch])
    story.append(table)
    story.append(PageBreak())


def _add_cashflow_page(story, styles, cashflow_summary, config):
    story.append(Paragraph("Cash Flow Calendar", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(
        "Typical month cash flow pattern. The $5,000 chequing buffer is critical: "
        "expenses hit Days 1-6 but income arrives Day 21.",
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.1 * inch))

    data = [["Day", "Events", "Amount"]]
    for day, desc, amount in cashflow_summary["rows"]:
        data.append([day, desc, amount])

    data.append(["", "", ""])
    data.append(["", "Day 1 Total Outflows", f"-${cashflow_summary['day1_total']:,.2f}"])
    data.append(["", "Day 6 CC Statement", f"-${cashflow_summary['day6_total']:,.2f}"])
    data.append(["", "Monthly Fixed Outflows", f"-${cashflow_summary['monthly_fixed_outflows']:,.2f}"])

    table = _make_table(data, col_widths=[1 * inch, 3.5 * inch, 2 * inch])
    story.append(table)

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        "<b>Buffer Analysis:</b> Day 1 outflows of ~$3,081 plus Day 6 CC payment of $1,750 total "
        "~$5,146 before any income arrives on Day 21. A $5,000 opening balance provides adequate buffer.",
        styles['BodyText2']
    ))
    story.append(PageBreak())


def _add_strategy_page(story, styles, config, debt_scenarios):
    story.append(Paragraph("Debt Elimination Strategy", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    phases = config.get("strategy", {}).get("phases", [])
    for p in phases:
        story.append(Paragraph(f"<b>{p['name']}</b>", styles['SubSection']))
        story.append(Paragraph(f"Months: {p['months']}", styles['BodyText2']))
        story.append(Paragraph(p['description'], styles['BodyText2']))
        story.append(Spacer(1, 0.1 * inch))

    # Scenario comparison
    if debt_scenarios:
        story.append(Paragraph("Scenario Comparison", styles['SubSection']))
        data = [["", "Current Plan", "Aggressive", "Comfortable"]]
        metrics = [
            ("Monthly Extra to LOC", [_fmt(s.monthly_extra) for s in debt_scenarios]),
            ("LOC Payoff Month", [str(s.loc_payoff_month) for s in debt_scenarios]),
            ("Total Interest", [_fmt(s.total_interest_paid) for s in debt_scenarios]),
            ("Debt-Free Date", [s.debt_free_date for s in debt_scenarios]),
        ]
        for label, values in metrics:
            row = [label] + values[:3]
            while len(row) < 4:
                row.append("")
            data.append(row)

        table = _make_table(data, col_widths=[2 * inch, 1.7 * inch, 1.7 * inch, 1.7 * inch])
        story.append(table)

    story.append(PageBreak())


def _add_windfall_page(story, styles, config):
    story.append(Paragraph("Windfall Decision Framework", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(
        "When unexpected income arrives (tax refund, bonus, side project), use this decision tree:",
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.1 * inch))

    rules = config.get("windfall_rules", [])
    data = [["Priority", "Condition", "Action"]]
    for i, rule in enumerate(rules, 1):
        # Parse "If X → Y" format
        parts = rule.split("→")
        if len(parts) == 2:
            condition = parts[0].replace("If ", "").strip()
            action = parts[1].strip()
        else:
            condition = rule
            action = ""
        data.append([str(i), condition, action])

    table = _make_table(data, col_widths=[0.8 * inch, 3 * inch, 3 * inch])
    story.append(table)
    story.append(PageBreak())


def _add_projection_page(story, styles, projections):
    story.append(Paragraph("24-Month Projection", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.1 * inch))

    data = [["Mo", "Phase", "Income", "Holdback", "Expenses", "LOC",
             "Car", "S.Loan", "Net Worth"]]

    for snap in projections[:24]:
        phase_short = snap.phase.split(":")[0] if ":" in snap.phase else snap.phase
        total_expenses = D(snap.fixed_expenses + snap.credit_card_payment)
        data.append([
            str(snap.month),
            phase_short,
            _fmt(snap.income),
            _fmt(snap.tax_holdback),
            _fmt(total_expenses),
            _fmt(snap.ending_balances.get("LOC", D(0))),
            _fmt(snap.ending_balances.get("Car Loan", D(0))),
            _fmt(snap.ending_balances.get("Student Loan", D(0))),
            _fmt(snap.net_worth()),
        ])

    widths = [0.4 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch,
              0.8 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch]
    table = _make_table(data, col_widths=widths)
    story.append(table)
    story.append(PageBreak())


def _add_wealth_projection(story, styles, config, tax_result, projections):
    story.append(Paragraph("Post-Debt Wealth Projection", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    savings = config.get("savings", {})
    rrsp_monthly = D(savings.get("phase_a_rrsp", 1200))
    tfsa_monthly = D(savings.get("phase_a_tfsa", 625))
    marginal = tax_result.marginal_rate

    story.append(Paragraph(
        f"Once debt-free (Phase 4), monthly wealth building: "
        f"RRSP ${rrsp_monthly:,.0f}/mo + TFSA ${tfsa_monthly:,.0f}/mo",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        f"RRSP tax refund at {marginal:.1f}% marginal rate: "
        f"~${float(rrsp_monthly * 12 * marginal / 100):,.0f}/year reinvested",
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 5-year projection table (simplified compound growth)
    growth_rate = Decimal("0.06")  # Assumed 6% annual growth
    data = [["Year", "RRSP Balance", "TFSA Balance", "Combined", "Tax Refund"]]

    rrsp_bal = D(0)
    tfsa_bal = D(0)

    for year in range(1, 6):
        annual_rrsp = rrsp_monthly * 12
        annual_tfsa = tfsa_monthly * 12
        refund = D(annual_rrsp * marginal / 100)

        rrsp_bal = D((rrsp_bal + annual_rrsp + refund) * (1 + growth_rate))
        tfsa_bal = D((tfsa_bal + annual_tfsa) * (1 + growth_rate))

        data.append([
            f"Year {year}",
            _fmt(rrsp_bal),
            _fmt(tfsa_bal),
            _fmt(rrsp_bal + tfsa_bal),
            _fmt(refund),
        ])

    table = _make_table(data, col_widths=[1 * inch, 1.7 * inch, 1.7 * inch, 1.7 * inch, 1.3 * inch])
    story.append(table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "<i>Assumes 6% annual portfolio growth. RRSP refund calculated at marginal rate and reinvested. "
        "TFSA grows tax-free. Actual returns will vary.</i>",
        styles['BodyText2']
    ))
