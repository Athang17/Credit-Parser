from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict, Optional

from credit_parser.orchestrator import process_pdf


def collect_results(folder: Path) -> List[Dict[str, Optional[str]]]:
    results: List[Dict[str, Optional[str]]] = []
    for pdf_path in sorted(folder.glob("*.pdf")):
        try:
            data = process_pdf(str(pdf_path))
            results.append(data)
        except Exception as e:
            results.append({
                "bank": None,
                "total_balance": None,
                "payment_due_date": None,
                "minimum_payment": None,
                "last4": None,
                "statement_closing_date": None,
                "source_file": str(pdf_path),
                "error": str(e),
            })
    return results


def save_json(results: List[Dict[str, Optional[str]]], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def save_csv(results: List[Dict[str, Optional[str]]], out_path: Path) -> None:
    if not results:
        out_path.write_text("")
        return
    # Use union of keys across rows for flexibility
    fieldnames = sorted({k for row in results for k in row.keys()})
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Credit Card Statement Parser")
    parser.add_argument("folder", type=str, help="Folder containing PDF files")
    parser.add_argument("--json", dest="json_out", type=str, default="results.json")
    parser.add_argument("--csv", dest="csv_out", type=str, default="results.csv")
    args = parser.parse_args()

    folder = Path(args.folder)
    results = collect_results(folder)

    # Print to console
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # Save outputs
    save_json(results, Path(args.json_out))
    save_csv(results, Path(args.csv_out))


if __name__ == "__main__":
    main()
