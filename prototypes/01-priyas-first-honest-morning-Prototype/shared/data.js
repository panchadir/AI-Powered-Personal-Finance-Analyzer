/* ============================================================================
   data.js — loads the Priya demo dataset (Scenario 01 prototype)
   Single source of truth: data/demo-data.json.
   NOTE: pages must be served over http (fetch of a local file fails on file://).
   ============================================================================ */

let _demoCache = null;

/**
 * Load and cache the demo dataset. Returns the parsed object.
 * Also sets window.DEMO for convenience in inline scripts.
 */
async function loadDemoData() {
  if (_demoCache) return _demoCache;
  try {
    const res = await fetch('data/demo-data.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    _demoCache = await res.json();
    window.DEMO = _demoCache;
    console.log('📦 Demo data loaded:', _demoCache._meta ? _demoCache._meta.scenario : '(no meta)');
    return _demoCache;
  } catch (err) {
    console.error('❌ Could not load demo-data.json — are you serving over http? ' +
      'Run:  python -m http.server 8000  in the prototype folder, then open http://localhost:8000/', err);
    throw err;
  }
}

window.loadDemoData = loadDemoData;
