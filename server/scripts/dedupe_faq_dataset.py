#!/usr/bin/env python3
"""Deduplicate FAQ dataset and enrich metadata tags before re-embedding."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / 'assistant' / 'data' / 'updated_faq.json'
OUTPUT_PATH = ROOT / 'assistant' / 'data' / 'updated_faq_deduped.json'


def normalize_question(text: str) -> str:
    return ' '.join((text or '').strip().lower().split())


def infer_section(keywords: List[str], question: str) -> str:
    text = f"{question} {' '.join(keywords or [])}".lower()
    rules = [
        ('account_access', ('account', 'login', 'password', 'profile', 'verify', 'registration')),
        ('orders_shipping', ('order', 'tracking', 'delivery', 'shipping', 'shipment')),
        ('returns_disputes', ('refund', 'return', 'dispute', 'complaint', 'damaged')),
        ('seller_tools', ('seller', 'listing', 'commission', 'withdraw', 'dashboard')),
        ('trust_safety', ('scam', 'fraud', 'security', 'safe', 'report')),
    ]
    for section, terms in rules:
        if any(term in text for term in terms):
            return section
    return 'general'


def dedupe_faqs(faqs: List[Dict]) -> Dict:
    grouped = defaultdict(list)
    for faq in faqs:
        grouped[normalize_question(faq.get('question', ''))].append(faq)

    deduped = []
    duplicate_groups = 0
    removed = 0

    for normalized_question, items in grouped.items():
        canonical = dict(items[0])
        all_keywords = []
        for entry in items:
            all_keywords.extend(entry.get('keywords') or [])

        canonical['keywords'] = sorted({k.strip() for k in all_keywords if k and k.strip()})
        canonical['metadata'] = canonical.get('metadata') or {}
        canonical['metadata']['section'] = infer_section(canonical['keywords'], canonical.get('question', ''))
        canonical['metadata']['duplicate_count'] = len(items)

        if len(items) > 1:
            duplicate_groups += 1
            removed += len(items) - 1

        deduped.append(canonical)

    deduped.sort(key=lambda f: int(f.get('id', 0)))
    return {
        'faqs': deduped,
        'stats': {
            'input_total': len(faqs),
            'deduped_total': len(deduped),
            'duplicate_groups': duplicate_groups,
            'duplicates_removed': removed,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Deduplicate assistant FAQ corpus.')
    parser.add_argument('--in-place', action='store_true', help='Overwrite the input file directly.')
    args = parser.parse_args()

    payload = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    faqs = payload.get('faqs', [])

    result = dedupe_faqs(faqs)
    output_file = INPUT_PATH if args.in_place else OUTPUT_PATH

    output_file.write_text(
        json.dumps({'faqs': result['faqs']}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    stats = result['stats']
    print(f"input_total={stats['input_total']}")
    print(f"deduped_total={stats['deduped_total']}")
    print(f"duplicate_groups={stats['duplicate_groups']}")
    print(f"duplicates_removed={stats['duplicates_removed']}")
    print(f"output={output_file}")


if __name__ == '__main__':
    main()
