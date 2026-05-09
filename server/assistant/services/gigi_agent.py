"""Groq-backed Gigi recommendation agent with deterministic catalog guards."""

from __future__ import annotations

import json
import logging
import math
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.conf import settings
from django.db.models import Q

from assistant.models import ConversationSession
from assistant.processors.local_model import LocalModelAdapter, RateLimitError
from assistant.services.demand_gap_service import log_demand_gap
from market.search.hybrid_ranker import product_search_text, rank_products_hybrid

logger = logging.getLogger(__name__)

NAIRA = "\u20A6"


class GigiRecommendationAgent:
    """Tool-calling shopping assistant for homepage recommendation conversations."""

    MODEL_NAME = "llama-3.3-70b-versatile"
    MAX_HISTORY_MESSAGES = 12
    MAX_RESULTS = 5

    SHORT_AFFIRMATIONS = {
        "yes", "yeah", "yep", "y", "ok", "okay", "sure", "alright",
        "fine", "cool", "go ahead", "please do", "sounds good",
    }
    GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
    SUPPORT_KEYWORDS = {
        "order", "delivery", "delivered", "arrived", "tracking", "track",
        "refund", "return", "cancel", "payment", "paid", "checkout",
        "account", "login", "password", "verification", "seller", "support",
        "complaint", "dispute", "damaged", "wrong item", "not delivered",
        "hasn't arrived", "has not arrived", "haven't arrived", "have not arrived",
    }
    SHOPPING_SIGNALS = {
        "buy", "need", "want", "looking for", "find", "show me", "recommend",
        "available", "price", "cost", "budget", "cheap", "affordable",
        "under", "below", "less than", "how much", "get me",
    }
    QUERY_STOPWORDS = {
        "a", "an", "and", "any", "around", "at", "below", "budget", "buy",
        "can", "cheap", "cost", "do", "find", "for", "from", "get", "give",
        "have", "how", "i", "im", "in", "is", "less", "like", "looking",
        "max", "me", "my", "naira", "need", "ngn", "of", "ok", "on",
        "one", "please", "price", "recommend", "show", "than", "the", "to",
        "under", "want", "what", "with", "within", "you",
    }

    PRODUCT_ALIASES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
        ("air conditioner", ("air conditioner", "air conditioners", "air conditioning", "split ac", "split unit", "a/c", "ac")),
        ("rice", ("bag of rice", "bags of rice", "basmati rice", "parboiled rice", "rice")),
        ("phone", ("mobile phone", "mobile phones", "smart phone", "smart phones", "smartphone", "smartphones", "android phone", "iphone", "phones", "phone")),
        ("laptop", ("laptop computer", "notebook computer", "laptops", "laptop")),
        ("shoe", ("sneakers", "trainer", "trainers", "shoes", "shoe")),
        ("shirt", ("t-shirt", "t-shirts", "tee shirt", "tee shirts", "shirts", "shirt")),
        ("dress", ("dresses", "dress")),
        ("generator", ("generators", "generator")),
        ("television", ("smart tv", "televisions", "television", "tvs", "tv")),
        ("refrigerator", ("refrigerators", "refrigerator", "fridges", "fridge")),
        ("fan", ("standing fan", "ceiling fan", "fans", "fan")),
        ("bag", ("handbag", "handbags", "school bag", "school bags", "bags", "bag")),
        ("watch", ("smart watch", "smartwatch", "wristwatch", "watches", "watch")),
        ("camera", ("cameras", "camera")),
        ("speaker", ("bluetooth speaker", "speakers", "speaker")),
        ("perfume", ("fragrances", "fragrance", "perfumes", "perfume")),
    )

    PHONE_FAMILY_INCLUDES = (
        "android phones",
        "iphones",
        "feature phones",
        "refurbished phones",
    )
    PHONE_FAMILY_EXCLUDES = (
        "accessor",
        "case",
        "screen protector",
        "power bank",
        "charger",
        "cable",
        "repair",
        "watch",
        "tablet",
        "earbud",
        "headset",
    )

    SYSTEM_PROMPT = (
        "You are Gigi, a smart and friendly AI shopping assistant for Zunto, "
        "a Nigerian marketplace.\n"
        "Help users find products through natural conversation.\n"
        "Use search_products when the user wants to buy, browse, compare, or narrow a product.\n"
        "Do not use search_products for customer service, order, account, payment, delivery, "
        "refund, or general knowledge questions.\n"
        "When a user gives a budget, it is always the maximum price in Nigerian Naira. "
        "Show strong options within that ceiling, not merely the cheapest.\n"
        "When the user says yes, ok, sure, or another short affirmation, continue the "
        "previous shopping context naturally. Never search for a product named yes or ok.\n"
        "If the user switches product topics, reset to the new product immediately.\n"
        "Never invent products. Only discuss products returned by the tool. Keep replies concise."
    )

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Search Zunto marketplace active inventory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Product type, for example phone, rice, laptop, AC.",
                        },
                        "max_price": {
                            "type": "number",
                            "description": "Maximum price in Nigerian Naira. Hard ceiling.",
                        },
                        "min_price": {
                            "type": "number",
                            "description": "Minimum price in Nigerian Naira if explicitly requested.",
                        },
                        "location": {
                            "type": "string",
                            "description": "Nigerian city, state, or area.",
                        },
                        "brand": {
                            "type": "string",
                            "description": "Brand name if specified.",
                        },
                        "condition": {
                            "type": "string",
                            "enum": ["new", "used", "any"],
                            "default": "any",
                        },
                    },
                    "required": ["category"],
                },
            },
        }
    ]

    def __init__(self, model_name: Optional[str] = None):
        configured_model = getattr(settings, "GROQ_MODEL", "") or self.MODEL_NAME
        self.model_name = model_name or configured_model
        self.adapter = LocalModelAdapter.get_instance()

    @staticmethod
    def initialize_context(session: ConversationSession) -> None:
        updates = []
        if session.context_type != ConversationSession.CONTEXT_TYPE_RECOMMENDATION:
            session.context_type = ConversationSession.CONTEXT_TYPE_RECOMMENDATION
            updates.append("context_type")
        if not isinstance(session.constraint_state, dict):
            session.constraint_state = {}
            updates.append("constraint_state")
        if not isinstance(session.intent_state, dict):
            session.intent_state = {}
            updates.append("intent_state")
        if updates:
            updates.append("updated_at")
            session.save(update_fields=updates)

    def run(
        self,
        *,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        user_message: str,
        session: Optional[ConversationSession] = None,
    ) -> Dict[str, Any]:
        """Return a frontend-compatible recommendation response."""

        if session is not None:
            self.initialize_context(session)

        message = self._clean_text(user_message)
        history = self._normalize_history(conversation_history or [], current_message=message)
        prior_slots = self._session_slots(session)
        prior_products = self._load_products_by_ids(prior_slots.get("_shown_product_ids") or [])

        if not message:
            return self._final_response(
                reply="What product would you like me to help you find?",
                session=session,
                products=[],
                intent="clarification",
                confidence=0.75,
                source="gigi_agent_empty_message",
                slots=prior_slots,
            )

        intent = self._classify_message(message, prior_slots)

        if intent == "support":
            reply = self._support_reply(message)
            self._update_session(
                session=session,
                slots=prior_slots,
                products=[],
                intent="customer_service",
                turn_type="support",
                turn_outcome=None,
            )
            return self._final_response(
                reply=reply,
                session=session,
                products=[],
                intent="customer_service",
                confidence=0.9,
                source="gigi_agent_support",
                slots=prior_slots,
                turn_type="support",
            )

        if intent == "off_topic":
            reply = self._off_topic_reply(message)
            return self._final_response(
                reply=reply,
                session=session,
                products=[],
                intent="off_topic",
                confidence=0.82,
                source="gigi_agent_off_topic",
                slots=prior_slots,
                turn_type="off_topic",
            )

        if intent == "affirmation":
            return self._handle_affirmation(
                session=session,
                prior_slots=prior_slots,
                prior_products=prior_products,
            )

        deterministic_args = self._deterministic_search_args(message, prior_slots)
        groq_args, groq_reply, groq_error = self._extract_with_groq(history, message)
        args = self._merge_search_args(
            prior_slots=prior_slots,
            deterministic_args=deterministic_args,
            groq_args=groq_args,
            message=message,
        )

        if not args.get("category"):
            reply = (
                "I can help with that. What product are you looking for?"
                if intent == "shopping"
                else (groq_reply or "Tell me what you want to buy and I will find good options.")
            )
            slots = self._slots_from_args(args, message=message)
            self._update_session(
                session=session,
                slots=slots,
                products=[],
                intent="product_search",
                turn_type="clarification",
                turn_outcome=None,
            )
            return self._final_response(
                reply=reply,
                session=session,
                products=[],
                intent="product_search",
                confidence=0.78,
                source="gigi_agent_missing_category",
                slots=slots,
                turn_type="clarification",
                groq_error=groq_error,
            )

        if self._needs_phone_budget_followup(args, message):
            slots = self._slots_from_args(args, message=message)
            slots["_last_clarification_key"] = "price_max"
            self._update_session(
                session=session,
                slots=slots,
                products=[],
                intent="product_search",
                turn_type="clarification",
                turn_outcome=None,
            )
            return self._final_response(
                reply="Sure - what's your budget for the phone?",
                session=session,
                products=[],
                intent="product_search",
                confidence=0.9,
                source="gigi_agent_phone_budget_followup",
                slots=slots,
                turn_type="clarification",
                groq_error=groq_error,
            )

        products = self.search_products(args)
        slots = self._slots_from_args(args, message=message)

        if not products:
            self._log_demand_gap(session, slots)
            reply = self._format_no_results_reply(args)
            self._update_session(
                session=session,
                slots=slots,
                products=[],
                intent="product_search",
                turn_type="search",
                turn_outcome="no_results",
            )
            return self._final_response(
                reply=reply,
                session=session,
                products=[],
                intent="product_search",
                confidence=0.78,
                source="gigi_agent_no_results",
                slots=slots,
                turn_type="search",
                turn_outcome="no_results",
                groq_error=groq_error,
            )

        final_reply = self._finalize_with_groq(history, message, args, products)
        if not final_reply:
            final_reply = self._format_results_reply(args, products)

        self._update_session(
            session=session,
            slots=slots,
            products=products,
            intent="product_search",
            turn_type="search",
            turn_outcome="results",
        )
        return self._final_response(
            reply=final_reply,
            session=session,
            products=products,
            intent="product_search",
            confidence=0.92,
            source="gigi_agent_results",
            slots=slots,
            turn_type="search",
            turn_outcome="results",
            groq_error=groq_error,
        )

    def search_products(self, args: Dict[str, Any]) -> List[Any]:
        """Execute a guarded Product ORM search with hard filters."""

        from market.models import Product

        category = self._canonical_category(args.get("category") or "")
        max_price = self._safe_decimal(args.get("max_price"))
        min_price = self._safe_decimal(args.get("min_price"))
        location = self._clean_text(args.get("location"))
        brand = self._clean_text(args.get("brand"))
        condition = self._normalize_condition(args.get("condition"))

        queryset = Product.objects.filter(status="active", quantity__gt=0).select_related(
            "category",
            "product_family",
            "location",
            "seller",
        )

        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        if location:
            queryset = queryset.filter(
                Q(location__area__icontains=location)
                | Q(location__city__icontains=location)
                | Q(location__state__icontains=location)
            )

        if brand:
            queryset = queryset.filter(Q(brand__icontains=brand) | Q(title__icontains=brand))

        if condition and condition != "any":
            if condition == "used":
                queryset = queryset.filter(condition__in=["like_new", "good", "fair", "poor", "used"])
            else:
                queryset = queryset.filter(condition__iexact=condition)

        if category:
            queryset = queryset.filter(self._product_broad_q(category)).distinct()

        candidates = list(queryset.order_by("-is_verified_product", "-views_count", "-favorites_count", "-created_at")[:250])
        if category:
            candidates = [product for product in candidates if self._product_matches_category(product, category)]

        slots = self._slots_from_args(args, message=args.get("raw_query") or "")
        ranked = rank_products_hybrid(candidates, slots=slots, semantic_scores={})
        ranked = self._apply_demo_quality_sort(ranked, args)
        ranked = self._dedupe_products(ranked)
        return ranked[: self.MAX_RESULTS]

    def _extract_with_groq(
        self,
        history: List[Dict[str, str]],
        message: str,
    ) -> Tuple[Optional[Dict[str, Any]], str, str]:
        if not self.adapter.is_available():
            return None, "", "groq_unavailable"

        messages = self._groq_messages(history, message)
        try:
            response = self._call_groq(
                messages=messages,
                tools=self.TOOLS,
                max_tokens=350,
                temperature=0.1,
            )
            choice = response.choices[0] if getattr(response, "choices", None) else None
            if not choice:
                return None, "", "groq_empty_choices"

            response_message = getattr(choice, "message", None)
            tool_calls = getattr(response_message, "tool_calls", None) or []
            if tool_calls:
                arguments = getattr(tool_calls[0].function, "arguments", "{}")
                parsed = json.loads(arguments or "{}")
                return parsed if isinstance(parsed, dict) else None, "", ""

            content = getattr(response_message, "content", "") or ""
            return None, content.strip(), ""
        except RateLimitError as exc:
            self.adapter.rate_limited_until = time.time() + self.adapter.cooldown_seconds
            logger.warning("Groq tool extraction rate-limited: %s", exc)
            return None, "", "groq_rate_limited"
        except Exception as exc:
            logger.warning("Groq tool extraction failed: %s", exc)
            return None, "", "groq_tool_error"

    def _finalize_with_groq(
        self,
        history: List[Dict[str, str]],
        message: str,
        args: Dict[str, Any],
        products: List[Any],
    ) -> str:
        if not self.adapter.is_available():
            return ""

        serialized = self._serialize_products(products)
        messages = self._groq_messages(history, message)
        messages.append(
            {
                "role": "user",
                "content": (
                    "search_products returned this JSON:\n"
                    f"{json.dumps({'arguments': args, 'products': serialized}, ensure_ascii=True)}\n\n"
                    "Write Gigi's final reply from these products only. "
                    "Mention at most three products, include Naira prices, condition, and location. "
                    "Do not add products that are not in the tool result."
                ),
            }
        )

        try:
            response = self._call_groq(messages=messages, max_tokens=420, temperature=0.2)
            choice = response.choices[0] if getattr(response, "choices", None) else None
            content = getattr(getattr(choice, "message", None), "content", "") if choice else ""
            content = self._clean_text(content)
            if not content:
                return ""
            if self._reply_mentions_unknown_product(content, products):
                logger.warning("Groq final reply mentioned unknown products; using deterministic reply")
                return ""
            return content
        except Exception as exc:
            logger.warning("Groq finalization failed: %s", exc)
            return ""

    def _call_groq(self, *, messages, max_tokens: int, temperature: float, tools=None):
        acquired = self.adapter._bulkhead.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("Groq concurrency limit reached")

        try:
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            future = self.adapter._executor.submit(self.adapter.client.chat.completions.create, **kwargs)
            response = future.result(timeout=self.adapter.timeout_seconds)
            self.adapter.request_count += 1
            return response
        finally:
            self.adapter._bulkhead.release()

    def _groq_messages(self, history: List[Dict[str, str]], message: str) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(history[-self.MAX_HISTORY_MESSAGES :])
        if not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != message:
            messages.append({"role": "user", "content": message})
        return messages

    def _classify_message(self, message: str, prior_slots: Dict[str, Any]) -> str:
        raw = message.lower().strip()
        if raw in self.SHORT_AFFIRMATIONS:
            return "affirmation"
        if self._looks_like_support(raw):
            return "support"
        if self._looks_like_off_topic(raw):
            return "off_topic"
        if self._looks_like_shopping(raw, prior_slots):
            return "shopping"
        if raw in self.GREETINGS:
            return "shopping"
        return "off_topic"

    def _looks_like_support(self, raw: str) -> bool:
        return any(keyword in raw for keyword in self.SUPPORT_KEYWORDS)

    def _looks_like_off_topic(self, raw: str) -> bool:
        if "capital of nigeria" in raw:
            return True
        if raw.endswith("?") and not any(signal in raw for signal in self.SHOPPING_SIGNALS):
            product = self._canonical_product_from_text(raw)
            return not bool(product)
        return False

    def _looks_like_shopping(self, raw: str, prior_slots: Dict[str, Any]) -> bool:
        if self._canonical_product_from_text(raw):
            return True
        if prior_slots.get("product_type") and self._extract_price(raw)[0] is not None:
            return True
        return any(signal in raw for signal in self.SHOPPING_SIGNALS)

    def _handle_affirmation(
        self,
        *,
        session: Optional[ConversationSession],
        prior_slots: Dict[str, Any],
        prior_products: List[Any],
    ) -> Dict[str, Any]:
        if prior_products:
            first = prior_products[0]
            title = getattr(first, "title", "the first option")
            price = self._format_price(getattr(first, "price", None))
            reply = (
                f"Great. I would start with {title} at {price}; it is the strongest match "
                "from the options I just showed. Tell me a brand, location, or condition if you want me to narrow it further."
            )
            self._update_session(
                session=session,
                slots=prior_slots,
                products=prior_products,
                intent="product_search",
                turn_type="affirmation",
                turn_outcome="continued",
            )
            return self._final_response(
                reply=reply,
                session=session,
                products=prior_products,
                intent="product_search",
                confidence=0.86,
                source="gigi_agent_affirmation",
                slots=prior_slots,
                turn_type="affirmation",
                turn_outcome="continued",
            )

        reply = "Sure. What product should I help you find?"
        return self._final_response(
            reply=reply,
            session=session,
            products=[],
            intent="product_search",
            confidence=0.72,
            source="gigi_agent_affirmation_no_context",
            slots=prior_slots,
            turn_type="clarification",
        )

    def _support_reply(self, message: str) -> str:
        raw = message.lower()
        if "order" in raw and ("arrived" in raw or "delivery" in raw or "delivered" in raw):
            return (
                "I am sorry your order has not arrived. Check the order status in My Orders first; "
                "if the delivery date has passed, contact the seller from the order page and send Customer Service your order number so they can trace it or help start a refund."
            )
        if "refund" in raw or "return" in raw:
            return (
                "For a refund or return, open the order in My Orders, message the seller with the issue, "
                "and contact Customer Service with the order number if you need Zunto to step in."
            )
        return (
            "I can help with that. Open the related order or account page and contact Customer Service with the key details, "
            "then I can help you phrase the message clearly."
        )

    def _off_topic_reply(self, message: str) -> str:
        if "capital of nigeria" in message.lower():
            return "Abuja is the capital of Nigeria. I can also help you find products on Zunto."
        return "I am Gigi, so I am best at shopping help. Tell me what product you want and any budget or location that matters."

    def _deterministic_search_args(self, message: str, prior_slots: Dict[str, Any]) -> Dict[str, Any]:
        raw = message.lower().strip()
        category = self._canonical_product_from_text(raw)
        price, min_price = self._extract_price(raw)
        condition = self._extract_condition(raw)
        location = self._extract_location(raw)
        brand = self._extract_brand(raw)
        price_intent = self._extract_price_intent(raw)

        if not category and prior_slots.get("product_type"):
            if price is not None or condition or location or brand or raw in self.SHORT_AFFIRMATIONS:
                category = str(prior_slots.get("product_type") or "")

        args: Dict[str, Any] = {}
        if category:
            args["category"] = category
        if price is not None:
            args["max_price"] = price
        if min_price is not None:
            args["min_price"] = min_price
        if location:
            args["location"] = location
        if brand:
            args["brand"] = brand
        if condition:
            args["condition"] = condition
        if price_intent:
            args["price_intent"] = price_intent
        args["raw_query"] = message
        return args

    def _merge_search_args(
        self,
        *,
        prior_slots: Dict[str, Any],
        deterministic_args: Dict[str, Any],
        groq_args: Optional[Dict[str, Any]],
        message: str,
    ) -> Dict[str, Any]:
        groq_args = self._sanitize_tool_args(groq_args or {})
        deterministic_args = self._sanitize_tool_args(deterministic_args)

        prior_category = self._canonical_category(prior_slots.get("product_type") or prior_slots.get("category") or "")
        incoming_category = deterministic_args.get("category") or groq_args.get("category")
        incoming_category = self._canonical_category(incoming_category or "")
        topic_switched = bool(prior_category and incoming_category and prior_category != incoming_category)

        args: Dict[str, Any] = {}
        if prior_slots and not topic_switched:
            args = {
                "category": prior_category,
                "max_price": prior_slots.get("price_max"),
                "min_price": prior_slots.get("price_min"),
                "location": prior_slots.get("location"),
                "brand": prior_slots.get("brand"),
                "price_intent": prior_slots.get("price_intent"),
                "condition": prior_slots.get("condition") or "any",
            }

        for source in (groq_args, deterministic_args):
            for key, value in source.items():
                if key == "raw_query":
                    continue
                if value in (None, "", {}, []):
                    continue
                args[key] = value

        if incoming_category:
            args["category"] = incoming_category

        if not args.get("category") and prior_category and self._extract_price(message)[0] is not None:
            args["category"] = prior_category

        args["condition"] = self._normalize_condition(args.get("condition")) or "any"
        args["raw_query"] = message
        return self._sanitize_tool_args(args)

    def _sanitize_tool_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        category = self._canonical_category(args.get("category") or args.get("product_type") or "")
        if category:
            sanitized["category"] = category

        for key in ("max_price", "min_price"):
            value = self._safe_decimal(args.get(key))
            if value is not None:
                sanitized[key] = float(value)

        for key in ("location", "brand", "raw_query"):
            value = self._clean_text(args.get(key))
            if value:
                sanitized[key] = value

        price_intent = self._normalize_space(args.get("price_intent"))
        if price_intent in {"cheap", "premium"}:
            sanitized["price_intent"] = price_intent

        condition = self._normalize_condition(args.get("condition"))
        if condition:
            sanitized["condition"] = condition
        return sanitized

    def _needs_phone_budget_followup(self, args: Dict[str, Any], message: str) -> bool:
        category = self._canonical_category(args.get("category") or "")
        if category != "phone":
            return False
        has_constraint = any(
            args.get(key) not in (None, "", {}, [])
            for key in ("max_price", "min_price", "location", "brand")
        )
        if has_constraint:
            return False
        raw = message.lower().strip()
        return raw in {"i want a phone", "i want phone", "want a phone", "phone", "phones"} or raw.startswith("i want a phone")

    def _slots_from_args(self, args: Dict[str, Any], *, message: str) -> Dict[str, Any]:
        category = self._canonical_category(args.get("category") or "")
        slots = {
            "product_type": category or None,
            "category": None,
            "price_min": args.get("min_price"),
            "price_max": args.get("max_price"),
            "location": args.get("location"),
            "brand": args.get("brand"),
            "price_intent": args.get("price_intent"),
            "condition": self._normalize_condition(args.get("condition")) or "any",
            "raw_query": message,
            "product_intent": "purchase" if category else "unknown",
        }
        if slots["price_max"] is not None or slots["price_min"] is not None:
            slots["budget_range"] = {"min": slots["price_min"], "max": slots["price_max"]}
        return {key: value for key, value in slots.items() if value not in (None, "", {}, []) or key == "category"}

    def _product_broad_q(self, category: str) -> Q:
        if category == "phone":
            return (
                Q(product_family__name__icontains="phone")
                | Q(product_family__name__icontains="iphone")
                | Q(category__name__icontains="phone")
                | Q(title__icontains="iphone")
                | Q(search_tags__icontains="phone")
            )
        if category == "rice":
            return (
                Q(title__icontains="rice")
                | Q(product_family__name__icontains="rice")
                | Q(category__name__icontains="rice")
                | Q(search_tags__icontains="rice")
            )
        if category == "air conditioner":
            return (
                Q(title__icontains="air conditioner")
                | Q(title__icontains="split ac")
                | Q(product_family__name__icontains="air conditioners")
                | Q(category__name__icontains="air conditioners")
                | Q(search_tags__icontains="air conditioner")
            )

        tokens = self._tokens(category)
        query = Q()
        for token in tokens:
            if len(token) < 3:
                continue
            query |= (
                Q(title__icontains=token)
                | Q(product_family__name__icontains=token)
                | Q(category__name__icontains=token)
                | Q(search_tags__icontains=token)
            )
        return query or Q(title__icontains=category)

    def _product_matches_category(self, product: Any, category: str) -> bool:
        category = self._canonical_category(category)
        title = self._normalize_space(getattr(product, "title", ""))
        family = self._normalize_space(getattr(getattr(product, "product_family", None), "name", ""))
        category_name = self._normalize_space(getattr(getattr(product, "category", None), "name", ""))
        text_tokens = set(self._normalized_tokens(product_search_text(product)))

        if category == "phone":
            family_text = f"{family} {category_name}"
            if any(excluded in family_text for excluded in self.PHONE_FAMILY_EXCLUDES):
                return False
            if any(included in family_text for included in self.PHONE_FAMILY_INCLUDES):
                return True
            return "iphone" in self._tokens(title)

        if category == "rice":
            return (
                "rice" in text_tokens
                or "rice grains" in f"{family} {category_name}"
            )

        if category == "air conditioner":
            family_text = f"{title} {family} {category_name}"
            return (
                "air conditioner" in family_text
                or "air conditioners" in family_text
                or "split ac" in family_text
            )

        wanted = self._normalized_tokens(category)
        if not wanted:
            return True
        return all(token in text_tokens for token in wanted)

    def _apply_demo_quality_sort(self, products: List[Any], args: Dict[str, Any]) -> List[Any]:
        max_price = self._safe_decimal(args.get("max_price"))
        price_intent = self._normalize_space(args.get("price_intent"))
        cheap_intent = price_intent == "cheap" or "cheap" in str(args.get("raw_query") or "").lower()
        relevance_terms = self._relevance_terms(args)
        category_terms = self._normalized_tokens(self._canonical_category(args.get("category") or ""))
        brand_terms = self._normalized_tokens(args.get("brand") or "")

        def score(product: Any) -> Tuple[float, float, Decimal]:
            price = self._safe_decimal(getattr(product, "price", None)) or Decimal("0")
            specificity = self._product_specificity_score(
                product,
                relevance_terms=relevance_terms,
                category_terms=category_terms,
                brand_terms=brand_terms,
            )
            value = float(getattr(product, "recommendation_score", 0.0) or 0.0)
            if getattr(product, "is_verified_product", False):
                value += 3.0
            if getattr(product, "is_verified", False):
                value += 1.5
            image = self._product_primary_image_url(product)
            if image and not self._is_no_image_placeholder(image):
                value += 2.5
            value += min(math.log1p(float(getattr(product, "views_count", 0) or 0)), 6.0) * 0.25
            value += min(math.log1p(float(getattr(product, "favorites_count", 0) or 0)), 5.0) * 0.3
            if max_price and max_price > 0:
                ratio = max(0.0, min(1.0, float(price / max_price)))
                if cheap_intent:
                    value += (1.0 - ratio) * 1.2
                else:
                    value += min(ratio / 0.85, 1.0) * 2.0
            components = getattr(product, "recommendation_score_components", {}) or {}
            components["parameter_specificity"] = round(specificity, 4)
            product.recommendation_score_components = components
            product.recommendation_score = round(value + specificity, 4)
            reasons = list(getattr(product, "recommendation_match_reasons", []) or [])
            if specificity >= 70 and "closest match to the requested details" not in reasons:
                reasons.insert(0, "closest match to the requested details")
            product.recommendation_match_reasons = reasons
            return specificity, value, price

        return sorted(products, key=score, reverse=True)

    def _relevance_terms(self, args: Dict[str, Any]) -> List[str]:
        raw_query = args.get("raw_query") or ""
        terms = self._meaningful_query_tokens(raw_query)

        brand_terms = self._normalized_tokens(args.get("brand") or "")
        category_terms = self._normalized_tokens(self._canonical_category(args.get("category") or ""))

        if brand_terms:
            terms.extend(brand_terms)
        if not terms:
            terms.extend(category_terms)
        elif category_terms and len(terms) <= 2:
            terms.extend(category_terms)

        return self._unique_tokens(terms)

    def _meaningful_query_tokens(self, value: Any) -> List[str]:
        tokens = []
        for token in self._normalized_tokens(value):
            if not token or token in self.QUERY_STOPWORDS:
                continue
            if re.fullmatch(r"\d+[km]", token):
                continue
            if token.isdigit() and int(token) >= 1000:
                continue
            tokens.append(token)
        return tokens

    def _product_specificity_score(
        self,
        product: Any,
        *,
        relevance_terms: List[str],
        category_terms: List[str],
        brand_terms: List[str],
    ) -> float:
        fields = self._product_relevance_fields(product)
        high_signal_tokens = (
            fields["title_tokens"]
            + fields["brand_tokens"]
            + fields["family_tokens"]
            + fields["category_tokens"]
        )
        weak_signal_tokens = fields["tag_tokens"] + fields["description_tokens"] + fields["attribute_tokens"]
        all_tokens = high_signal_tokens + weak_signal_tokens

        score = 0.0
        if relevance_terms:
            high_coverage = self._token_coverage(relevance_terms, high_signal_tokens)
            title_coverage = self._token_coverage(relevance_terms, fields["title_tokens"])
            all_coverage = self._token_coverage(relevance_terms, all_tokens)
            weak_only_coverage = max(0.0, all_coverage - high_coverage)
            score += title_coverage * 42.0
            score += self._token_coverage(relevance_terms, fields["brand_tokens"]) * 24.0
            score += self._token_coverage(relevance_terms, fields["family_tokens"]) * 26.0
            score += self._token_coverage(relevance_terms, fields["category_tokens"]) * 22.0
            score += self._ordered_token_score(relevance_terms, fields["title_tokens"]) * 18.0
            score += weak_only_coverage * 6.0
            if high_coverage >= 1.0:
                score += 35.0
            elif high_coverage >= 0.67:
                score += 18.0
            elif high_coverage > 0.0:
                score += 8.0

        if category_terms:
            category_high_coverage = max(
                self._token_coverage(category_terms, fields["title_tokens"]),
                self._token_coverage(category_terms, fields["family_tokens"]),
                self._token_coverage(category_terms, fields["category_tokens"]),
            )
            category_any_coverage = self._token_coverage(category_terms, all_tokens)
            score += category_high_coverage * 28.0
            if category_high_coverage <= 0.0 and category_any_coverage > 0.0:
                score += 3.0

        if brand_terms:
            brand_coverage = max(
                self._token_coverage(brand_terms, fields["brand_tokens"]),
                self._token_coverage(brand_terms, fields["title_tokens"]),
            )
            score += brand_coverage * 40.0

        phrase = " ".join(relevance_terms)
        if len(relevance_terms) > 1 and phrase:
            if phrase in fields["title_text"]:
                score += 45.0
            elif phrase in fields["brand_text"] or phrase in fields["family_text"] or phrase in fields["category_text"]:
                score += 30.0
            elif phrase in fields["all_text"]:
                score += 8.0

        return round(score, 4)

    def _product_relevance_fields(self, product: Any) -> Dict[str, Any]:
        family = getattr(product, "product_family", None)
        category = getattr(product, "category", None)
        title = self._normalize_space(getattr(product, "title", ""))
        brand = self._normalize_space(getattr(product, "brand", ""))
        family_text = self._normalize_space(getattr(family, "name", "") if family else "")
        category_text = self._normalize_space(getattr(category, "name", "") if category else "")
        tags = self._normalize_space(self._flatten_value(getattr(product, "search_tags", None)))
        attributes = self._normalize_space(self._flatten_value(getattr(product, "attributes", None)))
        description = self._normalize_space(getattr(product, "description", ""))
        all_text = self._normalize_space(" ".join([title, brand, family_text, category_text, tags, attributes, description]))
        return {
            "title_text": title,
            "brand_text": brand,
            "family_text": family_text,
            "category_text": category_text,
            "all_text": all_text,
            "title_tokens": self._normalized_tokens(title),
            "brand_tokens": self._normalized_tokens(brand),
            "family_tokens": self._normalized_tokens(family_text),
            "category_tokens": self._normalized_tokens(category_text),
            "tag_tokens": self._normalized_tokens(tags),
            "attribute_tokens": self._normalized_tokens(attributes),
            "description_tokens": self._normalized_tokens(description),
        }

    def _token_coverage(self, wanted: Iterable[str], actual: Iterable[str]) -> float:
        wanted_set = set(self._unique_tokens(wanted))
        if not wanted_set:
            return 0.0
        actual_set = set(actual)
        return len(wanted_set.intersection(actual_set)) / len(wanted_set)

    def _ordered_token_score(self, wanted: List[str], actual: List[str]) -> float:
        wanted = self._unique_tokens(wanted)
        if not wanted or not actual:
            return 0.0
        best_run = 0
        for start in range(len(actual)):
            run = 0
            for offset, token in enumerate(wanted):
                index = start + offset
                if index >= len(actual) or actual[index] != token:
                    break
                run += 1
            best_run = max(best_run, run)
        return best_run / len(wanted)

    def _unique_tokens(self, tokens: Iterable[str]) -> List[str]:
        unique = []
        seen = set()
        for token in tokens:
            normalized = self._normalize_space(token)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique

    def _dedupe_products(self, products: List[Any]) -> List[Any]:
        unique = []
        seen_titles = set()
        for product in products:
            title_key = self._normalize_space(getattr(product, "title", ""))
            if title_key and title_key in seen_titles:
                continue
            if title_key:
                seen_titles.add(title_key)
            unique.append(product)
        return unique

    def _serialize_products(self, products: Iterable[Any], match_type: str = "match") -> List[Dict[str, Any]]:
        suggestions = []
        for product in list(products or [])[: self.MAX_RESULTS]:
            location = ""
            if getattr(product, "location_id", None) and getattr(product, "location", None):
                location = str(product.location)

            category_name = ""
            if getattr(product, "category_id", None) and getattr(product, "category", None):
                category_name = getattr(product.category, "name", "") or ""

            suggestions.append(
                {
                    "id": str(product.id),
                    "title": product.title,
                    "slug": product.slug,
                    "product_url": f"/product/{product.slug}",
                    "price": str(product.price),
                    "condition": getattr(product, "condition", "") or "",
                    "brand": getattr(product, "brand", "") or "",
                    "location": location,
                    "category": category_name,
                    "primary_image": self._product_primary_image_url(product),
                    "image_url": self._product_primary_image_url(product),
                    "match_type": match_type,
                    "is_verified": bool(getattr(product, "is_verified", False)),
                    "is_verified_product": bool(getattr(product, "is_verified_product", False)),
                    "ranking": {
                        "total_score": float(getattr(product, "recommendation_score", 0.0) or 0.0),
                        "components": getattr(product, "recommendation_score_components", {}) or {},
                    },
                    "match_reasons": getattr(product, "recommendation_match_reasons", []) or [],
                }
            )
        return suggestions

    def _final_response(
        self,
        *,
        reply: str,
        session: Optional[ConversationSession],
        products: List[Any],
        intent: str,
        confidence: float,
        source: str,
        slots: Dict[str, Any],
        turn_type: Optional[str] = None,
        turn_outcome: Optional[str] = None,
        groq_error: str = "",
    ) -> Dict[str, Any]:
        serialized = self._serialize_products(products)
        metadata = {
            "assistant_mode": getattr(session, "assistant_mode", "homepage_reco") if session else "homepage_reco",
            "assistant_lane": getattr(session, "assistant_lane", "inbox") if session else "inbox",
            "intent": intent,
            "knowledge_lane": "homepage_reco_catalog",
            "retrieval_system": "gigi_groq_tool_agent",
            "retrieval_source": "market.Product",
            "suggested_products": serialized,
            "suggested_product_count": len(serialized),
            "active_product_family": slots.get("product_type") or slots.get("category") or "",
            "exact_match_found": bool(serialized),
            "no_exact_match": not bool(serialized) and intent == "product_search",
            "match_contract": "deterministic_filtered_active_inventory",
            "hard_constraints": self._hard_constraint_snapshot(slots),
            "turn_type": turn_type,
            "turn_outcome": turn_outcome,
            "groq_available": self.adapter.is_available(),
        }
        if groq_error:
            metadata["groq_fallback_reason"] = groq_error

        return {
            "reply": reply,
            "products": serialized,
            "confidence": float(confidence),
            "source": source,
            "metadata": metadata,
            "drift_detected": False,
        }

    def _update_session(
        self,
        *,
        session: Optional[ConversationSession],
        slots: Dict[str, Any],
        products: List[Any],
        intent: str,
        turn_type: str,
        turn_outcome: Optional[str],
    ) -> None:
        if session is None:
            return

        next_slots = dict(slots or {})
        if products:
            next_slots["_shown_product_ids"] = [str(product.id) for product in products[: self.MAX_RESULTS]]

        session.constraint_state = next_slots
        session.intent_state = {
            **(session.intent_state if isinstance(session.intent_state, dict) else {}),
            "last_intent": intent,
            "last_turn_type": turn_type,
            "last_turn_outcome": turn_outcome,
        }
        session.context_type = ConversationSession.CONTEXT_TYPE_RECOMMENDATION
        if products:
            session.active_product = products[0]
        session.drift_flag = False

        update_fields = ["constraint_state", "intent_state", "context_type", "drift_flag", "updated_at"]
        if products:
            update_fields.append("active_product")
        session.save(update_fields=update_fields)

    def append_ephemeral_turn(
        self,
        *,
        session: ConversationSession,
        user_message: str,
        assistant_reply: str,
        assistant_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist guest homepage turns because the normal ContextManager is not used there."""

        history = session.conversation_history if isinstance(session.conversation_history, list) else []
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        history.extend(
            [
                {
                    "role": "user",
                    "content": self._clean_text(user_message)[:4000],
                    "timestamp": timestamp,
                    "intent": "product_search",
                    "emotion": "neutral",
                    "confidence": 0.0,
                },
                {
                    "role": "assistant",
                    "content": self._clean_text(assistant_reply)[:4000],
                    "timestamp": timestamp,
                    "intent": "product_search",
                    "emotion": "neutral",
                    "confidence": 0.9,
                    "metadata": assistant_metadata or {},
                },
            ]
        )
        session.conversation_history = history[-400:]
        session.message_count = len(session.conversation_history)
        session.save(update_fields=["conversation_history", "message_count", "updated_at"])

    def _format_results_reply(self, args: Dict[str, Any], products: List[Any]) -> str:
        category = self._friendly_category(args.get("category"))
        budget = self._safe_decimal(args.get("max_price"))
        if budget is not None:
            intro = f"Nice, I found {category} options under {self._format_price(budget)} that are worth considering:"
        else:
            intro = f"I found active {category} listings for you:"

        lines = [intro]
        for index, product in enumerate(products[:3], start=1):
            location = str(product.location) if getattr(product, "location_id", None) and product.location else "location not listed"
            condition = self._humanize_condition(getattr(product, "condition", ""))
            lines.append(
                f"{index}. {product.title} - {self._format_price(product.price)} - {condition} - {location}"
            )
        lines.append("Want me to narrow these by brand, location, or condition?")
        return "\n".join(lines)

    def _format_no_results_reply(self, args: Dict[str, Any]) -> str:
        category = self._friendly_category(args.get("category"))
        budget = self._safe_decimal(args.get("max_price"))
        location = self._clean_text(args.get("location"))
        filters = []
        if budget is not None:
            filters.append(f"under {self._format_price(budget)}")
        if location:
            filters.append(f"in {location.title()}")
        filter_text = f" {' '.join(filters)}" if filters else ""
        return f"I could not find active {category} listings{filter_text} right now. Should I widen one filter and check again?"

    def _hard_constraint_snapshot(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        constraints = {"stock": "active_quantity_gt_0"}
        for key in ("product_type", "brand", "condition", "location", "price_min", "price_max"):
            value = slots.get(key)
            if value not in (None, "", {}, []):
                constraints[key] = value
        return constraints

    def _log_demand_gap(self, session: Optional[ConversationSession], slots: Dict[str, Any]) -> None:
        try:
            log_demand_gap(
                raw_query=str(slots.get("raw_query") or ""),
                structured_filters={
                    "category": slots.get("product_type") or "",
                    "location": slots.get("location") or "",
                    "min_price": slots.get("price_min"),
                    "max_price": slots.get("price_max"),
                    "condition": slots.get("condition"),
                    "brand": slots.get("brand"),
                },
                user=getattr(session, "user", None) if session else None,
                source="homepage_reco",
            )
        except Exception as exc:
            logger.warning("Gigi demand gap logging failed: %s", exc)

    def _reply_mentions_unknown_product(self, reply: str, products: List[Any]) -> bool:
        if not reply:
            return False
        known_titles = [self._normalize_space(getattr(product, "title", "")) for product in products]
        bold_titles = re.findall(r"\*\*(.+?)\*\*", reply)
        for title in bold_titles:
            normalized = self._normalize_space(title)
            if normalized and normalized not in known_titles:
                return True
        return False

    def _load_products_by_ids(self, product_ids: Iterable[Any]) -> List[Any]:
        ids = [str(product_id) for product_id in product_ids if str(product_id or "").strip()]
        if not ids:
            return []
        try:
            from market.models import Product

            products = list(
                Product.objects.filter(id__in=ids, status="active", quantity__gt=0).select_related(
                    "category",
                    "product_family",
                    "location",
                    "seller",
                )
            )
            by_id = {str(product.id): product for product in products}
            return [by_id[product_id] for product_id in ids if product_id in by_id]
        except Exception as exc:
            logger.warning("Could not reload prior Gigi products: %s", exc)
            return []

    def _session_slots(self, session: Optional[ConversationSession]) -> Dict[str, Any]:
        if session is None:
            return {}
        slots = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        return dict(slots)

    def _normalize_history(self, history: List[Dict[str, Any]], *, current_message: str) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for entry in history[-self.MAX_HISTORY_MESSAGES :]:
            if not isinstance(entry, dict):
                continue
            role = str(entry.get("role") or entry.get("sender") or "").strip().lower()
            if role in {"ai", "bot"}:
                role = "assistant"
            if role not in {"user", "assistant"}:
                continue
            content = self._clean_text(entry.get("content") or entry.get("text") or entry.get("message"))
            if not content:
                continue
            normalized.append({"role": role, "content": content[:1500]})

        if normalized and normalized[-1]["role"] == "user" and normalized[-1]["content"] == current_message:
            return normalized
        return normalized

    def _canonical_product_from_text(self, text: str) -> str:
        normalized = f" {self._normalize_space(text)} "
        for canonical, aliases in self.PRODUCT_ALIASES:
            for alias in sorted(aliases, key=len, reverse=True):
                alias_normalized = self._normalize_space(alias)
                if not alias_normalized:
                    continue
                if len(alias_normalized) <= 2:
                    if re.search(rf"(?<![a-z0-9]){re.escape(alias_normalized)}(?![a-z0-9])", normalized):
                        return canonical
                    continue
                if re.search(rf"(?<![a-z0-9]){re.escape(alias_normalized)}s?(?![a-z0-9])", normalized):
                    return canonical
        return ""

    def _canonical_category(self, value: Any) -> str:
        text = self._normalize_space(value)
        if not text:
            return ""
        detected = self._canonical_product_from_text(text)
        if detected:
            return detected
        if text in {"smartphones", "mobile phones", "iphone", "iphones"}:
            return "phone"
        if text in {"bags of rice", "bag rice"}:
            return "rice"
        return text

    def _extract_price(self, raw: str) -> Tuple[Optional[float], Optional[float]]:
        text = raw.lower().replace(",", "")
        pattern = re.compile(
            r"(?:\u20a6|ngn|n)?\s*(\d+(?:\.\d+)?)\s*(k|m|million|thousand)?",
            re.IGNORECASE,
        )
        values: List[float] = []
        for match in pattern.finditer(text):
            number_text = match.group(1)
            suffix = (match.group(2) or "").lower()
            try:
                value = float(number_text)
            except ValueError:
                continue
            if suffix == "k" or suffix == "thousand":
                value *= 1000
            elif suffix == "m" or suffix == "million":
                value *= 1000000
            if value >= 1000:
                values.append(value)

        if not values:
            return None, None

        value = values[-1]
        min_markers = {"above", "over", "from", "at least", "minimum", "min"}
        if any(marker in text for marker in min_markers) and not any(
            marker in text for marker in ("under", "below", "less than", "max", "budget")
        ):
            return None, value
        return value, None

    def _extract_condition(self, raw: str) -> str:
        text = raw.lower()
        if any(token in text for token in ("brand new", "new one", "new phone", "new only", "unused")):
            return "new"
        if any(token in text for token in ("used", "fairly used", "tokunbo", "second hand", "pre-owned", "pre owned")):
            return "used"
        return ""

    def _extract_price_intent(self, raw: str) -> str:
        text = raw.lower()
        if re.search(r"\b(?:premium|high[-\s]?end|flagship|luxury|best quality|top quality)\b", text):
            return "premium"
        if re.search(r"\b(?:cheap|budget|affordable|low[-\s]?cost|inexpensive|cheaper|lowest price)\b", text):
            return "cheap"
        return ""

    def _extract_location(self, raw: str) -> str:
        try:
            from market.models import Location

            text = self._normalize_space(raw)
            if not text:
                return ""
            values = set()
            for row in Location.objects.filter(is_active=True).values("state", "city", "area"):
                for key in ("area", "city", "state"):
                    value = self._normalize_space(row.get(key))
                    if len(value) >= 3:
                        values.add(value)
            for value in sorted(values, key=len, reverse=True):
                if re.search(rf"(?<![a-z0-9]){re.escape(value)}(?![a-z0-9])", text):
                    return value
        except Exception as exc:
            logger.debug("Location extraction skipped: %s", exc)
        return ""

    def _extract_brand(self, raw: str) -> str:
        try:
            from market.models import Product

            text = self._normalize_space(raw)
            if not text:
                return ""
            brands = [
                str(brand).strip()
                for brand in Product.objects.filter(status="active").exclude(brand="").values_list("brand", flat=True).distinct()
                if str(brand).strip()
            ]
            for brand in sorted(set(brands), key=len, reverse=True):
                normalized = self._normalize_space(brand)
                if len(normalized) < 3:
                    continue
                if re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text):
                    return brand
        except Exception as exc:
            logger.debug("Brand extraction skipped: %s", exc)
        return ""

    def _normalize_condition(self, value: Any) -> str:
        condition = self._normalize_space(value)
        if condition in {"", "any", "unknown"}:
            return "any" if condition == "any" else ""
        if condition in {"used", "fairly used", "second hand", "pre owned", "pre-owned", "tokunbo"}:
            return "used"
        if condition in {"new", "brand new", "unused"}:
            return "new"
        if condition in {"like_new", "like new", "good", "fair", "poor"}:
            return condition.replace(" ", "_")
        return ""

    def _product_primary_image_url(self, product: Any) -> str:
        image = getattr(product, "image_url", "") or getattr(product, "image_url_locked", "") or ""
        return str(image).strip()

    def _is_no_image_placeholder(self, value: str) -> bool:
        return "placehold.co" in value and "No+Image" in value

    def _format_price(self, value: Any) -> str:
        number = self._safe_decimal(value)
        if number is None:
            return "price on listing"
        return f"{NAIRA}{number:,.0f}"

    def _friendly_category(self, value: Any) -> str:
        category = self._canonical_category(value)
        if category == "phone":
            return "phone"
        if category == "rice":
            return "rice"
        return category or "product"

    def _humanize_condition(self, value: Any) -> str:
        text = str(value or "").replace("_", " ").strip()
        return text.title() if text else "condition not listed"

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _clean_text(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    def _normalize_space(self, value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    def _flatten_value(self, value: Any) -> str:
        if isinstance(value, dict):
            parts = []
            for key in sorted(value):
                flattened = self._flatten_value(value[key])
                if flattened:
                    parts.append(f"{key} {flattened}")
            return " ".join(parts)
        if isinstance(value, (list, tuple, set)):
            return " ".join(self._flatten_value(item) for item in value if item not in (None, ""))
        if value in (None, ""):
            return ""
        return str(value).strip()

    def _tokens(self, value: Any) -> List[str]:
        return re.findall(r"[a-z0-9]+", str(value or "").lower())

    def _normalized_tokens(self, value: Any) -> List[str]:
        normalized = []
        for token in self._tokens(value):
            if len(token) > 4 and token.endswith("s"):
                token = token[:-1]
            normalized.append(token)
        return normalized
