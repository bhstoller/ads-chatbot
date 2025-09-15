import streamlit as st
import os
import chromadb
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA, LLMChain
from langchain.prompts import PromptTemplate
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from utils.load_documents import load_raw_docs
from utils.reranker import CrossEncoderReranker
from utils.filters import filter_expired_deadlines
from datetime import date
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()
# NEW (go up one level: src/app -> src)
DEFAULT_CHROMA_PATH = (Path(__file__).parent.parent / "data" / "chroma_rag_store").resolve()

DATE_TODAY = date.today().strftime("%B %d, %Y")

# Define your system prompt once
SYSTEM_PLUS_USER = f"""\
You are the official AI assistant for the University of Chicago’s MS in Applied Data Science program.
Use only the following extracted documents to answer — do not hallucinate.
Today’s date is {DATE_TODAY}. Do not list deadlines that have already passed relative to today.

If the answer cannot be verified from the official program information, do not guess.
Instead, politely tell the user you cannot confirm and provide the admissions contact email:
applieddatascience-admissions@uchicago.edu

Context:
{{context}}

Question:
{{question}}

Answer:
"""


class RAGChatApp:
    def __init__(self):
        st.set_page_config(
            page_title="RAG Chat App",
            page_icon="🤖",
            layout="wide"
        )
        self.chroma_store_path = os.getenv("CHROMA_PERSIST_DIR", str(DEFAULT_CHROMA_PATH))
        Path(self.chroma_store_path).mkdir(parents=True, exist_ok=True)

        self.embeddings = None
        self.llm = None
        self.vectorstore = None
        self.reranker = CrossEncoderReranker()
        self.openai_api_key = None

        # Prompt template for RAG chain
        self.chat_prompt = PromptTemplate(
            template=SYSTEM_PLUS_USER,
            input_variables=["context", "question"],
        )

        self.load_chroma_db()

    def _require_api_key(self):
        """Ensure an OpenAI API key is present."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.openai_api_key:
            st.error("OPENAI_API_KEY not found. Add it to .env (in src/app) or export it in your shell.")
            st.stop()

    def load_chroma_db(self):
        self._require_api_key()

        # Make sure the directory exists
        Path(self.chroma_store_path).mkdir(parents=True, exist_ok=True)

        # Optional: show where we’re writing
        st.write(f"Using Chroma directory: {self.chroma_store_path}")

        # Initialize embeddings (keep model consistent with your index)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

        # ✅ New Chroma client initialization
        client = chromadb.PersistentClient(path=str(self.chroma_store_path))

        self.vectorstore = Chroma(
            client=client,
            collection_name="langchain",   # use the same name your index was built with
            embedding_function=self.embeddings,
        )

    def run(self):
        if "messages" not in st.session_state:
            st.session_state.messages = []

        self._require_api_key()

        st.title("🤖 Conversational AI for the MSADS")

        # Show past chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                if not self.openai_api_key:
                    st.error("Please configure your OpenAI API key")
                else:
                    # Init LLM
                    self.llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

                    # ---- HYBRID RETRIEVER ----
                    retriever = self.vectorstore.as_retriever(search_kwargs={"k": 10})
                    # --------------------------

                    # Get top 20 docs
                    retrieved_docs = retriever.get_relevant_documents(prompt)
                    retrieved_docs = filter_expired_deadlines(retrieved_docs)

                    # ---- RE-RANKING ----
                    reranked_docs = self.reranker.rerank(prompt, retrieved_docs, top_k=5)
                    # -------------------

                    # Build chain manually (stuff top docs into prompt)
                    context = "\n\n".join([doc.page_content for doc in reranked_docs])
                    final_prompt = PromptTemplate(
                        template=(
                            "You are the official AI assistant for the University of Chicago’s MS in Applied Data Science program. "
                            "Answer the question using only official program information. "
                            "Be direct, professional, and concise — as if you were an admissions officer responding on the website. "
                            "Do not mention documents, context, or sources in your answer.\n\n"
                            "The admissions office is applieddatascience-admissions@uchicago.edu "
                            "Official Information:\n{context}\n\n"
                            "Question: {question}\n"
                            "Answer:"
                        ),
                        input_variables=["context", "question"]
                    )
                    chain = LLMChain(llm=self.llm, prompt=final_prompt)
                    answer = chain.run(context=context, question=prompt).strip()

                    st.markdown("**Answer:**")
                    st.markdown(answer if answer else "_No answer returned._")

                    # Show sources
                    sources = "\n".join(
                        f"- {doc.metadata.get('source', 'Unknown source')}"
                        for doc in reranked_docs
                    )
                    if sources:
                        st.markdown("**Sources:**")
                        st.markdown(sources)

                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )


def main():
    app = RAGChatApp()
    app.run()


if __name__ == "__main__":
    main()
