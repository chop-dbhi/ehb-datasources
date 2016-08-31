.PHONY: all test

all: test

test:
	pytest -v --cov-report=html --cov=ehb_datasources ehb_datasources/tests/unit_tests
