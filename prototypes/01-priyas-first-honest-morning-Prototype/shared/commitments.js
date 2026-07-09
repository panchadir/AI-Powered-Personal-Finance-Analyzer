/* ============================================================================
   commitments.js — shared, persisted commitment state (Scenario 01/02 prototype)
   Single source of truth for "protected" commitments across the Dashboard
   (01.5) and the Commitments Management page (02.1), so adding/editing/
   deleting a commitment on one page is reflected on the other.
   Persisted client-side only (localStorage) — no backend in the prototype.
   ============================================================================ */

var Commitments = (function () {
  var KEY = 'afc_commitments';
  // Reference month for the demo dataset's upcoming commitments ("this month" = July 2026).
  var REF_YEAR = 2026, REF_MONTH = 7;

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function daysInMonth(year, month) { return new Date(year, month, 0).getDate(); }

  function dateForDueDay(dueDay) {
    var d = Math.min(Number(dueDay) || 1, daysInMonth(REF_YEAR, REF_MONTH));
    return REF_YEAR + '-' + pad2(REF_MONTH) + '-' + pad2(d);
  }
  function dueDayFromDate(iso) { return iso ? Number(iso.slice(8, 10)) : 1; }

  /** Seed the persisted list from the demo dataset's real (amount > 0) commitments. */
  function seed(baseCommitments) {
    return (baseCommitments || [])
      .filter(function (c) { return c.amount > 0; })
      .map(function (c) {
        return {
          id: c.id, name: c.name, amount: c.amount,
          due_day: dueDayFromDate(c.date), date: c.date, date_label: c.date_label,
          criticality: c.criticality || 'Critical', userAdded: false
        };
      });
  }

  function save(list) { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {} }

  /** Load the persisted list, seeding it from demo data on first run. */
  function load(baseCommitments) {
    var raw = null;
    try { raw = localStorage.getItem(KEY); } catch (e) {}
    if (raw) { try { return JSON.parse(raw); } catch (e) {} }
    var list = seed(baseCommitments);
    save(list);
    return list;
  }

  /** Add a commitment ({ name, amount, due_day, criticality }); returns the new list. */
  function add(list, item) {
    var date = dateForDueDay(item.due_day);
    list.push({
      id: 'c_' + Date.now(),
      name: item.name,
      amount: Number(item.amount),
      due_day: Number(item.due_day),
      date: date,
      date_label: (window.formatDate ? formatDate(date, 'short') : date),
      criticality: item.criticality,
      userAdded: true
    });
    save(list);
    return list;
  }

  /** Patch an existing commitment by id ({ name?, amount?, due_day?, criticality? }); returns the new list. */
  function update(list, id, patch) {
    list = list.map(function (c) {
      if (c.id !== id) return c;
      var next = {};
      for (var k in c) next[k] = c[k];
      for (var k2 in patch) next[k2] = patch[k2];
      if (patch.due_day) {
        next.due_day = Number(patch.due_day);
        next.date = dateForDueDay(next.due_day);
        next.date_label = (window.formatDate ? formatDate(next.date, 'short') : next.date);
      }
      if (patch.amount) next.amount = Number(patch.amount);
      return next;
    });
    save(list);
    return list;
  }

  /** Remove a commitment by id; returns the new list. */
  function remove(list, id) {
    list = list.filter(function (c) { return c.id !== id; });
    save(list);
    return list;
  }

  function total(list) { return list.reduce(function (a, c) { return a + c.amount; }, 0); }

  return { load: load, save: save, add: add, update: update, remove: remove, total: total };
})();

window.Commitments = Commitments;
