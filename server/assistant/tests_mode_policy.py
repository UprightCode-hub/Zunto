import unittest

from assistant.utils.assistant_modes import (
    normalize_assistant_mode,
    resolve_legacy_lane,
    mode_gate_response,
)


class AssistantModePolicyTests(unittest.TestCase):
    def test_normalize_prefers_assistant_mode(self):
        mode = normalize_assistant_mode({'assistant_mode': 'homepage_reco', 'assistant_lane': 'customer_service'})
        self.assertEqual(mode, 'homepage_reco')

    def test_normalize_falls_back_to_legacy_lane(self):
        mode = normalize_assistant_mode({'assistant_lane': 'dispute'})
        self.assertEqual(mode, 'customer_service')

    def test_legacy_lane_mapping(self):
        self.assertEqual(resolve_legacy_lane('inbox_general'), 'inbox')
        self.assertEqual(resolve_legacy_lane('customer_service'), 'customer_service')

    def test_inbox_general_blocks_recommendation_requests(self):
        reply = mode_gate_response('inbox_general', 'Can you recommend a laptop for coding?')
        self.assertIsNotNone(reply)
        self.assertIn('homepage assistant', reply.lower())

    def test_customer_service_blocks_non_dispute(self):
        reply = mode_gate_response('customer_service', 'How do I update my profile?')
        self.assertIsNotNone(reply)
        self.assertIn('disputes only', reply.lower())


if __name__ == '__main__':
    unittest.main()
