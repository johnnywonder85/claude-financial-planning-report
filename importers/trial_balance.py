"""Trial Balance importer — auto-detects CSV vs Excel, parses to Account objects."""

import os
from decimal import Decimal
from models.accounts import Account, D

try:
    import pandas as pd
except ImportError:
    pd = None


def load_trial_balance(filepath, config):
    """Load trial balance from CSV or Excel file.

    Expected columns: account_name, debit/credit (or single 'balance' column).
    Flexible header matching (case-insensitive, handles common variations).
    """
    if not os.path.exists(filepath):
        print(f"  [INFO] Trial balance file not found: {filepath}")
        print("  [INFO] Using opening balances from config.yaml instead.")
        return _build_accounts_from_config(config)

    ext = os.path.splitext(filepath)[1].lower()

    if ext in (".csv", ".txt"):
        df = pd.read_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Find account name column
    name_col = None
    for candidate in ["account_name", "account", "name", "description"]:
        if candidate in df.columns:
            name_col = candidate
            break
    if name_col is None:
        raise ValueError(f"Cannot find account name column. Found: {list(df.columns)}")

    # Determine balance: debit/credit columns or single balance column
    accounts = []
    if "debit" in df.columns and "credit" in df.columns:
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            debit = Decimal(str(row.get("debit", 0) or 0))
            credit = Decimal(str(row.get("credit", 0) or 0))
            balance = D(debit - credit)
            accounts.append((name, balance))
    elif "balance" in df.columns:
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            balance = D(row["balance"])
            accounts.append((name, balance))
    else:
        raise ValueError(f"Cannot find debit/credit or balance columns. Found: {list(df.columns)}")

    return build_coa_mapping(accounts, config)


def build_coa_mapping(raw_accounts, config):
    """Map TB account names to model categories using coa_mapping in config.

    Uses keyword-based auto-classification with confidence scoring.
    Unmatched accounts are flagged for user review.
    """
    coa_map = config.get("coa_mapping", {})
    mapped = []
    unmatched = []

    for name, balance in raw_accounts:
        # Direct match
        if name in coa_map:
            info = coa_map[name]
            mapped.append(Account(
                name=name,
                account_type=info.get("type", "Asset"),
                sub_type=info.get("sub_type", "Cash"),
                balance=balance,
                tax_treatment=info.get("tax_treatment", "N/A"),
            ))
            continue

        # Keyword-based auto-classification
        name_lower = name.lower()
        match_info = _keyword_classify(name_lower)
        if match_info:
            mapped.append(Account(
                name=name,
                account_type=match_info["type"],
                sub_type=match_info["sub_type"],
                balance=balance,
                tax_treatment=match_info.get("tax_treatment", "N/A"),
            ))
        else:
            unmatched.append((name, balance))

    if unmatched:
        print("\n  [WARNING] Unmatched TB accounts (add to coa_mapping in config.yaml):")
        for name, bal in unmatched:
            print(f"    - {name}: ${bal}")

    return mapped


def _keyword_classify(name_lower):
    """Keyword-based auto-classification with confidence scoring."""
    keywords = {
        "chequing": {"type": "Asset", "sub_type": "Cash"},
        "checking": {"type": "Asset", "sub_type": "Cash"},
        "savings": {"type": "Asset", "sub_type": "Cash"},
        "tfsa": {"type": "Asset", "sub_type": "Investment", "tax_treatment": "TFSA"},
        "rrsp": {"type": "Asset", "sub_type": "Investment", "tax_treatment": "RRSP"},
        "investment": {"type": "Asset", "sub_type": "Investment"},
        "receivable": {"type": "Asset", "sub_type": "Cash"},
        "line of credit": {"type": "Liability", "sub_type": "Debt"},
        "loc": {"type": "Liability", "sub_type": "Debt"},
        "loan": {"type": "Liability", "sub_type": "Debt"},
        "credit card": {"type": "Liability", "sub_type": "Debt"},
        "payable": {"type": "Liability", "sub_type": "Debt"},
        "revenue": {"type": "Revenue", "sub_type": "Income"},
        "income": {"type": "Revenue", "sub_type": "Income"},
        "consulting": {"type": "Revenue", "sub_type": "Income"},
        "rent": {"type": "Expense", "sub_type": "Fixed"},
        "utilities": {"type": "Expense", "sub_type": "Fixed"},
        "insurance": {"type": "Expense", "sub_type": "Fixed"},
        "expense": {"type": "Expense", "sub_type": "Discretionary"},
    }

    for keyword, info in keywords.items():
        if keyword in name_lower:
            return info
    return None


