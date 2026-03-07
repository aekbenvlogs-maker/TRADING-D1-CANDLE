format:
	black trading_d1_bougie/

lint:
	ruff check trading_d1_bougie/
	pylint trading_d1_bougie/

typecheck:
	mypy trading_d1_bougie/

test:
	pytest --cov --cov-fail-under=80

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
