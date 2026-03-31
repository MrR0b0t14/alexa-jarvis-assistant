.PHONY: check lint test format deploy

check: lint test

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/

format:
	ruff format src/ tests/

test:
	pytest -v

deploy:
	rm -rf /tmp/lambda_package
	mkdir -p /tmp/lambda_package
	pip install -r requirements/prod.txt -t /tmp/lambda_package --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.14 -q
	cp -r src/* /tmp/lambda_package/
	rm -f /tmp/lambda_package/.env
	cd /tmp/lambda_package && zip -r /tmp/lambda.zip . -x "__pycache__/*" "*.pyc" ".env" -q
	aws lambda update-function-code --function-name alexa-jarvis-assistant --zip-file fileb:///tmp/lambda.zip --region eu-west-1 --profile alexa-personal --query '{LastModified: LastModified}' --output json
