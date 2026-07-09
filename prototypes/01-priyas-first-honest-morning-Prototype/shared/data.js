/* ============================================================================
   data.js — loads the Priya demo dataset (Scenario 01 prototype)
   Primary source: data/demo-data.json (fetched over http).
   Fallback: FALLBACK_DEMO_DATA below — an identical copy, embedded inline, used
   automatically if the fetch fails (e.g. pages opened via file:// instead of a
   local server, where fetch() of a local JSON file is blocked by the browser).
   This guarantees every page always has data to render, not a blank/₹0 screen.
   ============================================================================ */

let _demoCache = null;

/** Embedded fallback copy of data/demo-data.json — keep in sync if that file changes. */
const FALLBACK_DEMO_DATA = {
  "_meta": {
    "scenario": "01 - Priya's First Honest Morning",
    "description": "Realistic demo dataset for the golden-path prototype (embedded fallback copy).",
    "generated": "2026-07-08",
    "currency": "INR",
    "currency_symbol": "₹",
    "honesty_note": "Confidence is On track because there is exactly 1 month of data. Freshness caveats must reference statement_date everywhere."
  },
  "user": {
    "first_name": "Priya",
    "last_name": "Sharma",
    "email": "priya.sharma@example.com",
    "city": "Mumbai",
    "monthly_income_estimate": 65000,
    "salary_day": 1,
    "avatar_initials": "PS"
  },
  "statement": {
    "bank_name": "HDFC Bank",
    "account_last4": "4821",
    "statement_date": "2026-06-30",
    "statement_label": "June 2026",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "opening_balance": 43120,
    "closing_balance": 25040,
    "filename": "HDFC_Statement_Jun2026.pdf",
    "transactions_total": 24,
    "parsed_by_rules": 18,
    "parsed_by_ai": 3,
    "transactions_need_review": 3,
    "salary_detected": true,
    "salary_amount": 65000,
    "salary_date": "2026-06-01"
  },
  "safe_to_spend": {
    "today": 2840,
    "after_salary": 8200,
    "current_balance": 25040,
    "ring_fenced_emis": 18000,
    "ring_fenced_recurring": 4200,
    "why_today": "Your ₹2,840 is what's left after your 3 upcoming EMIs (₹18,000) and your recurring bills (₹4,200) are ring-fenced from your current balance of ₹25,040.",
    "why_after_salary": "After your salary of ₹65,000 lands on 1 Jul and this month's committed amounts are set aside, about ₹8,200/day is comfortable through the month."
  },
  "confidence": {
    "level": "On track",
    "variant": "amber",
    "months_of_data": 1,
    "tooltip": "On track: we have one month of data. More months = higher confidence in your patterns.",
    "note": "Label only — the raw Confidence Score is never rendered (epics.md Story 5.1 / FR-5.5)."
  },
  "score_events": [
    { "id": "se1", "delta": "+4", "explanation": "3 EMIs matched against your commitments", "when": "2 hours ago" },
    { "id": "se2", "delta": "+3", "explanation": "First bank statement parsed — 24 transactions categorised", "when": "5 hours ago" },
    { "id": "se3", "delta": "+2", "explanation": "Account verified and statement upload completed", "when": "1 day ago" },
    { "id": "se4", "delta": "0", "explanation": "Confidence Score starts at a neutral baseline for new accounts", "when": "1 day ago" }
  ],
  "briefing": {
    "greeting_name": "Priya",
    "text": "Your biggest spend this month was food (₹7,200 — up from ₹5,100 last month). Your EMIs are on track. You have ₹2,840 you can spend today without touching your committed amounts."
  },
  "spending_by_category": [
    { "category": "Food & Dining", "amount": 7200, "percent": 28, "color": "#10796b", "prev_month": 5100 },
    { "category": "EMIs", "amount": 18000, "percent": 32, "color": "#26413f", "prev_month": 18000 },
    { "category": "Bills & Utilities", "amount": 4200, "percent": 12, "color": "#e0a63c", "prev_month": 4050 },
    { "category": "Transport", "amount": 3100, "percent": 9, "color": "#5aa9a0", "prev_month": 2800 },
    { "category": "Subscriptions", "amount": 1450, "percent": 5, "color": "#9ec7bf", "prev_month": 1450 },
    { "category": "Shopping", "amount": 2600, "percent": 8, "color": "#d98c5f", "prev_month": 1900 },
    { "category": "Other", "amount": 1650, "percent": 6, "color": "#c4d3cf", "prev_month": 1200 }
  ],
  "commitments": [
    { "id": "c1", "date": "2026-07-15", "date_label": "15 Jul", "name": "HDFC EMI", "amount": 8500, "criticality": "Critical" },
    { "id": "c2", "date": "2026-07-05", "date_label": "5 Jul", "name": "Car Loan EMI", "amount": 6500, "criticality": "Critical" },
    { "id": "c3", "date": "2026-07-10", "date_label": "10 Jul", "name": "Personal Loan EMI", "amount": 3000, "criticality": "Critical" }
  ],
  "transactions": [
    { "id": "t1", "date": "2026-06-01", "merchant": "ACME Corp Salary", "amount": 65000, "type": "credit", "category": "Income", "confidence": "confident" },
    { "id": "t2", "date": "2026-06-02", "merchant": "Zomato", "amount": -640, "type": "debit", "category": "Food & Dining", "confidence": "confident" },
    { "id": "t3", "date": "2026-06-03", "merchant": "BEST Bus Pass", "amount": -900, "type": "debit", "category": "Transport", "confidence": "confident" },
    { "id": "t4", "date": "2026-06-04", "merchant": "UPI-8847213", "amount": -1200, "type": "debit", "category": "Uncategorized", "confidence": "needs_review", "guess": "Shopping" },
    { "id": "t5", "date": "2026-06-05", "merchant": "Car Loan EMI", "amount": -6500, "type": "debit", "category": "EMIs", "confidence": "confident" },
    { "id": "t6", "date": "2026-06-06", "merchant": "Netflix", "amount": -649, "type": "debit", "category": "Subscriptions", "confidence": "confident" },
    { "id": "t7", "date": "2026-06-07", "merchant": "Swiggy", "amount": -520, "type": "debit", "category": "Food & Dining", "confidence": "confident" },
    { "id": "t8", "date": "2026-06-08", "merchant": "BigBasket", "amount": -2340, "type": "debit", "category": "Food & Dining", "confidence": "ai", "note": "AI-categorized" },
    { "id": "t9", "date": "2026-06-10", "merchant": "Personal Loan EMI", "amount": -3000, "type": "debit", "category": "EMIs", "confidence": "confident" },
    { "id": "t10", "date": "2026-06-11", "merchant": "PVR Cinemas", "amount": -900, "type": "debit", "category": "Entertainment", "confidence": "confident" },
    { "id": "t11", "date": "2026-06-12", "merchant": "NEFT-REF-99120", "amount": -1650, "type": "debit", "category": "Uncategorized", "confidence": "needs_review", "guess": "Other" },
    { "id": "t12", "date": "2026-06-13", "merchant": "Uber", "amount": -410, "type": "debit", "category": "Transport", "confidence": "confident" },
    { "id": "t13", "date": "2026-06-14", "merchant": "Amazon", "amount": -1400, "type": "debit", "category": "Shopping", "confidence": "ai", "note": "AI-categorized" },
    { "id": "t14", "date": "2026-06-15", "merchant": "HDFC EMI", "amount": -8500, "type": "debit", "category": "EMIs", "confidence": "confident" },
    { "id": "t15", "date": "2026-06-16", "merchant": "Tata Power", "amount": -1850, "type": "debit", "category": "Bills & Utilities", "confidence": "confident" },
    { "id": "t16", "date": "2026-06-17", "merchant": "Zomato", "amount": -730, "type": "debit", "category": "Food & Dining", "confidence": "confident" },
    { "id": "t17", "date": "2026-06-18", "merchant": "PhonePe-Merchant", "amount": -560, "type": "debit", "category": "Uncategorized", "confidence": "needs_review", "guess": "Food & Dining" },
    { "id": "t18", "date": "2026-06-19", "merchant": "Jio Recharge", "amount": -399, "type": "debit", "category": "Bills & Utilities", "confidence": "confident" },
    { "id": "t19", "date": "2026-06-20", "merchant": "Spotify", "amount": -119, "type": "debit", "category": "Subscriptions", "confidence": "confident" },
    { "id": "t20", "date": "2026-06-21", "merchant": "Starbucks", "amount": -480, "type": "debit", "category": "Food & Dining", "confidence": "confident" },
    { "id": "t21", "date": "2026-06-23", "merchant": "Myntra", "amount": -1200, "type": "debit", "category": "Shopping", "confidence": "ai", "note": "AI-categorized" },
    { "id": "t22", "date": "2026-06-25", "merchant": "Reliance Digital", "amount": -283, "type": "debit", "category": "Bills & Utilities", "confidence": "confident" },
    { "id": "t23", "date": "2026-06-27", "merchant": "Swiggy Instamart", "amount": -690, "type": "debit", "category": "Food & Dining", "confidence": "confident" },
    { "id": "t24", "date": "2026-06-29", "merchant": "Uber", "amount": -390, "type": "debit", "category": "Transport", "confidence": "confident" }
  ],
  "insights": [
    {
      "id": "i1",
      "icon": "🍽️",
      "pattern_name": "Food spending climbed this month",
      "observation": "Your food spending went up compared with last month.",
      "evidence": [
        "June food: ₹7,200 across 8 transactions",
        "May food: ₹5,100",
        "Largest single spend: BigBasket ₹2,340 on 8 Jun"
      ],
      "explanation": "This is common in a busy month — more delivery, more groceries. It's only a concern if it leaves you short by month-end, and right now your Safe-to-Spend still holds.",
      "action_suggestion": "You might consider a simple food budget for July — want me to help set one?",
      "confidence": "High",
      "copilot_prompt": "Tell me more about my food spending this month"
    },
    {
      "id": "i2",
      "icon": "🔁",
      "pattern_name": "Two streaming subscriptions running",
      "observation": "You're paying for two streaming subscriptions each month.",
      "evidence": [
        "Netflix ₹649 on 6 Jun",
        "Spotify ₹119 on 20 Jun",
        "Combined: ₹768/month recurring"
      ],
      "explanation": "Small recurring charges are easy to lose track of on a busy month. Only you know if you're actively using both — we're just surfacing what we see.",
      "action_suggestion": "You might want to check whether you're still using both — want to review your subscriptions?",
      "confidence": "High",
      "copilot_prompt": "Tell me more about my subscriptions"
    }
  ],
  "copilot_samples": [
    {
      "question": "Can I afford to spend ₹2,000 on dinner this weekend?",
      "verdict": "Stretch",
      "answer": "You have ₹2,840 safe to spend today. ₹2,000 fits, but it would leave you ₹840 until your salary on 1 Jul. It's doable — just tight.",
      "data_trace": ["Safe-to-spend today: ₹2,840", "Next salary: 1 Jul"]
    },
    {
      "question": "How much did I spend on food last month?",
      "verdict": null,
      "answer": "You spent ₹7,200 on food in June across 8 transactions. That's up from ₹5,100 in May.",
      "data_trace": ["Food & Dining category total: ₹7,200", "8 food transactions in June"]
    },
    {
      "question": "What are my biggest upcoming bills?",
      "verdict": null,
      "answer": "Your 3 EMIs total ₹18,000 in the first half of July: Car Loan ₹6,500 (5 Jul), Personal Loan ₹3,000 (10 Jul), HDFC EMI ₹8,500 (15 Jul).",
      "data_trace": ["3 EMIs detected", "Total ₹18,000"]
    }
  ]
};

