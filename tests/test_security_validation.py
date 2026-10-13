"""Regression tests for published TIMI UA/NSTEMI score and safe CSV exports."""
import csv
from pathlib import Path
import pytest
from timi_nstemi import calculate_metrics, process_batch, _validate_safe_path, EVENT_RATES

BASE = dict(age=40, cad_risk_factors=0, known_cad=False,
            aspirin_last_7_days=False, anginal_events_24h=0,
            st_deviation=False, elevated_biomarkers=False)
ALL = dict(age=65, cad_risk_factors=3, known_cad=True,
           aspirin_last_7_days=True, anginal_events_24h=2,
           st_deviation=True, elevated_biomarkers=True)
FACTORS = list(BASE)


@pytest.mark.parametrize("n", range(8))
def test_every_score_and_source_rate(n):
    inputs = BASE.copy()
    inputs.update({key: ALL[key] for key in FACTORS[:n]})
    result = calculate_metrics(**inputs)
    assert result["score"] == n
    assert result["event_rate_14d_pct"] == EVENT_RATES[n]
    assert sum(result["criteria_met"].values()) == n


def test_clinical_thresholds():
    assert calculate_metrics(**{**BASE, "age": 64})["score"] == 0
    assert calculate_metrics(**{**BASE, "age": 65})["score"] == 1
    assert calculate_metrics(**{**BASE, "cad_risk_factors": 2})["score"] == 0
    assert calculate_metrics(**{**BASE, "cad_risk_factors": 3})["score"] == 1
    assert calculate_metrics(**{**BASE, "anginal_events_24h": 1})["score"] == 0
    assert calculate_metrics(**{**BASE, "anginal_events_24h": 2})["score"] == 1


@pytest.mark.parametrize("changes", [
    {"age": float("nan")}, {"age": -1}, {"age": 150}, {"cad_risk_factors": 6},
    {"anginal_events_24h": 1.5}, {"known_cad": "maybe"},
    {"age": None}, {"elevated_biomarkers": ""}, {"unexpected": 8},
])
def test_invalid_or_unknown_inputs_rejected(changes):
    with pytest.raises(ValueError):
        calculate_metrics(**{**BASE, **changes})


def test_missing_input_never_defaults_to_negative():
    with pytest.raises(ValueError, match="Missing required"):
        calculate_metrics(age=65)


def test_csv_batch_valid_and_formula_escaped(tmp_path):
    src = tmp_path / "cases.csv"
    out = tmp_path / "scores.csv"
    with src.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[*BASE, "note"])
        writer.writeheader()
        writer.writerow({**{key: str(value).lower() for key, value in ALL.items()}, "note": "=SUM(1,2)"})
    process_batch(str(src), str(out))
    with out.open(newline="") as f:
        row = next(csv.DictReader(f))
    assert row["score"] == "7"
    assert row["event_rate_14d_pct"] == "40.9"
    assert row["note"] == "'=SUM(1,2)"


def test_invalid_row_does_not_replace_existing_output(tmp_path):
    src = tmp_path / "cases.csv"
    out = tmp_path / "scores.csv"
    out.write_text("existing results", encoding="utf-8")
    src.write_text(",".join(BASE) + "\n" + ",".join(["bad"] * len(BASE)) + "\n")
    with pytest.raises(ValueError, match="row 2"):
        process_batch(str(src), str(out))
    assert out.read_text() == "existing results"
    assert not list(tmp_path.glob(".timi-*.tmp"))


def test_paths_and_output_collision(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = Path("cases.csv")
    src.write_text("data\n")
    assert _validate_safe_path("cases.csv", must_exist=True) == src.resolve()
    with pytest.raises(ValueError, match="Path traversal"):
        _validate_safe_path("foo/../bar")
    with pytest.raises(FileNotFoundError):
        _validate_safe_path("missing.csv", must_exist=True)
    with pytest.raises(ValueError, match="different"):
        process_batch("cases.csv", "cases.csv")