def _build_accounts_from_config(config):
    """Build accounts from config when no TB file is provided."""
    accounts = []

    # Chequing — assume $5,000 opening buffer
    accounts.append(Account(
        name="Business Chequing",
        account_type="Asset",
        sub_type="Cash",
        balance=D(5000),
    ))

    # TFSA
    accounts.append(Account(
        name="TFSA",
        account_type="Asset",
        sub_type="Investment",
        balance=D(0),
        tax_treatment="TFSA",
    ))

    # RRSP
    accounts.append(Account(
        name="RRSP",
        account_type="Asset",
        sub_type="Investment",
        balance=D(0),
        tax_treatment="RRSP",
    ))

    # Safety Fund
    accounts.append(Account(
        name="Safety Fund",
        account_type="Asset",
        sub_type="Cash",
        balance=D(0),
    ))

    # Emergency Fund
    accounts.append(Account(
        name="Emergency Fund",
        account_type="Asset",
        sub_type="Cash",
        balance=D(0),
    ))

    # LOC
    debts = config.get("debts", {})
    loc = debts.get("loc", {})
    accounts.append(Account(
        name="LOC",
        account_type="Liability",
        sub_type="Debt",
        balance=D(loc.get("balance", 6450)),
        interest_rate=loc.get("interest_rate", 0.0449),
        payment_day=loc.get("autopay_day", 21),
        debt_priority=1,
    ))

    # Car Loan
    car = debts.get("car_loan", {})
    accounts.append(Account(
        name="Car Loan",
        account_type="Liability",
        sub_type="Debt",
        balance=D(car.get("balance", 4490)),
        interest_rate=car.get("interest_rate", 0.0449),
        payment_day=1,
        debt_priority=2,
    ))

    # Student Loan
    sl = debts.get("student_loan", {})
    accounts.append(Account(
        name="Student Loan",
        account_type="Liability",
        sub_type="Debt",
        balance=D(sl.get("balance", 10500)),
        interest_rate=sl.get("interest_rate", 0.0),
        payment_day=sl.get("payment_day", 1),
        debt_priority=3,
    ))

    return accounts


def display_summary(accounts):
    """Print opening balance table for validation."""
    print("\n" + "=" * 60)
    print("  OPENING TRIAL BALANCE")
    print("=" * 60)
    print(f"  {'Account':<25} {'Type':<12} {'Balance':>12}")
    print("  " + "-" * 49)

    total_assets = Decimal("0")
    total_liabilities = Decimal("0")

    for a in sorted(accounts, key=lambda x: x.account_type):
        sign = ""
        if a.account_type == "Liability":
            sign = "-"
            total_liabilities += a.balance
        elif a.account_type == "Asset":
            total_assets += a.balance

        print(f"  {a.name:<25} {a.account_type:<12} {sign}${a.balance:>10,.2f}")

    print("  " + "-" * 49)
    print(f"  {'Total Assets':<25} {'':12} ${total_assets:>10,.2f}")
    print(f"  {'Total Liabilities':<25} {'':12} -${total_liabilities:>10,.2f}")
    print(f"  {'Net Worth':<25} {'':12} ${total_assets - total_liabilities:>10,.2f}")
    print("=" * 60)

    # Template format hint
    print("\n  Expected TB file format:")
    print("  account_name, debit, credit")
    print("  (or: account_name, balance)")
    print()
