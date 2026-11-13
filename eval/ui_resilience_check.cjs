// Code-only regression checks. Requires the same jsdom dependency as ui_check.cjs.
// Run: node --test eval/ui_resilience_check.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM, VirtualConsole } = require('jsdom');
const template = fs.readFileSync(path.join(__dirname, '../src/signalpost/showcase/template.html'), 'utf8');
const rows = Array.from({ length: 60 }, (_, i) => ({
  o: String(900000000 + i), n: `Company ${i}`, s: {}, k: 0, c: 0, j: 0, l: 0,
}));

function page(hash = '#/companies', saved, report = {}) {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push(e.message));
  const html = template.replace('/*__BOOT__*/null', JSON.stringify({ index: rows, report }))
    .replace('// ================================================================ boot',
      'window.testAPI = { load };\n// ================================================================ boot');
  const dom = new JSDOM(html, {
    runScripts: 'dangerously', url: 'https://example.test/' + hash, virtualConsole: vc,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false, addEventListener() {} });
      w.scrollTo = () => {};
      if (saved !== undefined) w.localStorage.setItem('sp-compare', saved);
    },
  });
  return { dom, w: dom.window, errors };
}

test('malformed shared URL keeps navigation and an unavailable-profile message', () => {
  const { dom, w, errors } = page('#/c/%E0%A4%A');
  try {
    assert.deepEqual(errors, []);
    assert.ok(w.document.querySelector('#app a[href="#/companies"]'));
    assert.ok(w.document.getElementById('nav').textContent.includes('Companies'));
  } finally { dom.window.close(); }
});

for (const saved of ['{}', '42', '"old-version"', 'null', '{broken']) {
  test(`unexpected saved comparison state does not break startup: ${saved}`, () => {
    const { dom, w, errors } = page('#/compare', saved);
    try {
      assert.deepEqual(errors, []);
      assert.ok(w.document.querySelector('#app h1'));
      assert.equal(w.document.querySelector('.cmp'), null);
    } finally { dom.window.close(); }
  });
}

test('stored comparison filters duplicates, unknown companies and excess entries', async () => {
  const saved = ['toString', null, rows[0].o, rows[0].o, ...rows.map(r => r.o)];
  const { dom, w, errors } = page('#/compare', JSON.stringify(saved));
  try {
    assert.equal(w.location.hash, '#/compare/' + rows.slice(0, 4).map(r => r.o).join(','));
    for (const script of w.document.querySelectorAll('script[src^="data/"]')) script.onerror();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(w.document.querySelectorAll('.cmp thead th').length, 5);
    assert.deepEqual(errors, []);
  } finally { dom.window.close(); }
});

for (const [input, expected] of [['1.5', 1], ['Infinity', 1], ['-2', 1], ['invalid', 1], ['9999', 2]]) {
  test(`pagination normalizes ${input} and preserves usable rows`, () => {
    const { dom, w, errors } = page('#/companies?p=' + input);
    try {
      const params = new URLSearchParams(w.location.hash.split('?')[1]);
      assert.equal(Number(params.get('p') || 1), expected);
      assert.ok(w.document.querySelectorAll('#app tbody tr').length > 0);
      assert.deepEqual(errors, []);
    } finally { dom.window.close(); }
  });
}

for (const event of ['onerror', 'onload']) {
  test(`concurrent profile consumers recover from ${event} without hanging`, { timeout: 2000 }, async () => {
    const { dom, w } = page();
    try {
      const org = rows[0].o;
      const pending = Promise.allSettled([w.testAPI.load(org), w.testAPI.load(org)]);
      const scripts = w.document.querySelectorAll('script[src^="data/"]');
      assert.equal(scripts.length, 1);
      scripts[0][event](); // onload without SP_LOAD models an incomplete or invalid data file.
      assert.ok((await pending).every(r => r.status === 'rejected'));
      const retry = w.testAPI.load(org);
      assert.equal(w.document.querySelectorAll('script[src^="data/"]').length, 1);
      w.SP_LOAD(org, { claims: [] });
      assert.equal((await retry).claims.length, 0);
    } finally { dom.window.close(); }
  });
}

for (const report of [{}, {website_diagnostics: {companies_attempted: 50, companies_with_completed_check: 42, companies_budget_unattempted: 8}}]) {
  test(`run diagnostics render with ${report.website_diagnostics ? 'new' : 'legacy'} report`, () => {
    const {dom, w, errors} = page('#/', undefined, report);
    try {
      const text = w.document.querySelector('#app').textContent;
      assert.deepEqual(errors, []);
      assert.equal(text.includes('Companies with a website check attempted'), !!report.website_diagnostics);
      if (report.website_diagnostics) assert.ok(text.includes('not precision or recall'));
      assert.ok(!text.includes('NaN'));
    } finally {dom.window.close();}
  });
}
