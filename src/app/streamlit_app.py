import streamlit as st
import os
import chromadb
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from datetime import date
from pathlib import Path

load_dotenv()

# --- Globals ---
DEFAULT_CHROMA_PATH = (Path(__file__).parent.parent / "data" / "chroma_rag_store").resolve()
DATE_TODAY = date.today().strftime("%B %d, %Y")

# System prompt with date + admissions contact
SYSTEM_PLUS_USER = f"""
You are the official AI assistant for the University of Chicago’s MS in Applied Data Science program.
Use only the following extracted documents to answer — do not hallucinate.
Today’s date is {DATE_TODAY}. Do not list deadlines that have already passed relative to today.

If the answer cannot be verified from the official program information, do not guess.
If you cannot find the answer, politely tell the user to reach out to the admissions contact email:
applieddatascience-admissions@uchicago.edu

Context:
{{context}}

Question:
{{question}}

Answer:
"""


class RAGChatApp:
    def __init__(self):
        st.set_page_config(page_title="RAG Chat App", page_icon="🤖", layout="wide")

        self.chroma_store_path = DEFAULT_CHROMA_PATH
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.openai_api_key = None

        self.chat_prompt = PromptTemplate(
            template=SYSTEM_PLUS_USER,
            input_variables=["context", "question"],
        )

        self.load_chroma_db()

    def load_chroma_db(self):
        if os.path.exists(self.chroma_store_path):
            print("✅ Chroma store directory exists.")
            print("Files:", os.listdir(self.chroma_store_path))
        else:
            print("❌ Chroma store directory is missing!")

        self.embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        client = chromadb.PersistentClient(path=str(self.chroma_store_path))
        self.vectorstore = Chroma(
            client=client,
            collection_name="langchain",
            embedding_function=self.embeddings,
        )

    def run(self):
        if "messages" not in st.session_state:
            st.session_state.messages = []

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            st.error("OPENAI_API_KEY not found. Please add it to your environment.")
            st.stop()

        st.title("🤖 Conversational AI for the MSADS")

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})
                    retrieved_docs = retriever.get_relevant_documents(prompt)

                    # Format context
                    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

                    self.llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

                    chain = LLMChain(llm=self.llm, prompt=self.chat_prompt)
                    answer = chain.run(context=context, question=prompt).strip()

                    st.markdown("**Answer:**")
                    st.markdown(answer if answer else "_No answer returned._")

                    # Show sources
                    sources = "\n".join(
                        f"- {doc.metadata.get('source', 'Unknown source')}" for doc in retrieved_docs
                    )
                    if sources:
                        st.markdown("**Sources:**")
                        st.markdown(sources)

                    st.session_state.messages.append({"role": "assistant", "content": answer})

                except Exception as e:
                    st.error(f"⚠️ Error: {e}")


def main():
    app = RAGChatApp()
    app.run()


if __name__ == "__main__":
    main()
