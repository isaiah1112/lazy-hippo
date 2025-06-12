UV_PATH := $(shell which uv 2>/dev/null)
UV_INSTALL := 1

.PHONY: help
help:
	@echo "Usage: make <target> [option]"
	@echo "\nTargets:"
	@echo "  install [UV_INSTALL]    Install project"
	@echo "  lint    Run 'ruff' linting on project"

# Install UV if it is not installed
.PHONY: uv-init
init:
	@if [ -z "$(UV_PATH)" ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi

.PHONY: install
install:
	@if [ $(UV_INSTALL) ]; then\
		$(MAKE) uv-init && uv sync && echo "Please run the following to activate the virtualenv:\n source .venv/bin/activate";\
	else\
		python -m pip install -U .;\
	if

.PHONY: lint
lint: uv-init
	@uv run --group test ruff check lazy_hippo.py