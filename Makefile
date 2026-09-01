# entry points — everything a reviewer might want to reproduce
test:            ## run the full test suite (same as CI)
	python3 tests/run_all.py
figures:         ## regenerate every paper figure from ledgers on disk
	python3 papers/paper0/make_figures.py
	python3 papers/paper1/make_figures.py
paper0:          ## build the print-ready paper 0 HTML
	python3 papers/paper0/make_paper_html.py
paper1:          ## build the print-ready paper 1 HTML
	python3 papers/paper1/make_paper_html.py
pnl:             ## recompute the maker P&L ledger from real fills
	python3 maker_pnl_real.py
study:           ## rerun the calibration study + verdict
	python3 study_longshot.py
bookmid:         ## build + parity-test the C++ book reconstructor
	python3 tests/test_bookmid.py
.PHONY: test figures paper0 paper1 pnl study bookmid
