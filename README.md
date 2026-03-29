# Alexa Jarvis Assistant

[![CI](https://github.com/MrR0b0t14/alexa-jarvis-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/MrR0b0t14/alexa-jarvis-assistant/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MrR0b0t14/alexa-jarvis-assistant/branch/mainline/graph/badge.svg)](https://codecov.io/gh/MrR0b0t14/alexa-jarvis-assistant)

A personal AI memory system powered by Alexa, AWS Lambda, DynamoDB, and LLMs. Jarvis remembers facts about you, builds a knowledge base over time, and uses that context to have personalized conversations.

**Author:** Antonio Battipaglia ([@MrR0b0t14](https://github.com/MrR0b0t14))

## How It Works

```
User speaks → Alexa → Lambda → LLM classifies intent + responds
                                  ↓ (silently)
                              STORE/DELETE facts in DynamoDB
```

1. You say something to Alexa (e.g., "remember that I work at Amazon")
2. The LLM analyzes your input and decides what to do:
   - **STORE**: Extract and save relevant facts to DynamoDB
   - **DELETE**: Remove facts you want forgotten
   - **No action**: Just respond conversationally
3. The LLM always responds naturally, using your stored memory as context
4. Multiple facts can be extracted from a single utterance

The LLM is selective — it only stores personally relevant information (preferences, goals, job, relationships) and ignores trivial or transient input.

## Example Interactions

```
You:    "Jarvis, remember that I work at Amazon as a software engineer"
Jarvis: "That's great, you work as a software engineer at Amazon. I'll keep that in mind."

You:    "Jarvis, I want to run a marathon next year"
Jarvis: "That's a great goal! I've taken note of your aspiration."

You:    "Jarvis, what do you know about me?"
Jarvis: "You work as a software engineer at Amazon and your fitness goal is to run a marathon next year."

You:    "Jarvis, I got promoted to SDE2"
Jarvis: "Congratulations on your promotion! I've updated my records."

You:    "Jarvis, forget everything about my job"
Jarvis: "Done, I've removed your job information."
```

## Architecture

- **Alexa Skill**: Custom skill with `LogActivityIntent` using `AMAZON.SearchQuery` for free-form input
- **AWS Lambda** (Python 3.14): Handles Alexa requests, orchestrates the pipeline
- **DynamoDB**: Stores memory facts and category registry per user
- **Groq API**: LLM inference (Llama 3.3 70B) for classification, fact rewriting, and conversation
- **GitHub Actions**: CI with mypy, pytest, and Codecov

### Data Model (DynamoDB)

Single table `user_memory` with composite key:

| PK (`user_id`) | SK (`category`) | `value` | `source_utterance` | `updated_at` |
|---|---|---|---|---|
| amzn1.ask... | employment | Works at Amazon as SDE2 | I got promoted | 2026-03-29T... |
| amzn1.ask... | goal | Wants to run a marathon | I want to run... | 2026-03-29T... |
| amzn1.ask... | metadata#categories | {"employment": "Jobs", "goal": "Goals"} | | 2026-03-29T... |

Each category holds a single consolidated fact that the LLM rewrites on every update — not append-only. The LLM can add, modify, or remove information within a fact.

## Prerequisites

- Python 3.14+
- AWS account (free tier works)
- [Groq API key](https://console.groq.com) (free tier)
- [Alexa Developer account](https://developer.amazon.com/alexa/console/ask)

## AWS Infrastructure Setup

You need the following resources in your AWS account:

### 1. DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name user_memory \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=category,KeyType=RANGE \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=category,AttributeType=S \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

### 2. Lambda Function

Create a Lambda function named `alexa-jarvis-assistant` with:
- Runtime: Python 3.14
- Timeout: 30 seconds (Groq API calls need time)
- Memory: 128 MB
- Handler: `handler.lambda_handler`

### 3. Lambda Environment Variables

```bash
aws lambda update-function-configuration \
  --function-name alexa-jarvis-assistant \
  --environment 'Variables={GROQ_API_KEY=your_groq_api_key_here}' \
  --region eu-west-1
```

### 4. IAM Permissions

The Lambda execution role needs DynamoDB access:

```bash
aws iam attach-role-policy \
  --role-name <your-lambda-role-name> \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

### 5. Alexa Skill Configuration

In the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask):
- Create a custom skill with your preferred invocation name
- Add a `LogActivityIntent` with slot `freeText` of type `AMAZON.SearchQuery`
- Add sample utterances with carrier phrases (required by `AMAZON.SearchQuery`):
  ```
  record that {freeText}
  remember that {freeText}
  tell me {freeText}
  I think {freeText}
  I want {freeText}
  hey {freeText}
  ```
- Point the skill endpoint to your Lambda function ARN

## Local Development

```bash
git clone git@github.com:MrR0b0t14/alexa-jarvis-assistant.git
cd alexa-jarvis-assistant

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
```

### Environment Variables

Create `src/.env` with your Groq API key:

```
GROQ_API_KEY="your_groq_api_key_here"
```

### Running Checks

```bash
make check    # runs mypy + pytest with coverage
make lint     # mypy only
make test     # pytest only
```

### Integration Testing

```bash
python scripts/test_integration.py
```

Runs the full pipeline against real Groq and DynamoDB (requires AWS credentials and Groq API key).

## Deployment

```bash
# Build the zip with Lambda-compatible dependencies
pip install -r requirements/prod.txt -t /tmp/lambda_package \
  --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.14
cp -r src/* /tmp/lambda_package/
cd /tmp/lambda_package
zip -r /tmp/lambda.zip . -x "__pycache__/*" "*.pyc" ".env"

# Deploy
aws lambda update-function-code \
  --function-name alexa-jarvis-assistant \
  --zip-file fileb:///tmp/lambda.zip \
  --region eu-west-1
```

Note: Dependencies must be built with `--platform manylinux2014_x86_64` and `--python-version 3.14` to match the Lambda runtime. Local builds will fail with `pydantic_core` import errors.

## Project Structure

```
src/
  handler.py                # Lambda entry point, Alexa request routing
  config/
    prompts.py              # LLM prompt templates
    logger.py               # Centralized logging configuration
  models/
    memory.py               # MemoryFact and CategoryRegistry dataclasses
    llm.py                  # AgentAction, AgentTaskDecision, AgentResponse (pydantic)
  services/
    extraction_service.py   # Orchestrates classify → store/delete → respond pipeline
    memory_service.py       # DynamoDB read/write operations
    llm_service.py          # Groq LLM API integration
  utils/
    response.py             # Alexa response builder
tests/                      # Unit tests with mocked DynamoDB and LLM
scripts/
  test_integration.py       # Manual E2E integration test
requirements/
  prod.txt                  # Runtime dependencies (Lambda zip)
  dev.txt                   # Dev dependencies (testing, linting)
```

## Known Limitations

- **Groq latency**: LLM calls take 1-3 seconds. Combined with DynamoDB reads and the rewrite step, total response time is 3-7 seconds. Alexa has an 8-second timeout for skill responses.
- **Carrier phrases required**: `AMAZON.SearchQuery` requires at least one carrier word in utterances (e.g., "tell me", "I think"). Bare free-form input is not supported by Alexa.
- **No conversation history**: Each utterance is stateless within a session. The LLM doesn't know what you said 30 seconds ago — only what's in long-term memory.
- **Single LLM model**: Currently uses Llama 3.3 70B for everything. A smaller model for classification could improve speed.

## Roadmap

- [ ] **Session memory**: Multi-turn conversation context using Alexa session attributes
- [ ] **Google Calendar integration**: Automatically create calendar events from stored goals and plans
- [ ] **Faster responses**: Use a smaller model (Llama 3.1 8B) for classification, keep 70B for conversation
- [ ] **Auto-deploy**: GitHub Actions workflow to deploy on merge to mainline
- [ ] **Reprompt**: Keep the Alexa session alive between turns
