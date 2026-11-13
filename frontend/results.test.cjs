const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');

function screen() {
  const elements = new Map();
  function element() {
    return { textContent: '', className: '', children: [], hidden: false,
      replaceChildren(...children) { this.children = children; },
      append(...children) { this.children.push(...children); }, focus() {} };
  }
  const context = vm.createContext({ document: {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement: element, querySelectorAll: () => [],
  }});
  const source = fs.readFileSync(`${__dirname}/app.js`, 'utf8');
  vm.runInContext(source.replace(/initialise\(\);\s*$/, ''), context);
  return { context, get: id => elements.get(id) };
}

function job({ watermark = false, claim = false, score = 0.343, failed = false } = {}) {
  return { id: 'test', source_name: 'test.png', sha256: 'abc', status: 'completed',
    result: { media: { width: 100, height: 100 }, frames: [], modules: [
      { module: 'media_authenticity', status: failed ? 'failed' : 'completed', findings: failed ? {} : {
        assessment: watermark ? 'strong_ai_origin_evidence' : claim ? 'unverified_ai_origin_claim' : 'inconclusive',
        visible_watermark: { candidate_detected: watermark }, provenance: { ai_origin_claim_detected: claim },
      } },
      { module: 'deepfake_detection', status: score == null ? 'skipped' : 'completed', findings: score == null ? {} : {
        deepfake_probability: score, analysed_faces: 1, decision: 'evaluation_pending',
      } },
      { module: 'image_forensics', status: 'failed', findings: {} },
    ] } };
}

test('no watermark keeps the face percentage and missing LSB is not a negative', () => {
  const ui = screen();
  ui.context.job = job();
  vm.runInContext('renderResult(job)', ui.context);
  assert.equal(ui.get('riskScore').textContent, '34.3%');
  assert.equal(ui.get('lsbSummary').textContent, 'Not evaluated');
});

test('watermark keeps strong evidence and the independent model score', () => {
  const ui = screen();
  ui.context.job = job({ watermark: true, score: 0.068 });
  vm.runInContext('renderResult(job)', ui.context);
  assert.equal(ui.get('riskScore').textContent, 'Strong AI-origin evidence');
  assert.equal(ui.get('modelSignal').children[0].textContent, '6.8%');
});

test('unverified text is not promoted to strong evidence', () => {
  const ui = screen();
  ui.context.job = job({ claim: true });
  vm.runInContext('renderResult(job)', ui.context);
  assert.equal(ui.get('riskScore').textContent, '34.3%');
  assert.equal(ui.get('riskDecision').textContent, 'Unverified AI-origin claim');
});

test('failed modules and no face cannot claim a negative or a sampled-face count', () => {
  const ui = screen();
  ui.context.job = job({ failed: true, score: null });
  ui.context.job.result.frames = [{ frame_index: 1, timestamp_seconds: 0, artifact: { path: '/artifacts/a.jpg' } }];
  vm.runInContext('renderResult(job)', ui.context);
  assert.equal(ui.get('frameSummary').textContent, 'Not evaluated');
  assert.equal(ui.get('originSignal').children[0].textContent, 'Not evaluated');
  assert.equal(ui.get('riskScore').textContent, 'Unavailable');
  assert.doesNotMatch(ui.get('moduleList').children[0].innerHTML, /No known watermark/);
});

test('metadata preserves untrusted EXIF as text and handles older cases', () => {
  const ui = screen();
  ui.context.metadata = { format: 'JPEG', exif: { Software: '<img src=x onerror=alert(1)>' } };
  vm.runInContext('renderMetadata(metadata)', ui.context);
  const rows = ui.get('metadataList').children;
  assert.equal(rows.length, 2);
  assert.equal(rows[1].children[0].textContent, 'exif / Software');
  assert.equal(rows[1].children[1].textContent, '<img src=x onerror=alert(1)>');
  vm.runInContext('renderMetadata(undefined)', ui.context);
  assert.equal(ui.get('metadataList').children[0].children[1].textContent, 'No metadata available for this case');
});

test('history combines case ID or filename search with status', () => {
  const ui = screen();
  ui.context.jobs = [
    { id: 'ab12', source_name: 'Clip.MOV', status: 'completed' },
    { id: 'ab34', source_name: 'Image.PNG', status: 'failed' },
  ];
  const ids = expression => Array.from(vm.runInContext(expression, ui.context), item => item.id);
  assert.deepEqual(ids('filterHistory(jobs, " CLIP ", "")'), ['ab12']);
  assert.deepEqual(ids('filterHistory(jobs, "AB", "failed")'), ['ab34']);
  assert.deepEqual(ids('filterHistory(jobs, "clip", "failed")'), []);
});

test('opening an unfinished case does not report failure', () => {
  const ui = screen();
  ui.context.job = { ...job(), status: 'processing', result: null };
  vm.runInContext('renderResult(job)', ui.context);
  assert.match(ui.get('warningList').innerHTML, /still running/);
  assert.equal(ui.get('reportActions').hidden, true);
});
