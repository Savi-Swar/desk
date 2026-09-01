"""Render Paper 1 as a self-contained, print-ready HTML (one click to PDF
for SSRN). Figures embedded as data URIs; regenerate them first with
make_figures.py.

    python papers/paper1/make_paper_html.py
"""
import base64
import pathlib
import re

import markdown

HERE = pathlib.Path(__file__).parent
FIGS = [("fig1_calibration.png",
         "Figure 1 — Calibration by category, pinned marks excluded."),
        ("fig2_collapse.png",
         "Figure 2 — One effect, three inferences: regimes fake independence."),
        ("fig3_politics_strip.png",
         "Figure 3 — Politics favorites, monthly gap: train (dark) vs "
         "test (red).")]

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
    # title = the H1 of the draft
    m = re.search(r"^# (.+)$", md, flags=re.M)
    title = m.group(1).strip() if m else "Paper 1"
    # drop the italic draft-status paragraph for the rendered paper
    md = re.sub(r"^\*Draft v[^*]*\*\s*$", "", md, flags=re.M | re.S)
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
            f"<title>{title}</title>"
            f"<style>{CSS}</style>\n"
            f"<div class='meta'>Savitur Swarup · University of Pennsylvania ·"
            f" working paper · September 2026 ·"
            f" code &amp; data: github.com/Savi-Swar/desk</div>\n"
            + body + "\n<h2>Figures</h2>\n" + figs_html)
    out = HERE / "paper1.html"
    out.write_text(html)
    print(f"wrote {out} ({len(html)//1024} KB) — open and print to PDF for SSRN")


if __name__ == "__main__":
    main()
