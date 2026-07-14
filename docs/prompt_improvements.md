# Phase 2: Intent Extraction Prompt Improvements

## What Changed
The `INTENT_EXTRACTION_PROMPT` in `ai/prompts.py` was heavily expanded and restructured from a simple list of intents into a comprehensive, rule-based classification engine. Key modifications include:
- **Language Directives:** Explicit instructions added to interpret English, Urdu, Roman Urdu, and mixed-language naturally without being tripped up by slang or typos.
- **Negative Rules (Safety Boundaries):** Explicit instructions forbidding the model from classifying numeric-only strings (e.g. `12345`) as `order_tracking`. These are now strictly mapped to `unknown`.
- **40+ Few-Shot Examples:** The prompt now contains an extensive library of examples across all 7 intents. These cover high-ambiguity cases, aggressive complaints, formatting errors, and implicit/explicit entity extraction.
- **Output Constraints:** Rigidly defined the JSON structure, actively telling the model to drop markdown wrappers.

## Why it Improves Accuracy
By using **Few-Shot Prompting**, we teach the LLM exactly how to behave in edge cases rather than relying on its base reasoning. 
- **Urdu/Roman Urdu Robustness:** Informing the model that it is acting as a "multilingual bot for Naheed" primes its weights for South Asian e-commerce slang (e.g. "abhi tak order nahi aya"), vastly reducing confusion.
- **Preventing False Positives:** The negative examples directly address the biggest flaw in naive LLMs: guessing. By defining numeric-only messages as `unknown`, we prevent the bot from immediately firing a database query when a user randomly types a number without context.

## New Few-Shot Examples (Categories Covered)
- **Greetings/Goodbyes:** `hello 12345`, `Salam`, `Khuda hafiz`
- **Order Tracking:** English (`Where is my order?`), Urdu/Typos (`mera ordr kha hy`, `Delivery kab hogi?`), Multi-entities (`Where are my orders 111 and 222?`)
- **Complaints:** Emotional/Aggressive (`Are you guys scammers???`, `Baqwas service hai`)
- **Refunds:** Clear vs Typos (`Mujhe paisay wapas chahiye`, `refnd`)
- **General Queries:** `What are your timings?`, `help`
- **Negative Examples:** `12345`, `987654`

## Expected Impact on Production
- **Higher Precision:** False positives on `order_tracking` will drop to near 0%.
- **Higher Recall on Complaints:** Angry customers using colloquial slang won't be misclassified as "unknown" anymore, improving customer satisfaction routing.
- **JSON Stability:** The explicit JSON formatting blocks hallucinated conversational prefixes (e.g. "Sure, here is the JSON...").

## Remaining Limitations
- **Context Windows:** If a user sends a massive paragraph detailing a 5-part complaint with 3 different order IDs, the model might still struggle to extract a single `order_id` entity because the schema currently only maps a single string.
- **Stateless Classification:** The Intent Parser is currently stateless. If the bot asks "Please provide your order ID", and the user replies "12345", the parser will classify it as `unknown` because it has no memory of the bot's previous question. This will need to be resolved in Phase 3 by passing conversation history to the model!