/**
 * Load and cache the demo dataset. Returns the parsed object.
 * Also sets window.DEMO for convenience in inline scripts.
 * Falls back to the embedded FALLBACK_DEMO_DATA if the fetch fails for any
 * reason (most commonly: the page was opened directly via file:// instead of
 * a local server, where fetch() of a same-folder JSON file is blocked).
 */
async function loadDemoData() {
  if (_demoCache) return _demoCache;
  try {
    const res = await fetch('data/demo-data.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    _demoCache = await res.json();
    window.DEMO = _demoCache;
    console.log('📦 Demo data loaded from data/demo-data.json:', _demoCache._meta ? _demoCache._meta.scenario : '(no meta)');
    return _demoCache;
  } catch (err) {
    console.warn('⚠️ Could not fetch data/demo-data.json (are you opening this file directly instead of via a local server?). ' +
      'Falling back to the embedded demo dataset so the page still shows data. ' +
      'Run:  python -m http.server 8000  in the prototype folder, then open http://localhost:8000/ for the real fetch path.', err);
    _demoCache = FALLBACK_DEMO_DATA;
    window.DEMO = _demoCache;
    return _demoCache;
  }
}

window.loadDemoData = loadDemoData;
window.FALLBACK_DEMO_DATA = FALLBACK_DEMO_DATA;
