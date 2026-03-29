.PHONY: check lint test

check: lint test

lint:
	mypy src/

test:
	pytest -v
