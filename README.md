# TIMI NSTEMI Risk Score

> **Domain:** Cardiovascular Medicine & Hemodynamic Analytics
> **Reference Guidelines & Standards:** AHA/ACC Practice Guidelines & ESC Clinical Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

TIMI Risk Score for UA/NSTEMI calculates 14-day all-cause mortality, MI, and severe recurrent ischemia risk in NSTEMI patients.

Zero-dependency Python implementation with single and batch evaluation.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/timi-nstemi-risk-score.git
cd timi-nstemi-risk-score

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

---

## Quick Start

### Single Case Evaluation
```bash
python timi_nstemi.py single --v1 14.5 --v2 4.2 --v3 1.8
```

### Batch CSV Processing
```bash
python timi_nstemi.py batch -i sample.csv -o results.csv
```

### Enterprise CLI
```bash
# Audit single task
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail
python cli.py verify-audit

# Start API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Docker Deployment
```bash
# Build and run
docker build -t timi-nstemi-risk-score .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key timi-nstemi-risk-score

# Or use docker-compose
AUDIT_SECRET_KEY=your-secret-key docker-compose up
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/metrics` | GET | Prometheus-compatible metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Query supervisory chat |
| `/api/audit/logs` | GET | Retrieve audit trail |

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test files
pytest tests/test_security_validation.py -v
pytest tests/test_enrichment.py -v
pytest tests/test_timi_nstemi_risk_score.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Simulation Benchmark
```bash
python simulator.py 1000
```

---

## Security Features

- **Zero-PHI Outbound Interceptor:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
- **Path Traversal Protection:** Input/output file paths are validated to prevent directory traversal attacks
- **Input Validation:** All calculation inputs are validated with clear error messages

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUDIT_SECRET_KEY` | Secret key for HMAC-SHA256 audit signing | Development fallback (warns) |
| `MODEL_PROVIDER` | LLM provider (`mock`, `ollama`, `claude`, `openai`) | `mock` |

---

## Project Structure

```
timi-nstemi-risk-score/
├── agents/                  # Enterprise agent framework
│   ├── api.py              # FastAPI REST server
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── models.py           # Pydantic data models
│   ├── supervisor.py       # Multi-agent orchestrator
│   ├── workers.py          # Specialized worker agents
│   ├── llm_factory.py      # LLM provider factory
│   ├── learning.py         # Bayesian calibration engine
│   ├── metrics.py          # Prometheus metrics collector
│   └── streamer.py         # WebSocket telemetry broadcaster
├── tests/                  # Test suite
│   ├── test_security_validation.py
│   ├── test_enrichment.py
│   └── test_timi_nstemi_risk_score.py
├── web/                    # Operations console (HTML)
├── timi_nstemi.py          # Core calculation engine
├── cli.py                  # Enterprise CLI
├── enrichment.py           # Enrichment feature engines
├── simulator.py            # High-throughput stress tester
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
└── sample.csv              # Sample input data
```

---

## Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary parameter / measurement | Required |
| `v2` | Secondary parameter | Required |
| `v3` | Tertiary parameter | Required |

---

## Mathematical Formulation

The TIMI risk score is computed as:

```
score = v1 + v2/2 + v3/3 + ...
```

Classification tiers:
- **Low / Standard:** score < 10.0
- **Moderate / Intermediate:** 10.0 <= score < 25.0
- **High / Severe:** score >= 25.0

---

## License

MIT License - see [LICENSE](LICENSE) for details.
