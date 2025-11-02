from __future__ import annotations

import re
from typing import Dict, Optional

# Common output keys
FIELDS = [
    "total_balance",
    "payment_due_date",
    "minimum_payment",
    "last4",
    "statement_closing_date",
]


def _clean_amount(s: str) -> str:
    s = s.strip()
    # normalize unicode minus or spaces
    s = s.replace("\u2212", "-")
    # strip currency markers and CR suffix artifacts
    s = re.sub(r"^[₹r\s]+", "", s)
    s = re.sub(r"\s*CR\b", "", s, flags=re.IGNORECASE)
    return s


def _last4_from_number_block(s: str) -> Optional[str]:
    digits = re.findall(r"\d", s)
    if not digits:
        return None
    return "".join(digits)[-4:] if len(digits) >= 4 else None


def _find_value_after_label(text: str, label_pattern: str, value_pattern: str, window: int = 200) -> Optional[str]:
    """Find the first value that appears within 'window' chars after a label.
    Returns the matched value group 1 if found.
    """
    m = re.search(label_pattern, text, re.IGNORECASE)
    if not m:
        return None
    start = m.end()
    snippet = text[start:start + window]
    mv = re.search(value_pattern, snippet, re.IGNORECASE)
    if mv:
        return mv.group(1).strip()
    return None


# ---------------- Bank 1 ----------------

