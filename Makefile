.PHONY: install
install:
	@python -m pip install -U .

.PHONY: install-dev
install-dev:
	@python -m pip install -U -e .
