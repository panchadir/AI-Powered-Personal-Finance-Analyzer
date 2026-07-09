/* ============================================================================
   nav.js — left sidebar navigation + linear scenario routing (prototype)
   Desktop-only left sidebar, used by all authenticated views
   (Dashboard, Transactions, Insights, Copilot).
   Commitments is NOT a sidebar item (2026-07-09) — reached only via the
   Dashboard's "+ Add a commitment" button, matching FR-6.4's 4-screen nav.
   ============================================================================ */

/* Linear golden-path order (page file names). Dashboard is the landing page
   immediately after Upload; Transactions is reached from the Dashboard's
   "View All Transactions" CTA or the sidebar, not automatically post-upload. */
const SCENARIO_ORDER = [
  '01.1-register.html',
  '01.2-login.html',
  '01.3-statement-upload.html',
  '01.5-dashboard.html',
  '01.4-transactions-table.html',
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
 * Render the persistent LEFT sidebar nav into #side-nav-slot.
 * Nav order per ux-spec-mvp.md FR-6.4 / epics.md: Dashboard, Transactions, Insights, Copilot.
 * Commitments is intentionally not a sidebar item — reached via the Dashboard's
 * "+ Add a commitment" button (02.1-commitments-management.html renders this same
 * sidebar with no active tab, since it isn't one of the 4 primary destinations).
 * activeTab: 'dashboard' | 'transactions' | 'insights' | 'copilot'
 */
function renderSideNav(activeTab) {
  var slot = document.getElementById('side-nav-slot');
  if (!slot) return;
  var tabs = [
    { key: 'dashboard',    label: 'Dashboard',    icon: '📊', page: '01.5-dashboard.html' },
    { key: 'transactions', label: 'Transactions', icon: '📄', page: '01.4-transactions-table.html' },
    { key: 'insights',     label: 'Insights',     icon: '💡', page: '01.6-ai-insights-recommendations.html' },
    { key: 'copilot',      label: 'Copilot Chat', icon: '💬', page: '01.7-copilot-chat.html' }
  ];
  var items = tabs.map(function (t) {
    var active = t.key === activeTab;
    return '<button class="side-nav__tab' + (active ? ' is-active' : '') + '"' +
      (active ? ' aria-current="page"' : '') + ' onclick="goTo(\'' + t.page + '\')">' +
      '<span class="ico" aria-hidden="true">' + t.icon + '</span>' +
      '<span class="label">' + t.label + '</span></button>';
  }).join('');
  // Logout pinned to the bottom of the rail
  items += '<button class="side-nav__tab side-nav__logout" onclick="Auth.logout()">' +
    '<span class="ico" aria-hidden="true">⏻</span><span class="label">Log out</span></button>';
  slot.innerHTML = items;
}

window.goNext = goNext;
window.goTo = goTo;
window.renderSideNav = renderSideNav;
