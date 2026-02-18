#!/usr/bin/env python3
"""Analyze FAQ duplication and metadata coverage for retrieval quality hardening."""
import json
from collections import Counter
from pathlib import Path

FAQ_PATH = Path(__file__).resolve().parents[1] / 'assistant' / 'data' / 'updated_faq.json'


def normalize(text: str) -> str:
    return ' '.join((text or '').strip().lower().split())


def main():
    payload = json.loads(FAQ_PATH.read_text(encoding='utf-8'))
    faqs = payload.get('faqs', [])

    questions = [normalize(f.get('question', '')) for f in faqs]
    question_counts = Counter(questions)
    duplicates = {q: c for q, c in question_counts.items() if c > 1}

    missing_keywords = [f.get('id') for f in faqs if not f.get('keywords')]

    print(f"total_faqs={len(faqs)}")
    print(f"duplicate_questions={len(duplicates)}")
    print(f"missing_keywords={len(missing_keywords)}")

    if duplicates:
        print('top_duplicates:')
        for q, c in sorted(duplicates.items(), key=lambda item: item[1], reverse=True)[:20]:
            print(f"- count={c} question={q}")


if __name__ == '__main__':
    main()
