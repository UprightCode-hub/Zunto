#!/usr/bin/env python3
"""Analyze FAQ duplication and metadata coverage for retrieval quality hardening."""
import json
from collections import Counter
from pathlib import Path

FAQ_PATH = Path(__file__).resolve().parents[1] / 'assistant' / 'data' / 'updated_faq.json'
VALID_LANES = {
    'homepage_reco_catalog',
    'buyer_support',
    'seller_support',
    'dispute_resolution',
    'platform_help',
    'trust_safety_account',
}


def normalize(text: str) -> str:
    return ' '.join((text or '').strip().lower().split())


def main():
    payload = json.loads(FAQ_PATH.read_text(encoding='utf-8'))
    faqs = payload.get('faqs', [])

    questions = [normalize(f.get('question', '')) for f in faqs]
    question_counts = Counter(questions)
    duplicates = {q: c for q, c in question_counts.items() if c > 1}

    missing_keywords = [f.get('id') for f in faqs if not f.get('keywords')]
    missing_lane = [f.get('id') for f in faqs if f.get('primary_lane') not in VALID_LANES]
    lane_counts = Counter(f.get('primary_lane') for f in faqs)

    print(f"total_faqs={len(faqs)}")
    print(f"source_of_truth={payload.get('source_of_truth') is True}")
    print(f"duplicate_questions={len(duplicates)}")
    print(f"missing_keywords={len(missing_keywords)}")
    print(f"missing_or_invalid_lane={len(missing_lane)}")
    print('lane_counts:')
    for lane, count in sorted(lane_counts.items()):
        print(f"- {lane}: {count}")

    if duplicates:
        print('top_duplicates:')
        for q, c in sorted(duplicates.items(), key=lambda item: item[1], reverse=True)[:20]:
            print(f"- count={c} question={q}")


if __name__ == '__main__':
    main()
