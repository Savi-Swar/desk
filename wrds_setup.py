"""One-time WRDS credential setup + capability inventory.

Run this YOURSELF (it prompts for your WRDS username/password and offers to
store a ~/.pgpass so future sessions connect without typing anything):

    ~/lab/wrds-env/bin/python wrds_setup.py

After the login it prints which libraries Penn's subscription actually grants
(taqmsec? crsp? optionm?) — that inventory decides what the desk can use WRDS
for, so paste it back into the session.
"""
import wrds

db = wrds.Connection()          # prompts for user/pass; offers .pgpass save
libs = sorted(db.list_libraries())
print(f"\n{len(libs)} libraries granted. The ones that matter for the plan:")
WANT = {
    "taqmsec": "TAQ millisecond trades/quotes — equity microstructure benchmark for Paper 0",
    "taqm": "TAQ monthly aggregates",
    "crsp": "CRSP daily equities — classical validation sleeve",
    "optionm": "OptionMetrics — implied-prob calibration comparison",
    "ibes": "I/B/E/S analyst forecasts",
    "comp": "Compustat fundamentals",
}
for k, why in WANT.items():
    hit = [l for l in libs if l.startswith(k)]
    print(f"  [{'YES' if hit else ' - '}] {k:10s} {why}" + (f"  -> {hit[:3]}" if hit else ""))
print("\nfull list:", ", ".join(libs))
db.close()
