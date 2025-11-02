from __future__ import annotations

from typing import Dict, List, Optional

from .extract import extract_text
from .parsers import (
    detect_bank,
    parse_bank_1,
    parse_bank_2,
    parse_bank_3,
    parse_bank_4,
    parse_bank_5,
    FIELDS,
)


def identify_and_parse(text: str) -> Dict[str, Optional[str]]:
    """
    Identify bank from raw text and route to the appropriate parser.
    Returns a dictionary including 'bank' and the standard FIELDS keys.
    """
    bank = detect_bank(text) or "unknown"
    if bank == "bank1":
        data = parse_bank_1(text)
    elif bank == "bank2":
        data = parse_bank_2(text)
    elif bank == "bank3":
        data = parse_bank_3(text)
    elif bank == "bank4":
        data = parse_bank_4(text)
    elif bank == "bank5":
        data = parse_bank_5(text)
    else:
        data = {k: None for k in FIELDS}

    # Attach bank id
    data_with_bank: Dict[str, Optional[str]] = {"bank": bank, **data}
    return data_with_bank


essential_keys: List[str] = ["bank", *FIELDS]


def process_pdf(pdf_path: str, password: str = "") -> Dict[str, Optional[str]]:
    """Extractor -> Orchestrator -> Parser for a single PDF path."""
    text = extract_text(pdf_path, password=password)
    result = identify_and_parse(text)
    # Add source file for traceability
    result["source_file"] = pdf_path
    return result
