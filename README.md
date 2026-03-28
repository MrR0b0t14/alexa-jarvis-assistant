# Alexa Jarvis Assistant

A personal AI memory system powered by Alexa, AWS Lambda, and LLMs. Jarvis remembers facts about you, updates them over time, and acts as a personal AI assistant.

## Prerequisites

- Python 3.10+
- AWS account (free tier)
- [Groq API key](https://console.groq.com) (free tier)

## Setup

```bash
git clone git@github.com:MrR0b0t14/alexa-jarvis-assistent.git
cd alexa-jarvis-assistent

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements/dev.txt
```

## Environment Variables

Create a `src/.env` file with your Groq API key:

```
GROQ_API_KEY="your_groq_api_key_here"
```

You can get a free key at https://console.groq.com

## Running Tests

```bash
source .venv/bin/activate
pytest -v
```

## Project Structure

```
src/
  handler.py              # Lambda entry point, Alexa request routing
  config/
    prompts.py            # LLM prompt templates
  intents/
    log_intent.py         # Intent handler for user input
  models/
    memory.py             # Data models (MemoryFact, CategoryRegistry)
  services/
    memory_service.py     # DynamoDB read/write operations
    llm_service.py        # Groq LLM API integration
  utils/
    response.py           # Alexa response builder
tests/
  test_models.py          # Unit tests for data models
  test_memory_service.py  # Unit tests for memory service (mocked DynamoDB)
requirements/
  prod.txt                # Runtime dependencies (bundled in Lambda zip)
  dev.txt                 # Dev dependencies (testing, local development)
```

## Deployment

```bash
pip install -r requirements/prod.txt -t src/package/
cd src
zip -r ../lambda.zip . -x "*.env*" "__pycache__/*"
aws lambda update-function-code --function-name <your-function-name> --zip-file fileb://../lambda.zip --region eu-west-1
```
