from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class CrossEncoderReranker:
    def __init__(self, model_name="BAAI/bge-reranker-base"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

    def rerank(self, query, docs, top_k=5):
        """Re-rank docs based on query relevance and return top_k"""
        pairs = [(query, d.page_content) for d in docs]

        inputs = self.tokenizer(
            [q for q, d in pairs],
            [d for q, d in pairs],
            padding=True,
            truncation=True,
            return_tensors="pt"
        )

        with torch.no_grad():
            scores = self.model(**inputs).logits.view(-1).float()

        scored_docs = list(zip(docs, scores.tolist()))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, _ in scored_docs[:top_k]]
