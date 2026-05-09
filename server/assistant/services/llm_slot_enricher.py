import json
import logging

from assistant.processors.local_model import LocalModelAdapter

logger = logging.getLogger(__name__)


class LLMSlotEnricher:
    @classmethod
    def enrich(cls, message: str, prior_slots: dict) -> dict:
        adapter = LocalModelAdapter.get_instance()

        if not adapter.is_available():
            logger.info("LLM slot enrichment skipped: adapter unavailable")
            return {}

        system_prompt = """
You are a strict JSON extraction engine for a marketplace recommendation system.
Extract only values explicitly present in the user message. Do not infer inventory,
availability, ranking, filtering, product facts, or hidden attributes.

Return one JSON object using only these top-level keys:
{
  "product_type": string|null,
  "attributes": {
    "dynamic_snake_case_key": {
      "value": string|number|boolean|array|object|null,
      "match_type": "text|numeric|categorical|boolean|range|unknown",
      "importance": "low|medium|high"
    }
  },
  "numeric_filters": {
    "dynamic_numeric_key": {
      "min": number|null,
      "max": number|null,
      "target": number|null,
      "unit": string|null,
      "currency": string|null
    }
  },
  "preferences": {
    "dynamic_preference_key": string|number|boolean|array|object|null
  },
  "intent": "buy|browse|compare|budget|premium|gift|replacement|unknown",
  "strictness": "low|medium|high"
}

Use null or omit a field when it is not directly supported by the text.
Respond with JSON only.
"""

        llm_output = adapter.generate(
            prompt=message,
            system_prompt=system_prompt,
            max_tokens=200,
            temperature=0.1,
        )

        response_text = llm_output.get('response', '') if isinstance(llm_output, dict) else str(llm_output)
        stripped = response_text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`").strip()
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()

        try:
            parsed = json.loads(stripped)
        except Exception:
            logger.warning("LLM raw extraction parse failed, using empty extraction")
            return {}

        if not isinstance(parsed, dict):
            logger.warning("LLM raw extraction parse failed, using empty extraction")
            return {}

        logger.info("LLM raw structured extraction returned %s top-level fields", len(parsed))
        return parsed


def enrich_slots(message: str, prior_slots: dict) -> dict:
    return LLMSlotEnricher.enrich(message, prior_slots)
