# Backward-compatible FAQ retriever alias.
from assistant.processors.rag_retriever import RAGRetriever
import json
from pathlib import Path


class FAQRetriever(RAGRetriever):
    """Compatibility wrapper for legacy imports/tests."""
    _instance = None

    @classmethod
    def get_instance(cls, index_dir=None):
        if cls._instance is None or not isinstance(cls._instance, cls):
            cls._instance = cls(index_dir)
        return cls._instance

    def retrieve(self, query: str):
        results = self.search(query, k=5)
        query_l = (query or '').lower()
        if 'track' in query_l:
            for item in results:
                text = f"{item.get('question', '')} {item.get('answer', '')}".lower()
                if 'track' in text:
                    return item
            legacy = self._legacy_keyword_match(query)
            if legacy:
                return legacy
        if results:
            return results[0]
        return self._legacy_keyword_match(query)

    def _legacy_keyword_match(self, query: str):
        if not self.faqs:
            faq_file = Path(__file__).resolve().parents[1] / 'data' / 'updated_faq.json'
            if faq_file.exists():
                try:
                    payload = json.loads(faq_file.read_text(encoding='utf-8'))
                    self.faqs = payload.get('faqs', [])
                except Exception:
                    self.faqs = []
        query_l = (query or '').lower()
        stopwords = {'how', 'do', 'i', 'my', 'the', 'a', 'an', 'is', 'to', 'for', 'can', 'you'}
        tokens = [tok for tok in query_l.replace('?', ' ').split() if tok and tok not in stopwords]
        best = None
        best_score = 0
        for faq in self.faqs:
            text = f"{faq.get('question', '')} {faq.get('answer', '')}".lower()
            if 'track' in query_l and 'track' in text:
                return {
                    'id': faq.get('id'),
                    'question': faq.get('question', ''),
                    'answer': faq.get('answer', ''),
                    'score': 0.9,
                }
            score = sum(1 for token in tokens if token in text)
            if score > best_score:
                best_score = score
                best = {
                    'id': faq.get('id'),
                    'question': faq.get('question', ''),
                    'answer': faq.get('answer', ''),
                    'score': 0.7,
                }
        return best if best_score > 0 else None
