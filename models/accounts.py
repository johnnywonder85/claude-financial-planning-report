"""Core data structures for financial planning model."""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional


# Decimal helper — all money uses Decimal with ROUND_HALF_UP
def D(value) -> Decimal:
    """Convert any numeric value to Decimal, rounded to 2 places."""
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Account:
    name: str
    account_type: str       # Asset, Liability, Equity, Revenue, Expense
    sub_type: str           # Cash, Investment, Debt, Fixed, Discretionary
    balance: Decimal        # Opening balance from TB
    tax_treatment: str = "N/A"      # TFSA, RRSP, Taxable, N/A
    liquidity: str = "Immediate"    # Immediate, 30-day, 2-week, Locked
    interest_rate: float = 0.0
    payment_day: int = 0
    debt_priority: int = 0          # 0 = not debt


@dataclass
class MonthlySnapshot:
    month: int
    date: date
    income: Decimal
    tax_holdback: Decimal
    fixed_expenses: Decimal
    debt_payments: dict  # dict[str, Decimal]
    extra_debt_payment: Decimal
    savings_contributions: dict  # dict[str, Decimal]
    ending_balances: dict  # dict[str, Decimal]
    phase: str
    chequing_balance: Decimal
    net_cashflow: Decimal
    credit_card_payment: Decimal = field(default_factory=lambda: Decimal("0"))

    def net_worth(self) -> Decimal:
        """Calculate net worth from ending balances."""
        assets = Decimal("0")
        liabilities = Decimal("0")
        for name, bal in self.ending_balances.items():
            if name in ("LOC", "Car Loan", "Student Loan"):
                liabilities += bal
            else:
                assets += bal
        return D(assets - liabilities)


@dataclass
class TaxResult:
    federal: Decimal
    provincial: Decimal
    cpp: Decimal
    ei: Decimal
    total: Decimal
    effective_rate: Decimal
    marginal_rate: Decimal
    donation_credit: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass
class DebtScenario:
    name: str
    monthly_extra: Decimal
    loc_payoff_month: int
    total_interest_paid: Decimal
    debt_free_date: str
    total_cost: Decimal
    timeline: list = field(default_factory=list)  # list of monthly snapshots


@dataclass
class EmergencyResult:
    scenario_name: str
    description: str
    months: list  # list of MonthlySnapshot showing drawdown
    reserves_exhausted_month: Optional[int] = None
    missed_payments: list = field(default_factory=list)
    recovery_months: int = 0
