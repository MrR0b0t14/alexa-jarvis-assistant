import json
from groq import Groq

MODEL = "llama-3.3-70b-versatile"

class LlmService:
    def __init__(self, client):
        self.client = client
            
    def call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    def call_llm_json(self, prompt: str) -> dict:
        raw = self.call_llm(prompt)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
