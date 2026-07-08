/* ============================================================================
   format.js — currency + date formatting helpers (Scenario 01 prototype)
   ============================================================================ */

/**
 * Format a number as Indian Rupees with Indian digit grouping.
 * formatINR(2840)    -> "₹2,840"
 * formatINR(1800000) -> "₹18,00,000"
 * formatINR(-640)    -> "-₹640"
 */
function formatINR(amount) {
  const n = Number(amount) || 0;
  const sign = n < 0 ? '-' : '';
  const grouped = Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  return sign + '₹' + grouped;
}

/**
 * Format an ISO date string.
 * formatDate('2026-06-30')          -> "30 Jun 2026"
 * formatDate('2026-06-30', 'short') -> "30 Jun"
 */
function formatDate(iso, style) {
  if (!iso) return '';
  const d = new Date(iso + (iso.length === 10 ? 'T00:00:00' : ''));
  if (isNaN(d)) return iso;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const day = d.getDate();
  const mon = months[d.getMonth()];
  if (style === 'short') return `${day} ${mon}`;
  return `${day} ${mon} ${d.getFullYear()}`;
}

// Expose globally for inline page scripts.
window.formatINR = formatINR;
window.formatDate = formatDate;
