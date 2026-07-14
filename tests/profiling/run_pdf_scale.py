# --- appended to _harness.py -------------------------------------------------
"""PDF parse latency vs page count -- is a long multi-page statement over 3s?

Builds larger statements by repeating the real 5-page bank statement's pages with PyMuPDF,
so the page content is genuinely representative (same fonts/layout the parser must handle),
then times the real dispatch path.
"""
import sys
from pathlib import Path

import fitz  # PyMuPDF

from services.ingestion.dispatch import parse_statement
from services.ingestion.pdf_parser import PDFParser

SRC = Path("/app/data/OpTransactionHistory10-07-2026_3625 1.pdf")
out = {"source_pages": None, "curve": [], "fallthrough": {}}

src = fitz.open(str(SRC))
out["source_pages"] = src.page_count

TMP = Path("/tmp/pdfscale")
TMP.mkdir(exist_ok=True)


def build(target_pages: int) -> bytes:
    doc = fitz.open()
    while doc.page_count < target_pages:
        doc.insert_pdf(src)
    # trim to exactly target_pages
    if doc.page_count > target_pages:
        doc.delete_pages(range(target_pages, doc.page_count))
    p = TMP / f"stmt_{target_pages}p.pdf"
    doc.save(str(p))
    doc.close()
    return p.read_bytes()


for pages in [5, 10, 20, 40, 60]:
    data = build(pages)

    def _parse(d=data):
        return parse_statement(f"stmt_{pages}p.pdf", d)

    txns = _parse()
    t = timeit(_parse, runs=3)
    row = {
        "pages": pages,
        "bytes": len(data),
        "transactions": len(txns),
        "cold_ms": t["cold_ms"],
        "p50_ms": t["warm_p50_ms"],
        "max_ms": t["warm_max_ms"],
        "over_3s": t["warm_p50_ms"] > 3000,
    }
    out["curve"].append(row)
    print(f"[pdf] {pages}p -> {len(txns)} txns, p50 {t['warm_p50_ms']:.0f}ms", file=sys.stderr)

# ---- Worst case: what if the FIRST extractor doesn't match this bank's format? ----
# The chain tries each extractor in order; a miss costs its full attempt before falling
# through. Measure the cost of the chain when the early extractors are skipped.
from services.ingestion.pdf_parser import (  # noqa: E402
    CamelotExtractor,
    HDFCTableExtractor,
    PdfplumberExtractor,
)

data5 = build(5)
p5 = TMP / "stmt_5p.pdf"

# A parser whose chain must fall all the way through to camelot (simulates a bank format
# none of the earlier extractors handle).
late_chain = PDFParser(extractors=[HDFCTableExtractor(), PdfplumberExtractor(), CamelotExtractor()])
t = time.perf_counter()
try:
    rows = late_chain.parse(p5)
    n, err = len(rows), None
except Exception as e:  # noqa: BLE001
    n, err = 0, repr(e)[:150]
out["fallthrough"]["late_chain_5p_ms"] = round((time.perf_counter() - t) * 1000, 1)
out["fallthrough"]["late_chain_rows"] = n
out["fallthrough"]["late_chain_error"] = err

emit(out)
