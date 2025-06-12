UV_PATH := $(shell which uv 2>/dev/null)

# Install UV if it is not installed
.PHONY: uv-init
init:
	@if [ -z "$(UV_PATH)" ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi

.PHONY: install
install:
	@python -m pip install -U .

.PHONY: install-dev
install-dev:
	@python -m pip install -U -e .

.PHONY: lint
lint: uv-init
	@uv run --group test ruff check lazy_hippo.py