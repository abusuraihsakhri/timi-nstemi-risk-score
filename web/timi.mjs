/** Original TIMI UA/NSTEMI score, Antman et al., JAMA 2000;284:835-842. */
export const FIELDS = Object.freeze([
  'age', 'cad_risk_factors', 'known_cad', 'aspirin_last_7_days',
  'anginal_events_24h', 'st_deviation', 'elevated_biomarkers'
]);
export const RATES = Object.freeze([4.7, 4.7, 8.3, 13.2, 19.9, 26.2, 40.9, 40.9]);

function integer(value, name, maximum) {
  if ((typeof value !== 'number' && typeof value !== 'string') ||
      typeof value === 'string' && !/^\d+$/.test(value.trim()) ||
      value === '' || value === null) {
    throw new Error(name + ': enter a whole number from 0 to ' + maximum);
  }
  const num = Number(value);
  if (!Number.isSafeInteger(num) || num < 0 || num > maximum) {
    throw new Error(name + ': enter a whole number from 0 to ' + maximum);
  }
  return num;
}

function yesNo(value, name) {
  if (typeof value === 'boolean') return value;
  if (value === 1 || value === 0) return Boolean(value);
  if (typeof value === 'string') {
    const s = value.trim().toLowerCase();
    if (['yes', 'true', '1'].includes(s)) return true;
    if (['no', 'false', '0'].includes(s)) return false;
  }
  throw new Error(name + ': select Yes or No');
}

export function calculateTIMI(input) {
  for (const field of FIELDS) {
    if (!Object.hasOwn(input, field) || input[field] == null || input[field] === '') {
      throw new Error('Missing required input: ' + field);
    }
  }
  const age = integer(input.age, 'Age', 120);
  const riskFactors = integer(input.cad_risk_factors, 'CAD risk factors', 5);
  const angina = integer(input.anginal_events_24h, 'Anginal events', 1000);
  const criteria = {
    age_65_or_older: age >= 65,
    three_or_more_cad_risk_factors: riskFactors >= 3,
    known_cad_stenosis_50_or_more: yesNo(input.known_cad, 'Known CAD'),
    aspirin_use_last_7_days: yesNo(input.aspirin_last_7_days, 'Recent aspirin'),
    two_or_more_anginal_events_24h: angina >= 2,
    st_deviation_0_5_mm_or_more: yesNo(input.st_deviation, 'ST deviation'),
    elevated_cardiac_biomarkers: yesNo(input.elevated_biomarkers, 'Elevated biomarkers')
  };
  const score = Object.values(criteria).filter(Boolean).length;
  return {
    score,
    maxScore: 7,
    eventRate14dPct: RATES[score],
    classification: score <= 2 ? 'Lower' : score <= 4 ? 'Intermediate' : 'Higher',
    criteriaMet: criteria
  };
}

export function parseCSV(text) {
  const data = text.replace(/^\uFEFF/, '');
  const rows = []; let row = []; let field = ''; let quoted = false; let closed = false;
  for (let i = 0; i < data.length; i++) {
    const char = data[i];
    if (quoted) {
      if (char === '"') {
        if (data[i + 1] === '"') { field += '"'; i++; }
        else { quoted = false; closed = true; }
      } else { field += char; }
    } else if (char === ',' || char === '\n' || char === '\r') {
      row.push(field); field = ''; closed = false;
      if (char !== ',') {
        if (char === '\r' && data[i + 1] === '\n') i++;
        rows.push(row); row = [];
      }
    } else if (char === '"' && !field && !closed) {
      quoted = true;
    } else if (closed || char === '"') {
      throw new Error('Invalid CSV quoting');
    } else { field += char; }
  }
  if (quoted) throw new Error('Unclosed CSV quoted field');
  if (field || row.length || closed) { row.push(field); rows.push(row); }
  return rows;
}

function escapeCell(value, userSupplied) {
  let s = String(value ?? '');
  if (userSupplied && /^[\s]*[=+@-]/.test(s)) s = "'" + s;
  return /[",\r\n]/.test(s) ? '"' + s.replaceAll('"', '""') + '"' : s;
}

export function processBatchCSV(text) {
  if (text.length > 5_000_000) throw new Error('CSV exceeds 5 MB size limit');
  const rows = parseCSV(text);
  if (!rows.length) throw new Error('CSV is empty');
  const columns = rows[0];
  if (new Set(columns).size !== columns.length) throw new Error('Duplicate CSV headers');
  for (const name of FIELDS) if (!columns.includes(name)) throw new Error('Missing CSV header: ' + name);
  const outputs = ['score', 'event_rate_14d_pct', 'classification'];
  for (const name of outputs) if (columns.includes(name)) throw new Error('Output column already exists: ' + name);
  if (rows.length > 20_001) throw new Error('CSV exceeds 20,000 record limit');
  const serialized = [[...columns, ...outputs].map(x => escapeCell(x, false)).join(',')];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (row.length !== columns.length) throw new Error('CSV record ' + (i + 1) + ': column count mismatch');
    const input = Object.fromEntries(columns.map((name, j) => [name, row[j]]));
    let result;
    try { result = calculateTIMI(input); }
    catch (err) { throw new Error('CSV record ' + (i + 1) + ': ' + err.message); }
    serialized.push([...row.map(x => escapeCell(x, true)), result.score, result.eventRate14dPct,
      result.classification].join(','));
  }
  return { csv: serialized.join('\r\n') + '\r\n', count: rows.length - 1 };
}
