# --- appended to _harness.py -------------------------------------------------
"""Ingestion timing: PDF parse (the real bank statement in data/), CSV parse, persist."""
import cProfile
import io
import pstats
import sys
from pathlib import Path

from services.ingestion.csv_parser import CSVParser
from services.ingestion.dispatch import parse_statement
from services.ingestion.pdf_parser import PDFParser
from services.ingestion.persist import persist_transactions
from services.categorize.rules import categorize_rules

out = {}

PDF = Path("/app/data/OpTransactionHistory10-07-2026_3625 1.pdf")
out["pdf_exists"] = PDF.exists()
out["pdf_size_bytes"] = PDF.stat().st_size if PDF.exists() else None

# How many pages? (context for whether this is a "representative multi-page statement")
import pdfplumber  # noqa: E402

t = time.perf_counter()
with pdfplumber.open(str(PDF)) as pdf:
    out["pdf_pages"] = len(pdf.pages)
out["pdfplumber_open_only_ms"] = round((time.perf_counter() - t) * 1000, 1)

# ---- 1. Full PDF parse, end to end (the dispatch path the upload handler uses) ----
data = PDF.read_bytes()


def _parse_pdf():
    return parse_statement(PDF.name, data)


txns = _parse_pdf()
out["pdf_transactions_parsed"] = len(txns)
out["pdf_parse"] = timeit(_parse_pdf, runs=3)

# Which extractor actually won? Time each in the fallback chain to see the cost of the
# chain itself (a failed extractor still costs its full attempt before falling through).
parser = PDFParser()
chain = []
for extractor in parser._extractors if hasattr(parser, "_extractors") else []:
    t = time.perf_counter()
    try:
        rows = extractor.extract(PDF)
        ok, n, err = True, len(rows), None
    except Exception as e:  # noqa: BLE001
        ok, n, err = False, 0, repr(e)[:120]
    chain.append(
        {
            "extractor": getattr(extractor, "name", type(extractor).__name__),
            "ms": round((time.perf_counter() - t) * 1000, 1),
            "ok": ok,
            "rows": n,
            "error": err,
        }
    )
out["pdf_extractor_chain"] = chain

# ---- 2. cProfile the PDF parse ------------------------------------------------
pr = cProfile.Profile()
pr.enable()
_parse_pdf()
pr.disable()
sio = io.StringIO()
pstats.Stats(pr, stream=sio).sort_stats("cumulative").print_stats(14)
out["cprofile_pdf_parse"] = sio.getvalue()

# ---- 3. CSV parse, for contrast ------------------------------------------------
csv_text = "Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
rows = []
bal = 100000.0
for i in range(500):
    bal -= 100
    rows.append(f"0{(i % 9) + 1}/07/26,UPI-SWIGGY-{i},100.00,,{bal:.2f}")
csv_bytes = (csv_text + "\n".join(rows)).encode()


def _parse_csv():
    return parse_statement("statement.csv", csv_bytes)


csv_txns = _parse_csv()
out["csv_rows_parsed"] = len(csv_txns)
out["csv_parse_500_rows"] = timeit(_parse_csv, runs=5)

# ---- 4. The full upload pipeline as the handler runs it -------------------------
# parse -> rule-categorize -> persist  (LLM tier-2 excluded; measured separately)
with rx.session() as s:
    uid = get_perf_user(s)


def _full_upload_pipeline():
    parsed = parse_statement(PDF.name, data)
    categorized = categorize_rules(parsed)
    with rx.session() as s:
        # roll back by deleting after, so repeated runs measure the same work
        return persist_transactions(s, TxnModel, uid, None, categorized)


with rx.session() as s:
    set_transaction_count(s, uid, 0)

t = time.perf_counter()
with count_queries() as q:
    res = _full_upload_pipeline()
first_ms = (time.perf_counter() - t) * 1000
out["full_upload_pipeline_pdf (parse+rules+persist)"] = {
    "cold_ms": round(first_ms, 2),
    "inserted": res.inserted,
    "skipped": res.skipped,
    "sql": summarize_queries(list(q)),
    "note": "excludes the Tier-2 Haiku LLM call, which the upload handler also makes",
}

with rx.session() as s:
    set_transaction_count(s, uid, 100)
    ensure_commitments(s, uid)

emit(out)
