.PHONY: dev-install install

install:
	@python -m pip install -U .

dev-install:
	@python -m pip install -U -e .
