#!/usr/bin/env python3
"""TIMI risk score for unstable angina/non-ST-elevation myocardial infarction.

The 7-item score and historical 14-day composite endpoint rates follow
Antman et al., JAMA 2000;284:835-842 (doi:10.1001/jama.284.7.835).
"""

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

FACTORS = (
    "age", "cad_risk_factors", "known_cad", "aspirin_last_7_days",
    "anginal_events_24h", "st_deviation", "elevated_biomarkers",
)
BINARY_FACTORS = ("known_cad", "aspirin_last_7_days", "st_deviation", "elevated_biomarkers")
EVENT_RATES = (4.7, 4.7, 8.3, 13.2, 19.9, 26.2, 40.9, 40.9)
REFERENCE = "Antman et al. JAMA. 2000;284:835-842. doi:10.1001/jama.284.7.835"
OUTCOME = "14-day death, new/recurrent MI, or severe ischemia requiring urgent revascularization"


def _integer(value: Any, name: str, upper: int) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be an integer between 0 and {upper}")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and value.strip().isdecimal():
        result = int(value.strip())
    else:
        raise ValueError(f"{name} must be an integer between 0 and {upper}")
    if not 0 <= result <= upper:
        raise ValueError(f"{name} must be an integer between 0 and {upper}")
    return result


def _boolean(value: Any, name: str = "factor") -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        val = value.strip().lower()
        if val in ("true", "yes", "1"):
            return True
        if val in ("false", "no", "0"):
            return False
    raise ValueError(f"{name} must be yes/no, true/false, or 1/0")


def calculate_metrics(**kwargs: Any) -> dict[str, Any]:
    """Calculate the original integer TIMI UA/NSTEMI score, not treatment advice.

    CAD risk factor count covers family history, hypertension,
    hypercholesterolemia, diabetes and current smoking (0-5).
    Known CAD means prior stenosis >=50%; ST deviation means >=0.5 mm.
    Historical event rates are cohort observations, not individual risks.
    """
    missing = [k for k in FACTORS if k not in kwargs or kwargs[k] is None or kwargs[k] == ""]
    unknown = set(kwargs) - set(FACTORS)
    if missing:
        raise ValueError("Missing required TIMI inputs: " + ", ".join(missing))
    if unknown:
        raise ValueError("Unknown TIMI inputs: " + ", ".join(sorted(unknown)))

    age = _integer(kwargs["age"], "age", 120)
    cad_factors = _integer(kwargs["cad_risk_factors"], "cad_risk_factors", 5)
    angina = _integer(kwargs["anginal_events_24h"], "anginal_events_24h", 1000)
    flags = {name: _boolean(kwargs[name], name) for name in BINARY_FACTORS}
    criteria = {
        "age_65_or_older": age >= 65,
        "three_or_more_cad_risk_factors": cad_factors >= 3,
        "known_cad_stenosis_50_or_more": flags["known_cad"],
        "aspirin_use_last_7_days": flags["aspirin_last_7_days"],
        "two_or_more_anginal_events_24h": angina >= 2,
        "st_deviation_0_5_mm_or_more": flags["st_deviation"],
        "elevated_cardiac_biomarkers": flags["elevated_biomarkers"],
    }
    score = sum(criteria.values())
    band = "Lower" if score <= 2 else "Intermediate" if score <= 4 else "Higher"
    return {
        "tool": "timi-nstemi-risk-score",
        "score": score,
        "max_score": 7,
        "event_rate_14d_pct": EVENT_RATES[score],
        "classification": band,
        "criteria_met": criteria,
        "outcome": OUTCOME,
        "reference": REFERENCE,
        "note": "Historical TIMI 11B cohort composite event rate; not an individualized probability or treatment directive.",
    }


def _validate_safe_path(path_str: str, must_exist: bool = False) -> Path:
    """Resolve an input/output path; reject explicit parent traversal components."""
    if not path_str or ".." in Path(path_str).parts:
        raise ValueError("Path traversal detected or empty path")
    path = Path(path_str).resolve()
    if must_exist and not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path_str}")
    return path


def _csv_safe(value: Any) -> Any:
    """Prevent spreadsheet formula execution in user-supplied CSV columns."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def process_batch(input_csv: str, output_csv: str) -> None:
    """Validate all records before atomically replacing the output CSV."""
    in_path = _validate_safe_path(input_csv, must_exist=True)
    out_path = _validate_safe_path(output_csv)
    if in_path == out_path:
        raise ValueError("Input and output paths must be different")
    temp_name = None
    try:
        with in_path.open("r", encoding="utf-8-sig", newline="") as infile:
            reader = csv.DictReader(infile)
            cols = reader.fieldnames or []
            if len(cols) != len(set(cols)):
                raise ValueError("CSV has duplicate column names")
            missing = sorted(set(FACTORS) - set(cols))
            if missing:
                raise ValueError("CSV missing required headers: " + ", ".join(missing))
            outputs = ("score", "event_rate_14d_pct", "classification")
            if set(outputs) & set(cols):
                raise ValueError("CSV already contains output column names")
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=out_path.parent,
                                             prefix=".timi-", suffix=".tmp", delete=False) as f:
                temp_name = f.name
                writer = csv.DictWriter(f, fieldnames=[*cols, *outputs])
                writer.writeheader()
                n = 0
                for i, row in enumerate(reader, start=2):
                    if None in row:
                        raise ValueError(f"CSV row {i}: extra fields")
                    try:
                        res = calculate_metrics(**{k: row[k] for k in FACTORS})
                    except ValueError as exc:
                        raise ValueError(f"CSV row {i}: {exc}") from exc
                    writer.writerow({**{k: _csv_safe(v) for k, v in row.items()},
                                     "score": res["score"], "event_rate_14d_pct": res["event_rate_14d_pct"],
                                     "classification": res["classification"]})
                    n += 1
        os.replace(temp_name, out_path)
        temp_name = None
        print(f"Processed {n} records -> {out_path}")
    finally:
        if temp_name is not None:
            os.unlink(temp_name)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validated TIMI UA/NSTEMI 0–7 risk score")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Evaluate one patient without transmitting input")
    for name in FACTORS:
        single.add_argument("--" + name.replace("_", "-"), required=True,
                            help="Explicit assessment (boolean items: yes/no)")
    batch = commands.add_parser("batch", help="Evaluate CSV rows locally")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            print(json.dumps(calculate_metrics(**{k: getattr(args, k) for k in FACTORS}), indent=2))
        else:
            process_batch(args.input, args.output)
    except (ValueError, FileNotFoundError, PermissionError, csv.Error) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
