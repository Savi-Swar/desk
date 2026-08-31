"""Render Paper 0 as a self-contained, print-ready HTML (one click to PDF
for SSRN). Figures embedded as data URIs; regenerate them first with
make_figures.py.

    python papers/paper0/make_paper_html.py
"""
import base64
import pathlib

import markdown

HERE = pathlib.Path(__file__).parent
FIGS = [("fig1_fill_overcount.png",
         "Figure 1 — Shrinkage 'fills' vs real prints (log scale)."),
        ("fig2_decomposition.png",
         "Figure 2 — Markout decomposition by half-spread at fill."),
        ("fig3_reprice.png",
         "Figure 3 — The edge exists only at the touch you never rest at.")]

CSS = """
@page { size: letter; margin: 2.4cm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11.5pt;
       line-height: 1.45; max-width: 42em; margin: 2em auto; color: #111; }
h1 { font-size: 17pt; line-height: 1.25; }
h2 { font-size: 13pt; margin-top: 1.6em; }
table { border-collapse: collapse; margin: 1em 0; font-size: 10.5pt; }
td, th { border: 1px solid #999; padding: 3px 9px; text-align: right; }
td:first-child, th:first-child { text-align: left; }
figure { margin: 1.4em 0; text-align: center; page-break-inside: avoid; }
img { max-width: 88%; }
figcaption { font-size: 9.5pt; color: #444; margin-top: .4em; }
.meta { color: #444; font-size: 10.5pt; margin-bottom: 2em; }
@media print { body { margin: 0; } }
"""


def main():
    md = (HERE / "DRAFT.md").read_text()
    # drop the draft-status line for the rendered paper
    md = md.replace("*Draft v0.1 — every number regenerates from the repo "
                    "(`make_figures.py`,\n`taq_benchmark.py`, "
                    "`benchmark_table.py`). Prose is a working skeleton.*", "")
    body = markdown.markdown(md, extensions=["tables"])
    figs_html = ""
    for fn, cap in FIGS:
        f = HERE / fn
        if not f.exists():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        figs_html += (f'<figure><img src="data:image/png;base64,{b64}">'
                      f"<figcaption>{cap}</figcaption></figure>\n")
    html = (f"<!doctype html><meta charset='utf-8'>"
            f"<title>The maker edge that wasn't</title>"
            f"<style>{CSS}</style>\n"
            f"<div class='meta'>Savitur Swarup · University of Pennsylvania ·"
            f" working paper · September 2026 ·"
            f" code &amp; data: github.com/Savi-Swar/desk</div>\n"
            + body + "\n<h2>Figures</h2>\n" + figs_html)
    out = HERE / "paper0.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html)//1024} KB) — open and print to PDF for SSRN")


if __name__ == "__main__":
    main()
