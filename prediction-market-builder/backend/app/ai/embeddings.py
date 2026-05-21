class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self.__class__._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        return self._get_model().encode(text, normalize_embeddings=True).tolist()

    def encode_market(self, market: dict) -> list[float]:
        text = f"{market.get('title', '')} {market.get('description', '')} {market.get('category', '')}"
        return self.encode(text)
