from langchain.document_loaders import DirectoryLoader, TextLoader
from pathlib import Path

def load_raw_docs():
    docs_path = Path(__file__).resolve().parent.parent / "data" / "documents"
    docs = []
    if not docs_path.exists():
        print(f"❌ Path not found: {docs_path}")
        return docs
    loader = DirectoryLoader(
        str(docs_path),
        glob="*.txt",
        loader_cls=TextLoader
    )
    docs = loader.load()
    print(f"✅ Loaded {len(docs)} documents from {docs_path}")
    return docs

