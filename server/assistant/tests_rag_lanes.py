import json
from collections import Counter
from pathlib import Path

from django.core.cache import cache
from django.test import TestCase

from assistant.processors.query_processor import QueryProcessor
from assistant.processors.rag_retriever import RAG_LANES


FAQ_PATH = Path(__file__).resolve().parent / 'data' / 'updated_faq.json'
DEDUPED_PATH = Path(__file__).resolve().parent / 'data' / 'updated_faq_deduped.json'


def _normalized_question(faq):
    return ' '.join((faq.get('question') or '').strip().lower().split())


class LaneSeparatedRAGTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payload = json.loads(FAQ_PATH.read_text(encoding='utf-8'))
        cls.faqs = cls.payload.get('faqs', [])

    def setUp(self):
        cache.clear()
        self.processor = QueryProcessor()

    def test_single_canonical_faq_source_exists(self):
        self.assertTrue(FAQ_PATH.exists())
        self.assertFalse(DEDUPED_PATH.exists())
        self.assertTrue(self.payload.get('source_of_truth'))
        self.assertEqual(len(self.faqs), 212)

    def test_every_faq_has_one_valid_primary_lane_and_priority(self):
        valid_priorities = {'critical', 'useful', 'low-value', 'obsolete'}
        for faq in self.faqs:
            self.assertIn(faq.get('primary_lane'), RAG_LANES)
            self.assertIn(faq.get('priority'), valid_priorities)
            self.assertIsInstance(faq.get('secondary_tags'), list)

        normalized_questions = [_normalized_question(faq) for faq in self.faqs]
        duplicate_questions = [
            question for question, count in Counter(normalized_questions).items()
            if count > 1
        ]
        self.assertEqual(duplicate_questions, [])

    def test_lane_inference_examples(self):
        examples = {
            'How do I get started as a new seller on Zunto?': 'seller_support',
            'What makes Zunto different from other marketplaces?': 'platform_help',
            'How do I track my order?': 'buyer_support',
            'What proof is required for disputes?': 'dispute_resolution',
            'How do I reset my password?': 'trust_safety_account',
        }
        for query, expected_lane in examples.items():
            with self.subTest(query=query):
                self.assertEqual(
                    self.processor._infer_rag_lane(query),
                    expected_lane,
                )

    def test_search_returns_lane_local_new_knowledge(self):
        seller = self.processor._search_faqs_multiple(
            'How do I get started as a new seller on Zunto?'
        )
        self.assertTrue(seller)
        self.assertEqual(seller[0]['lane'], 'seller_support')
        self.assertEqual(int(seller[0]['id']), 221)

        platform = self.processor._search_faqs_multiple(
            'What makes Zunto different from other marketplaces?'
        )
        self.assertTrue(platform)
        self.assertEqual(platform[0]['lane'], 'platform_help')
        self.assertEqual(int(platform[0]['id']), 222)

    def test_buyer_and_dispute_queries_do_not_cross_lanes(self):
        tracking = self.processor._search_faqs_multiple('How do I track my order?')
        self.assertTrue(tracking)
        self.assertEqual(tracking[0]['lane'], 'buyer_support')
        self.assertIn(
            'track',
            f"{tracking[0].get('question', '')} {tracking[0].get('answer', '')}".lower(),
        )

        proof = self.processor._search_faqs_multiple('What proof is required for disputes?')
        self.assertTrue(proof)
        self.assertEqual(proof[0]['lane'], 'dispute_resolution')
        self.assertEqual(int(proof[0]['id']), 140)

    def test_same_query_cache_is_isolated_by_lane(self):
        query = 'proof required'
        dispute = self.processor._search_faqs_multiple(query, lane='dispute_resolution')
        trust = self.processor._search_faqs_multiple(query, lane='trust_safety_account')

        self.assertTrue(dispute)
        self.assertTrue(trust)
        self.assertTrue(all(item['lane'] == 'dispute_resolution' for item in dispute))
        self.assertTrue(all(item['lane'] == 'trust_safety_account' for item in trust))
