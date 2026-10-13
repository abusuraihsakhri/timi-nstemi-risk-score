# TIMI UA/NSTEMI Risk Score

A validated implementation of the **published seven-item scoring rule** for unstable angina / non-ST-elevation myocardial infarction (UA/NSTEMI). Runs in a browser without a backend, through the Python CLI, or via a separately hosted API.

**Clinical limitations:** Results are the integer 0–7 score and observed **14-day composite event rates in the original TIMI 11B cohort**. These are not individualized risk probabilities or treatment recommendations. This implementation has not been independently validated as a medical device.

## Calculation

One point is assigned for each criterion: age ≥65 years; at least three CAD risk factors (family history, hypertension, hypercholesterolemia, diabetes, current smoking); prior coronary stenosis ≥50%; aspirin use within seven days; two or more anginal episodes within 24 hours; ST-segment deviation ≥0.5 mm; and elevated serum cardiac biomarkers.

| TIMI score | 14-day composite event rate |
|---|---:|
| 0–1 | 4.7% |
| 2 | 8.3% |
| 3 | 13.2% |
| 4 | 19.9% |
| 5 | 26.2% |
| 6–7 | 40.9% |

Endpoint: all-cause death, new/recurrent MI, or severe recurrent ischemia requiring urgent revascularization through 14 days. The descriptive bands (Lower 0–2, Intermediate 3–4, Higher 5–7) **are not treatment thresholds**. Source: Antman EM et al. *JAMA*. 2000;284:835–842. [doi:10.1001/jama.284.7.835](https://doi.org/10.1001/jama.284.7.835). See also the [TIMI Study Group calculator](https://timi.org/calculators/timi-risk-score-calculator-for-ua-nstemi/).

## Browser application

Open [web/index.html](web/index.html) locally, or use the GitHub Pages deployment when available. The browser app performs all scoring and CSV processing locally with no servers, analytics, outbound requests, external scripts, or persisted inputs. Do not import patient-identifiable data.

The interface requires all seven factors, supports accessible keyboard input and responsive layout, and handles CSV files up to 5 MB and 20,000 records. CSV downloads escape potential spreadsheet formulas. Uses modern browser ES modules; no browser Python runtime is needed.

## Python CLI

Python 3.10 or later. Install and run:

~~~bash
python -m pip install -e ".[dev]"
timi-nstemi single --age 65 --cad-risk-factors 3 --known-cad yes \
  --aspirin-last-7-days no --anginal-events-24h 2 \
  --st-deviation no --elevated-biomarkers yes
timi-nstemi batch -i sample.csv -o results.csv
~~~

The required CSV fields are:

~~~text
age,cad_risk_factors,known_cad,aspirin_last_7_days,anginal_events_24h,st_deviation,elevated_biomarkers
~~~

Extra columns are retained. Booleans accept yes/no, true/false, or 1/0. Missing/invalid fields fail closed; invalid batches do not replace existing output. The former v1/v2/v3 CLI and CSV input schema is incompatible because it implemented unrelated arithmetic.

## Optional API and legacy components

Start the backend using:

~~~bash
python cli.py serve --host 127.0.0.1 --port 8000
~~~

**POST /api/timi** accepts the seven required JSON fields (age, CAD count and anginal count as integers; the four other fields as JSON booleans) and returns the score, historical event rate, and criteria breakdown.

~~~json
{
  "age": 65,
  "cad_risk_factors": 3,
  "known_cad": true,
  "aspirin_last_7_days": false,
  "anginal_events_24h": 2,
  "st_deviation": false,
  "elevated_biomarkers": true
}
~~~

The pre-existing generic agent console and legacy **/api/audit** and **/api/chat** routes are retained for compatibility. Their arbitrary metric thresholds and mock responses are **not TIMI scoring** and must not be used for clinical decisions. Never send PHI to these legacy routes. The generic backend is not suitable for public exposure without additional authentication and security controls.

The audit trail is signed in memory, not persistently stored. The log-read endpoint is disabled unless AUDIT_LOG_READ_TOKEN is set, then requires a Bearer token. When APP_ENV=production, AUDIT_SECRET_KEY must be configured. Do not place real keys in version control.

## Tests, deployment and environment

~~~bash
python -m pytest -q
node --test tests/timi-web.test.mjs
~~~

GitHub Actions runs Python tests on 3.10–3.12 and JavaScript syntax/tests with Node 22. The Pages workflow deploys the static web directory from master when GitHub Pages is enabled. Browser targets: current Chrome, Firefox, Safari and Edge.

For the Docker service, copy .env.example to .env, provide a securely generated AUDIT_SECRET_KEY, then run docker compose up --build. By default the container binds to localhost, with an unprivileged user. Use separate operational and regulatory safeguards before using the API with clinical records.

## License

[MIT](LICENSE).