def parse_bank_1(text: str) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {k: None for k in FIELDS}

    # Total Balance (New Balance shown multiple times; pick last occurrence)
    m_all = re.findall(r"(?:New\s*Balance)[:\s]*\$?([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if m_all:
        out["total_balance"] = _clean_amount(m_all[-1])

    # Payment Due Date
    m = re.search(r"Payment\s*Due\s*Date[:\s]*([A-Za-z0-9/\-–]+)", text, re.IGNORECASE)
    if m:
        out["payment_due_date"] = m.group(1).strip()

    # Minimum Payment
    m = re.search(r"Minimum\s*Payment(?:\s*Due)?[:\s]*\$?([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if m:
        out["minimum_payment"] = _clean_amount(m.group(1))

    # Last 4 digits
    m = re.search(r"Account\s*Number[:\s]*([\d\-\s]+)", text, re.IGNORECASE)
    if m:
        out["last4"] = _last4_from_number_block(m.group(1))

    # Statement Closing Date from Opening/Closing Date X – Y (take Y)
    m = re.search(r"Opening/Closing\s*Date\s*([A-Za-z0-9/\-]+)\s*[–-]\s*([A-Za-z0-9/\-]+)", text, re.IGNORECASE)
    if m:
        out["statement_closing_date"] = m.group(2).strip()

    return out


# ---------------- Bank 2 ----------------

def parse_bank_2(text: str) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {k: None for k in FIELDS}

    # Total Balance -> Ending Balance
    m = re.search(r"Ending\s*Balance.*?\$([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE | re.DOTALL)
    if m:
        out["total_balance"] = _clean_amount(m.group(1))

    # Payment Due Date: likely not present in checking statement
    # Leave as None if not found

    # Minimum Payment: likely not present
    # Leave as None if not found

    # Last 4 digits from Primary Account Number or Account #
    m = re.search(r"Primary\s*Account\s*Number[:\s#]*([0-9\s]+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Account\s*[#No\.]?\s*[:#]*\s*([0-9\s]{6,})", text, re.IGNORECASE)
    if m:
        out["last4"] = _last4_from_number_block(m.group(1))

    # Statement Closing Date -> Statement Date
    m = re.search(r"Statement\s*Date[:\s]*([A-Za-z]+\s+\d{1,2},\s*\d{4})", text, re.IGNORECASE)
    if m:
        out["statement_closing_date"] = m.group(1).strip()

    return out


# ---------------- Bank 3 ----------------

def parse_bank_3(text: str) -> Dict[str, Optional[str]]:
    """ICICI Bank-style statement.
    Extract Total Amount Due, Due Date, Minimum Amount Due, Card last4, Statement Date.
    """
    out: Dict[str, Optional[str]] = {k: None for k in FIELDS}

    # Total Balance near label
    v = _find_value_after_label(text, r"(?:Your\s+)?Total\s+Amount\s+Due\b", r"([₹r]?\s*(?:\d{1,3}(?:,\d{3})+|\d+\.\d{2}))", window=80)
    m = None
    if v:
        out["total_balance"] = _clean_amount(v)
    else:
        m = re.search(r"(?:Your\s+)?Total\s+Amount\s+Due[\s\S]{0,60}?([₹r]?\s*[\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if m:
        out["total_balance"] = _clean_amount(m.group(1))

    # Payment Due Date: "Due Date :" or "Payment Due Date"
    m = re.search(r"(?:Payment\s+)?Due\s*Date\s*:?\s*(?:\n|\s){0,20}?([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", text, re.IGNORECASE)
    if m:
        out["payment_due_date"] = m.group(1)

    # Minimum Amount Due via label-window
    v = _find_value_after_label(text, r"Minimum\s+Amount\s+Due\b", r"([₹r]?\s*(?:\d{1,3}(?:,\d{3})+|\d+\.\d{2}))", window=80)
    if v:
        out["minimum_payment"] = _clean_amount(v)

    # Last 4 from card number block like "4375 XXXX XXXX 8007"
    m = re.search(r"Card\s*Number\s*:?\s*([0-9Xx\s]+)", text, re.IGNORECASE)
    if m:
        out["last4"] = _last4_from_number_block(m.group(1))

    # Statement Closing Date: "Statement Date" used as closing date for many Indian banks
    m = re.search(r"Statement\s*Date\s*:?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", text, re.IGNORECASE)
    if m:
        out["statement_closing_date"] = m.group(1)

    return out


# ---------------- Bank 4 ----------------

def parse_bank_4(text: str) -> Dict[str, Optional[str]]:
    """Generic US credit card statement sample with explicit labels."""
    out: Dict[str, Optional[str]] = {k: None for k in FIELDS}

    # Total Balance from NEW BALANCE or = New Balance using label-window
    v = _find_value_after_label(text, r"NEW\s+BALANCE\b", r"\$?([\d,]+(?:\.\d{2})?)", window=30)
    if not v:
        v = _find_value_after_label(text, r"=\s*New\s*Balance\b", r"\$?([\d,]+(?:\.\d{2})?)", window=30)
    if v:
        out["total_balance"] = _clean_amount(v)

    # Payment Due Date (restrict to date with slashes)
    m = re.search(r"PAYMENT\s*DUE\s*DATE\s*\n?\s*(\d{1,2}/\d{1,2}/\d{2,4})", text, re.IGNORECASE)
    if m:
        out["payment_due_date"] = m.group(1)

    # Minimum Payment Due via label-window
    v = _find_value_after_label(text, r"MINIMUM\s*PAYMENT\s*DUE\b", r"\$?([\d,]+(?:\.\d{2})?)", window=40)
    if v:
        out["minimum_payment"] = _clean_amount(v)

    # Last 4 digits from ACCOUNT NUMBER like 1234-567-890
    m = re.search(r"ACCOUNT\s*NUMBER\s*\n?\s*([\d\-\s]+)", text, re.IGNORECASE)
    if m:
        out["last4"] = _last4_from_number_block(m.group(1))

    # Statement Closing Date: "Closing Date"
    m = re.search(r"Closing\s*Date\s*\n?\s*([0-9/\-]+)", text, re.IGNORECASE)
    if m:
        out["statement_closing_date"] = m.group(1)

    return out


# ---------------- Bank 5 ----------------

def parse_bank_5(text: str) -> Dict[str, Optional[str]]:
    """IDFC FIRST Bank-style statement (India)."""
    out: Dict[str, Optional[str]] = {k: None for k in FIELDS}

    # Total Balance via label-window
    v = _find_value_after_label(text, r"Total\s*Amount\s*Due\b", r"([₹r]?\s*(?:\d{1,3}(?:,\d{3})+|\d+\.\d{2}))", window=160)
    if v:
        out["total_balance"] = _clean_amount(v)

    # Payment Due Date
    v = _find_value_after_label(text, r"Payment\s*Due\s*Date\b", r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", window=160)
    if v:
        out["payment_due_date"] = v

    # Minimum Amount Due
    v = _find_value_after_label(text, r"Minimum\s*Amount\s*Due\b", r"([₹r]?\s*(?:\d{1,3}(?:,\d{3})+|\d+\.\d{2}))", window=160)
    if v:
        out["minimum_payment"] = _clean_amount(v)

    # Last 4 digits from Account Number
    m = re.search(r"Account\s*Number\s*:?\s*([\d\s]+)", text, re.IGNORECASE)
    if m:
        out["last4"] = _last4_from_number_block(m.group(1))

    # Statement Closing Date -> Statement Date
    m = re.search(r"Statement\s*Date\s*\n?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", text, re.IGNORECASE)
    if m:
        out["statement_closing_date"] = m.group(1)

    return out


# --------------- Detection ----------------

def detect_bank(text: str) -> Optional[str]:
    t = text.lower()
    if "building blocks student handout" in t:
        return "bank1"
    if "connections checking" in t or "1000 walnut" in t:
        return "bank2"
    # ICICI Bank cues
    if "icici" in t or "your total amount due" in t:
        return "bank3"
    # Generic sample statement cues
    if "sample credit card statement" in t or "great lakes higher education" in t:
        return "bank4"
    # IDFC FIRST cues
    if "idfcbank" in t or "customer relationship no." in t:
        return "bank5"
    return None
