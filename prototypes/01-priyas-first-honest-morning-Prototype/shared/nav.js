/* ============================================================================
   nav.js — bottom navigation + linear scenario routing (Scenario 01 prototype)
   Stubbed/available in Section 1 (Register is a public page, no bottom nav).
   Used by the authenticated views (Dashboard, Transactions, Commitments, Copilot).
   ============================================================================ */

/* Linear golden-path order (page file names). */
const SCENARIO_ORDER = [
  '01.1-register.html',
  '01.2-login.html',
  '01.3-statement-upload.html',
  '01.4-transactions-table.html',
  '01.5-dashboard.html',
  '01.6-ai-insights-recommendations.html',
  '01.7-copilot-chat.html'
];

/** Navigate to the next page in the golden path. */
function goNext(currentPage) {
  const i = SCENARIO_ORDER.indexOf(currentPage);
  if (i > -1 && i < SCENARIO_ORDER.length - 1) {
    window.location.href = SCENARIO_ORDER[i + 1];
  }
}

/** Navigate directly to a page file. */
function goTo(page) { window.location.href = page; }

/**
 * Render the persistent bottom nav into #bottom-nav-slot on authenticated pages.
 * activeTab: 'home' | 'transactions' | 'commitments' | 'copilot'
 */
function renderBottomNav(activeTab) {
  const slot = document.getElementById('bottom-nav-slot');
  if (!slot) return;
  const tabs = [
    { key: 'transactions', label: 'Transactions', page: '01.4-transactions-table.html' },
    { key: 'dashboard',    label: 'Dashboard',    page: '01.5-dashboard.html' },
    { key: 'insights',     label: 'Insights',     page: '01.6-ai-insights-recommendations.html' },
    { key: 'copilot',      label: 'Copilot Chat', page: '01.7-copilot-chat.html' }
  ];
  slot.innerHTML = tabs.map(t => `
    <button class="bottom-nav__tab${t.key === activeTab ? ' is-active' : ''}"
            ${t.key === activeTab ? 'aria-current="page"' : ''}
            onclick="goTo('${t.page}')">${t.label}</button>
  `).join('');
}

/**
 * Render a persistent LEFT side nav into #side-nav-slot.
 * activeTab: 'home' | 'transactions' | 'commitments' | 'copilot'
 */
function renderSideNav(activeTab) {
  var slot = document.getElementById('side-nav-slot');
  if (!slot) return;
  var tabs = [
    { key: 'transactions', label: 'Transactions', icon: '📄', page: '01.4-transactions-table.html' },
    { key: 'dashboard',    label: 'Dashboard',    icon: '📊', page: '01.5-dashboard.html' },
    { key: 'insights',     label: 'Insights',     icon: '💡', page: '01.6-ai-insights-recommendations.html' },
    { key: 'copilot',      label: 'Copilot Chat', icon: '💬', page: '01.7-copilot-chat.html' }
  ];
  slot.innerHTML = tabs.map(function (t) {
    var active = t.key === activeTab;
    return '<button class="side-nav__tab' + (active ? ' is-active' : '') + '"' +
      (active ? ' aria-current="page"' : '') + ' onclick="goTo(\'' + t.page + '\')">' +
      '<span class="ico" aria-hidden="true">' + t.icon + '</span>' +
      '<span class="label">' + t.label + '</span></button>';
  }).join('');
}

window.goNext = goNext;
window.goTo = goTo;
window.renderBottomNav = renderBottomNav;
window.renderSideNav = renderSideNav;
