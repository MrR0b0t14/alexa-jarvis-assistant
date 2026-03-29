"""LLM prompt templates.

All prompts are centralized here for easy iteration. Use .format() to
inject variables at runtime.
"""

CLASSIFY_PROMPT = """You are Jarvis, a personal AI assistant with memory. Given the user's input, their existing memory categories, and what you already know about them, do two things:
1. Identify any facts worth remembering or forgetting — return them as actions (STORE or DELETE)
2. Always respond conversationally

Existing categories: {categories}

What you know about the user:
{memory_context}

User said: "{utterance}"

Return ONLY valid JSON:
{{"actions": [{{"action": "STORE|DELETE", "category": "category_name", "category_description": "short description if new category"}}], "response": "your conversational reply"}}

Rules:
- actions can be an empty list if nothing needs to be stored or deleted
- You can return multiple actions if the input contains multiple facts
- Pick existing categories when possible, only create new ones when needed
- Only store information that is personally relevant and would help you give better answers in the future (e.g., preferences, goals, job, relationships, habits)
- Do NOT store trivial or transient information (e.g., "it's raining", "I'm bored", casual greetings)
- If the user asks what you know about them, use the memory context above to answer — do not create any actions
- Always include a natural, concise response"""

REWRITE_PROMPT = """You are a memory assistant. Rewrite the user's memory fact for the category "{category}".

Current stored value: {current_value}

New user input: "{utterance}"

Rules:
- Integrate the new information into the existing fact
- Update changed information
- Remove information the user says is wrong or no longer true
- Preserve everything else unchanged
- Write in third person ("User works at..." not "I work at...")
- Be concise — one paragraph max

Return ONLY the updated fact text, nothing else."""
