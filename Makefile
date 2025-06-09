UV_PATH := $(shell which uv 2>/dev/null)

.PHONY: init
init:
	@if [ -z "$(UV_PATH)" ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi

.PHONY: install
install:
	@python -m pip install -U .

.PHONY: install-dev
install-dev:
	@python -m pip install -U -e .

.PHONY: lint
lint: init
	@uv run --group test ruff check lazy_hippo.py