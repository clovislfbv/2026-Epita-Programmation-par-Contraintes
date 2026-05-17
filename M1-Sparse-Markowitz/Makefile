PYTHON ?= python3
PIP ?= pip3
SEED ?= 42
TIME_LIMIT ?= 10
REF_TIME_LIMIT ?= 30
OUT ?= results

SP500_MAX_ASSETS ?= 150

.PHONY: help install install-dev test smoke bench pareto backtest sp500 figures slides clean

help:
	@echo "Cibles disponibles :"
	@echo "  install       installe les dependances de base"
	@echo "  install-dev   installe deps + pytest"
	@echo "  test          execute la suite pytest"
	@echo "  smoke         lance le demo rapide des 4 solveurs"
	@echo "  bench         genere reference_n50_k10.csv + bench.csv + scalability.png"
	@echo "  pareto        genere pareto.csv + pareto.png"
	@echo "  backtest      genere backtest.csv + backtest_cum.csv + backtest.png"
	@echo "  sp500         backtest S&P 500 Kaggle (sweep K) -> results/sp500_pnl*.csv/png"
	@echo "  figures       bench + pareto + backtest"
	@echo "  slides        compile slides/soutenance.md -> slides/soutenance.pdf (Marp si dispo)"
	@echo "  clean         supprime __pycache__ et results/"

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests

smoke:
	$(PYTHON) tests/smoke.py

bench:
	$(PYTHON) scripts/run_benchmark.py --seed $(SEED) --time-limit $(TIME_LIMIT) \
	    --ref-time-limit $(REF_TIME_LIMIT) --output $(OUT) --sizes 50 100 200

pareto:
	$(PYTHON) scripts/run_pareto.py --seed $(SEED) --time-limit $(TIME_LIMIT) --output $(OUT)

backtest:
	$(PYTHON) scripts/run_backtest.py --seed 7 --time-limit $(TIME_LIMIT) --output $(OUT)

sp500:
	$(PYTHON) scripts/run_sp500.py --k-min 10 --k-max 100 --k-step 10 \
	    --max-assets $(SP500_MAX_ASSETS) --time-limit $(TIME_LIMIT) --output $(OUT)

figures: bench pareto backtest

slides:
	@if command -v marp >/dev/null 2>&1 && marp slides/soutenance.md --pdf --allow-local-files --output slides/soutenance.pdf 2>/dev/null; then \
	    echo "slides/soutenance.pdf (Marp)"; \
	elif command -v npx >/dev/null 2>&1 && npx --yes @marp-team/marp-cli slides/soutenance.md --pdf --allow-local-files --output slides/soutenance.pdf 2>/dev/null; then \
	    echo "slides/soutenance.pdf (npx marp)"; \
	elif command -v pandoc >/dev/null 2>&1; then \
	    pandoc slides/soutenance.md -V geometry:margin=1.5cm -o slides/soutenance.pdf 2>/dev/null && echo "slides/soutenance.pdf (pandoc)" || echo "pandoc PDF a echoue (LaTeX manquant ?). Laisser le .md."; \
	else \
	    echo "marp et pandoc indisponibles : slides/soutenance.md laisse tel quel."; \
	fi

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf results/*.csv results/*.png
