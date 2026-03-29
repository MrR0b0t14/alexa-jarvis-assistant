"""Manual integration test for the extraction pipeline.

Run: source .venv/bin/activate && python scripts/test_integration.py

Requires:
- GROQ_API_KEY in src/.env
- DynamoDB table 'user_memory' in eu-west-1
- AWS profile 'alexa-personal' configured
"""

import sys
import os
import boto3
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "src", ".env"))

from groq import Groq
from services.memory_service import MemoryService
from services.llm_service import LlmService
from services.extraction_service import ExtractionService

TEST_USER_ID = "test_user_integration"


def setup() -> ExtractionService:
    session = boto3.Session(profile_name="alexa-personal", region_name="eu-west-1")
    table = session.resource("dynamodb").Table("user_memory")
    memory_service = MemoryService(table)
    llm_service = LlmService(Groq(api_key=os.environ["GROQ_API_KEY"]))
    return ExtractionService(memory_service, llm_service)


def cleanup(service: ExtractionService) -> None:
    facts = service.memory_service.get_all_facts(TEST_USER_ID)
    for fact in facts:
        service.memory_service.delete_fact(TEST_USER_ID, fact.category)
    service.memory_service.delete_fact(TEST_USER_ID, "metadata#categories")
    print("\n🧹 Cleaned up test data.")


def main() -> None:
    service = setup()

    try:
        print("=" * 60)
        print("TEST 1: Store a fact")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "I work at Amazon as a software engineer")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("TEST 2: Store another fact (different category)")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "I want to run a marathon next year")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("TEST 3: Update existing fact")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "I got promoted to SDE2")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("TEST 4: Ask what it knows")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "What do you know about me?")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("TEST 5: Multiple facts in one utterance")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "I live in Dublin and I'm learning Italian")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("TEST 6: Delete a fact")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "Forget everything about my job")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("TEST 7: Verify deletion")
        print("=" * 60)
        response = service.process(TEST_USER_ID, "What do you know about me?")
        print(f"Response: {response}\n")

        print("=" * 60)
        print("FINAL STATE: All facts in DynamoDB")
        print("=" * 60)
        facts = service.memory_service.get_all_facts(TEST_USER_ID)
        for f in facts:
            print(f"  [{f.category}] {f.value}")
        if not facts:
            print("  (empty)")

    finally:
        cleanup(service)


if __name__ == "__main__":
    main()
