import json
import logging
from typing import Dict

from assistant.processors.local_model import LocalModelAdapter

logger = logging.getLogger(__name__)


class LLMSlotEnricher:
    @classmethod
    def enrich(cls, message: str, prior_slots: dict) -> dict:
        adapter = LocalModelAdapter.get_instance()

        if not adapter.is_available():
            logger.info("LLM slot enrichment skipped: adapter unavailable")
            return {}

        system_prompt = (
            "You are a slot extraction engine for a Nigerian marketplace\n"
            "called Zunto. Extract product search parameters..."
        )

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
            logger.warning("LLM slot enrichment parse failed, using SlotExtractor only")
            return {}

        if not isinstance(parsed, dict):
            logger.warning("LLM slot enrichment parse failed, using SlotExtractor only")
            return {}

        result: Dict = {k: v for k, v in parsed.items() if v is not None}

        for price_key in ('price_min', 'price_max'):
            if price_key in result and isinstance(result[price_key], str):
                try:
                    result[price_key] = float(result[price_key])
                except Exception:
                    result.pop(price_key, None)

        if 'condition' in result:
            condition = str(result.get('condition', '')).lower()
            if condition in {"new", "fair", "used", "like_new"}:
                result['condition'] = condition
            else:
                result.pop('condition', None)

        logger.info(f"LLM slot enrichment: {len(result)} slots extracted")
        return result


def enrich_slots(message: str, prior_slots: dict) -> dict:
    return LLMSlotEnricher.enrich(message, prior_slots)
