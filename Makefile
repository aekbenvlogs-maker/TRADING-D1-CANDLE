format:
	black trading_d1_bougie/

lint:
	ruff check trading_d1_bougie/
	pylint trading_d1_bougie/

typecheck:
	mypy trading_d1_bougie/

test: build
	pytest trading_d1_bougie/tests/ --cov=trading_d1_bougie.core --cov-fail-under=80 -v

qa:
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

build:
	python setup.py build_ext --inplace

all:
	$(MAKE) qa
	$(MAKE) build
