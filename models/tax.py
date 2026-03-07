"""Canadian Tax Engine — Federal + BC + CPP + EI.

All brackets come from config.yaml, not hardcoded.
Clear distinction: effective rate vs marginal rate — labeled explicitly in all outputs.
"""

from decimal import Decimal
from models.accounts import D, TaxResult


def calculate_federal_tax(income, config):
    """Graduated bracket calculation with basic personal amount."""
    tax_cfg = config["tax"]
    brackets = tax_cfg["federal_brackets"]
    bpa = D(tax_cfg["basic_personal_amount"])

    taxable = max(D(income) - bpa, D(0))
    tax = Decimal("0")

    for bracket_size, rate in brackets:
        bracket_size = D(bracket_size)
        rate = Decimal(str(rate))
        if taxable <= 0:
            break
        taxed = min(taxable, bracket_size)
        tax += D(taxed * rate)
        taxable -= taxed

    return D(tax)


def calculate_bc_tax(income, config):
    """BC provincial brackets."""
    tax_cfg = config["tax"]
    brackets = tax_cfg["bc_brackets"]
    bpa = D(tax_cfg["bc_basic_personal_amount"])

    taxable = max(D(income) - bpa, D(0))
    tax = Decimal("0")

    for bracket_size, rate in brackets:
        bracket_size = D(bracket_size)
        rate = Decimal(str(rate))
        if taxable <= 0:
            break
        taxed = min(taxable, bracket_size)
        tax += D(taxed * rate)
        taxable -= taxed

    return D(tax)


def calculate_cpp(income, config):
    """Self-employed CPP — both employee + employer portions = 11.90%."""
    tax_cfg = config["tax"]
    cpp_cfg = tax_cfg["cpp"]
    rate = Decimal(str(cpp_cfg["rate"]))
    max_pensionable = D(cpp_cfg["max_pensionable"])
    basic_exemption = D(cpp_cfg["basic_exemption"])

    pensionable = min(D(income), max_pensionable) - basic_exemption
    if pensionable <= 0:
        return D(0)
    return D(pensionable * rate)


def calculate_ei(income, config):
    """EI — only if ei_opted_in: true in config."""
    tax_cfg = config["tax"]
    if not tax_cfg.get("ei_opted_in", False):
        return D(0)

    ei_cfg = tax_cfg["ei"]
    rate = Decimal(str(ei_cfg["rate"]))
    max_insurable = D(ei_cfg["max_insurable"])

    insurable = min(D(income), max_insurable)
    return D(insurable * rate)


def calculate_donation_credit(config):
    """Donation credit: 29% on $106/mo donations ($1,272/year)."""
    tax_cfg = config["tax"]
    rate = Decimal(str(tax_cfg.get("donation_credit_rate", 0.29)))
    monthly = D(tax_cfg.get("donation_monthly", 106))
    annual = D(monthly * 12)
    return D(annual * rate)


def calculate_total_tax(income, config):
    """Returns dict with federal, provincial, cpp, ei, total, effective_rate, marginal_rate."""
    income = D(income)

    federal = calculate_federal_tax(income, config)
    provincial = calculate_bc_tax(income, config)
    cpp = calculate_cpp(income, config)
    ei = calculate_ei(income, config)
    donation_credit = calculate_donation_credit(config)

    # Apply donation credit to federal tax
    federal = max(D(0), D(federal - donation_credit))

    total = D(federal + provincial + cpp + ei)

    effective_rate = D(0)
    if income > 0:
        effective_rate = D((total / income) * 100)

    # Marginal rate: find the bracket the taxpayer is in
    marginal_rate = _find_marginal_rate(income, config)

    return TaxResult(
        federal=federal,
        provincial=provincial,
        cpp=cpp,
        ei=ei,
        total=total,
        effective_rate=effective_rate,
        marginal_rate=marginal_rate,
        donation_credit=donation_credit,
    )


def _find_marginal_rate(income, config):
    """Find combined federal + provincial marginal rate."""
    tax_cfg = config["tax"]
    bpa = D(tax_cfg["basic_personal_amount"])

    # Federal marginal
    fed_brackets = tax_cfg["federal_brackets"]
    remaining = max(D(income) - bpa, D(0))
    fed_marginal = Decimal("0")
    for bracket_size, rate in fed_brackets:
        bracket_size = D(bracket_size)
        fed_marginal = Decimal(str(rate))
        if remaining <= bracket_size:
            break
        remaining -= bracket_size

    # BC marginal
    bc_bpa = D(tax_cfg["bc_basic_personal_amount"])
    bc_brackets = tax_cfg["bc_brackets"]
    remaining = max(D(income) - bc_bpa, D(0))
    bc_marginal = Decimal("0")
    for bracket_size, rate in bc_brackets:
        bracket_size = D(bracket_size)
        bc_marginal = Decimal(str(rate))
        if remaining <= bracket_size:
            break
        remaining -= bracket_size

    combined = D((fed_marginal + bc_marginal) * 100)
    return combined
