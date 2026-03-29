# Alexa Jarvis Assistant

[![CI](https://github.com/MrR0b0t14/alexa-jarvis-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/MrR0b0t14/alexa-jarvis-assistant/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MrR0b0t14/alexa-jarvis-assistant/branch/mainline/graph/badge.svg)](https://codecov.io/gh/MrR0b0t14/alexa-jarvis-assistant)

A personal AI memory system powered by Alexa, AWS Lambda, DynamoDB, and LLMs. Jarvis remembers facts about you, builds a knowledge base over time, and uses that context to have personalized conversations. Optionally integrates with Google Calendar to manage your schedule.

**Author:** Antonio Battipaglia ([@MrR0b0t14](https://github.com/MrR0b0t14))

## How It Works

```
User speaks → Alexa → Lambda → LLM classifies intent + responds
                                  ↓ (silently)
                              STORE/DELETE facts in DynamoDB
                              ADD/QUERY events in Google Calendar
```

1. You say something to Alexa (e.g., "Jarvis, remember that I work at Amazon")
2. The LLM analyzes your input and decides what to do:
   - **STORE**: Extract and save relevant facts to DynamoDB
   - **DELETE**: Remove facts you want forgotten
   - **CALENDAR_ADD**: Create a Google Calendar event
   - **CALENDAR_QUERY**: Retrieve upcoming events
   - **No action**: Just respond conversationally
3. The LLM always responds naturally, using your stored memory as context
4. Multiple actions can be extracted from a single utterance

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

You:    "Jarvis, add my trip to China on October 15th to the calendar"
Jarvis: "Done, I've added your China trip to your calendar for October 15th."

You:    "Jarvis, what's on my calendar this week?"
Jarvis: "Here's what's coming up: Team standup on 2026-03-30. Dentist on 2026-04-01."
```

## Architecture

- **Alexa Skill**: Custom skill with `LogActivityIntent` using `AMAZON.SearchQuery` for free-form input
- **AWS Lambda** (Python 3.14): Handles Alexa requests, orchestrates the pipeline
- **DynamoDB**: Stores memory facts and category registry per user
- **Groq API**: LLM inference (Llama 3.3 70B) for classification, fact rewriting, and conversation
- **Google Calendar API**: Event creation and retrieval via OAuth2 Account Linking
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
- [Google Cloud account](https://console.cloud.google.com) (optional, for calendar integration)

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
  Jarvis {freeText}
  hey {freeText}
  ```
- Point the skill endpoint to your Lambda function ARN

## Google Calendar Setup (Optional)

To enable calendar integration, you need to set up OAuth2 Account Linking between Alexa and Google.

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Go to **APIs & Services** → **Library** → search "Google Calendar API" → **Enable**
4. Go to **APIs & Services** → **OAuth consent screen**:
   - User type: **External**
   - App name: "Jarvis Assistant"
   - Add your email as a test user
5. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Authorized redirect URIs — add all three:
     ```
     https://layla.amazon.com/api/skill/link/<YOUR_VENDOR_ID>
     https://alexa.amazon.co.jp/api/skill/link/<YOUR_VENDOR_ID>
     https://pitangui.amazon.com/api/skill/link/<YOUR_VENDOR_ID>
     ```
   - You can find your Vendor ID in the Alexa Developer Console under Account Linking
6. Save the **Client ID** and **Client Secret**

### 2. Alexa Account Linking

In the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask):
1. Go to your skill → **Build** → **Account Linking**
2. Toggle account linking **On**
3. Fill in:
   - **Authorization URI**: `https://accounts.google.com/o/oauth2/v2/auth`
   - **Access Token URI**: `https://oauth2.googleapis.com/token`
   - **Client ID**: your Google OAuth client ID
   - **Client Secret**: your Google OAuth client secret
   - **Client Authentication Scheme**: HTTP Basic
   - **Scopes**:
     ```
     https://www.googleapis.com/auth/calendar
     https://www.googleapis.com/auth/calendar.events
     ```
4. Save and rebuild the skill

### 3. Link Your Account

Open the Alexa app on your phone → Skills → Your Skills → Jarvis Assistant → Settings → **Link Account**. You'll be redirected to Google to grant calendar access.

If the account is not linked, Jarvis will still work for memory features — calendar actions will be gracefully skipped with a message asking you to link your account.

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
    calendar.py             # CalendarEvent and CalendarEventResult (pydantic)
    llm.py                  # AgentAction, AgentTaskDecision, AgentResponse (pydantic)
  services/
    extraction_service.py   # Orchestrates classify → store/delete/calendar → respond
    memory_service.py       # DynamoDB read/write operations
    llm_service.py          # Groq LLM API integration
    calendar_service.py     # Google Calendar API integration
  utils/
    response.py             # Alexa response builder
tests/                      # Unit tests with mocked DynamoDB, LLM, and Calendar
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
- **Google OAuth token expiry**: Access tokens from Alexa Account Linking may expire. If calendar calls fail, the user may need to re-link their account.

## Roadmap

- [ ] **Session memory**: Multi-turn conversation context using Alexa session attributes
- [ ] **Faster responses**: Use a smaller model (Llama 3.1 8B) for classification, keep 70B for conversation
- [ ] **Auto-deploy**: GitHub Actions workflow to deploy on merge to mainline
- [ ] **Reprompt**: Keep the Alexa session alive between turns
- [ ] **Calendar event confirmation**: Ask user before creating events from auto-detected plans
