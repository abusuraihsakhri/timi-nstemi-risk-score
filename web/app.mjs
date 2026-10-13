import {FIELDS, calculateTIMI, processBatchCSV} from './timi.mjs';

const form = document.getElementById('calculator');
const formError = document.getElementById('form-error');
let downloadUrl;

form.addEventListener('submit', (event) => {
  event.preventDefault();
  formError.hidden = true;
  try {
    const data = Object.fromEntries(FIELDS.map(field => [field, form.elements.namedItem(field).value]));
    const result = calculateTIMI(data);
    document.getElementById('score').textContent = result.score + ' / 7';
    document.getElementById('rate').textContent = result.eventRate14dPct + '%';
    document.getElementById('risk-band').textContent = result.classification;
    document.getElementById('result').hidden = false;
    document.getElementById('empty-result').hidden = true;
  } catch (err) {
    formError.textContent = err.message;
    formError.hidden = false;
    document.getElementById('result').hidden = true;
  }
});
form.addEventListener('reset', () => {
  document.getElementById('result').hidden = true;
  document.getElementById('empty-result').hidden = false;
  formError.hidden = true;
});

document.getElementById('process-csv').addEventListener('click', async () => {
  const file = document.getElementById('batch-file').files[0];
  const message = document.getElementById('batch-message');
  const link = document.getElementById('download');
  if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = undefined; }
  link.hidden = true;
  message.className = '';
  if (!file) { message.textContent = 'Select a CSV file first.'; return; }
  if (file.size > 5_000_000) { message.textContent = 'File exceeds 5 MB.'; return; }
  message.textContent = 'Processing...';
  try {
    const result = processBatchCSV(await file.text());
    downloadUrl = URL.createObjectURL(new Blob([result.csv], {type:'text/csv;charset=utf-8'}));
    link.href = downloadUrl;
    link.hidden = false;
    message.className = 'pass';
    message.textContent = 'Processed ' + result.count + ' records locally.';
  } catch (err) { message.textContent = 'CSV error: ' + err.message; }
});
window.addEventListener('pagehide', () => { if (downloadUrl) URL.revokeObjectURL(downloadUrl); });
