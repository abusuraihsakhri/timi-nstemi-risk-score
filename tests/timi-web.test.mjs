import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateTIMI, processBatchCSV, parseCSV, RATES} from '../web/timi.mjs';

const baseline = {
  age: 40, cad_risk_factors: 0, known_cad: false,
  aspirin_last_7_days: false, anginal_events_24h: 0,
  st_deviation: false, elevated_biomarkers: false
};
const positive = {age: 65, cad_risk_factors: 3, known_cad: true,
  aspirin_last_7_days: true, anginal_events_24h: 2, st_deviation: true,
  elevated_biomarkers: true};
const fields = ['age','cad_risk_factors','known_cad','aspirin_last_7_days','anginal_events_24h','st_deviation','elevated_biomarkers'];
test('all eight score totals map to published combined source bins', () => {
  for (let n=0; n<=7; n++) {
    const input={...baseline};
    for (const name of fields.slice(0,n)) input[name]=positive[name];
    const res=calculateTIMI(input);
    assert.equal(res.score,n);
    assert.equal(res.eventRate14dPct,RATES[n]);
  }
});
test('thresholds and invalid data', () => {
  assert.equal(calculateTIMI({...baseline,age:64}).score,0);
  assert.equal(calculateTIMI({...baseline,age:65}).score,1);
  assert.equal(calculateTIMI({...baseline,anginal_events_24h:2}).score,1);
  assert.throws(()=>calculateTIMI({...baseline,st_deviation:'maybe'}));
  assert.throws(()=>calculateTIMI({...baseline,age:-1}));
  assert.throws(()=>calculateTIMI({...baseline,cad_risk_factors:6}));
  assert.throws(()=>calculateTIMI({...baseline,age:'NaN'}));
  assert.throws(()=>calculateTIMI({age:65}));
});
test('batch quotes and neutralizes spreadsheet formulas', () => {
  const data='age,cad_risk_factors,known_cad,aspirin_last_7_days,anginal_events_24h,st_deviation,elevated_biomarkers,note\r\n65,3,yes,no,2,no,yes,"=HYPERLINK(""http://evil"",""click"")"';
  const result=processBatchCSV(data);
  assert.equal(result.count,1);
  const rows=parseCSV(result.csv);
  assert.equal(rows[1][8],'5');
  assert.equal(rows[1][9],'26.2');
  assert.match(rows[1][7],/^'=HYPERLINK/);
});
test('reject malformed and incomplete CSV', () => {
  assert.throws(()=>parseCSV('"broken'));
  assert.throws(()=>processBatchCSV('age,cad_risk_factors\n65,3'));
  assert.throws(()=>processBatchCSV('age,age\n65,65'));
});
