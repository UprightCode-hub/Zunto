"""
Lazy loading for AI models - loads only when needed.
"""
class LazyAILoader:
    """
    Loads AI models only when first used, not at import time.
    This prevents memory usage at startup.
    """
    def __init__(self):
        self._sentence_model = None
        self._faiss_index = None
        self._faiss_module = None
    @property
    def sentence_model(self):
        """Load sentence transformer only when first accessed"""
        if self._sentence_model is None:
            print("🔄 Loading sentence transformer model...")
            try:
                from sentence_transformers import SentenceTransformer
                # Use smallest model possible
                self._sentence_model = SentenceTransformer(
                    'paraphrase-MiniLM-L3-v2',  # Smallest model (~60MB)
                    device='cpu'  # Force CPU to avoid GPU memory
                )
                print("✅ Model loaded successfully")
            except ImportError:
                print("❌ sentence_transformers not installed. RAG features will be disabled.")
                return None
            except Exception as e:
                print(f"❌ Error loading model: {e}")
                return None
        return self._sentence_model

    @property
    def faiss(self):
        """Load FAISS only when first accessed"""
        if self._faiss_module is None:
            print("🔄 Loading FAISS...")
            try:
                import faiss
                self._faiss_module = faiss
                print("✅ FAISS loaded successfully")
            except ImportError:
                print("❌ faiss not installed. RAG features will be disabled.")
                return None
            except Exception as e:
                print(f"❌ Error loading FAISS: {e}")
                return None
        return self._faiss_module
    def create_faiss_index(self, embeddings):
        """Create FAISS index on-demand"""
        if self.faiss is None:
            print("❌ FAISS not available. Cannot create index.")
            return None

        if self._faiss_index is None:
            print("🔄 Creating FAISS index...")
            dimension = embeddings.shape[1]
            self._faiss_index = self.faiss.IndexFlatL2(dimension)
            self._faiss_index.add(embeddings)
            print("✅ FAISS index created")
        return self._faiss_index
    def clear_cache(self):
        """Clear loaded models to free memory"""
        print("🧹 Clearing AI model cache...")
        self._sentence_model = None
        self._faiss_index = None
        self._faiss_module = None
        import gc
        gc.collect()
        print("✅ Cache cleared")
# Global singleton instance
_ai_loader = LazyAILoader()
def get_ai_loader():
    """Get the global AI loader instance"""
    return _ai_loader