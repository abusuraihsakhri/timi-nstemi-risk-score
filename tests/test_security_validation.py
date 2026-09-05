"""
Security and input validation tests for timi-nstemi-risk-score.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from timi_nstemi import calculate_metrics, process_batch, _validate_safe_path


class TestCalculateMetricsValidation:
    """Tests for input validation in calculate_metrics."""

    def test_empty_kwargs_raises_error(self):
        with pytest.raises(ValueError, match="At least one input parameter is required"):
            calculate_metrics()

    def test_none_values_filtered(self):
        result = calculate_metrics(v1=None, v2=None, valid=5.0)
        assert result["score"] == 5.0

    def test_single_numeric_param(self):
        result = calculate_metrics(v1=10.0)
        assert result["score"] == 10.0
        assert result["classification"] == "Moderate / Intermediate"

    def test_multiple_numeric_params(self):
        result = calculate_metrics(v1=10.0, v2=5.0, v3=2.0)
        # score = 10 + 5/2 + 2/3 = 10 + 2.5 + 0.67 = 13.17
        assert result["score"] == pytest.approx(13.17, abs=0.01)

    def test_string_params_ignored_in_calculation(self):
        result = calculate_metrics(v1=10.0, name="test")
        assert result["score"] == 10.0

    def test_classification_low(self):
        result = calculate_metrics(v1=5.0)
        assert result["classification"] == "Low / Standard"
        assert "Standard" in result["clinical_recommendation"]

    def test_classification_moderate(self):
        result = calculate_metrics(v1=15.0)
        assert result["classification"] == "Moderate / Intermediate"
        assert "Close observation" in result["clinical_recommendation"]

    def test_classification_high(self):
        result = calculate_metrics(v1=30.0)
        assert result["classification"] == "High / Severe"
        assert "Urgent" in result["clinical_recommendation"]


class TestPathValidation:
    """Tests for path traversal prevention."""

    def test_valid_path_within_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "test.csv"
        test_file.write_text("data\n1\n")
        result = _validate_safe_path("test.csv", must_exist=True)
        assert result == test_file.resolve()

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal detected"):
            _validate_safe_path("../etc/passwd")

    def test_nonexistent_input_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            _validate_safe_path("nonexistent.csv", must_exist=True)

    def test_output_path_doesnt_need_to_exist(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _validate_safe_path("output.csv", must_exist=False)
        assert result == (tmp_path / "output.csv").resolve()


class TestProcessBatchValidation:
    """Tests for process_batch security."""

    def test_batch_with_valid_paths(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("Patient_ID,v1,v2\nPT-001,10.0,5.0\n")
        output_csv = tmp_path / "output.csv"
        process_batch(str(input_csv), str(output_csv))
        assert output_csv.exists()

    def test_batch_path_traversal_input(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises((ValueError, FileNotFoundError)):
            process_batch("../etc/passwd", "output.csv")

    def test_batch_path_traversal_output(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("Patient_ID,v1\nPT-001,10.0\n")
        with pytest.raises(ValueError, match="Path traversal"):
            process_batch(str(input_csv), "../etc/output.csv")
