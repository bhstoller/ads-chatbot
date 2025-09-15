import nest_asyncio
import asyncio
import os
import hashlib
from urllib.parse import urlparse
from pathlib import Path

from playwright.async_api import async_playwright
from langchain.schema import Document
from langchain.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

from dotenv import load_dotenv
load_dotenv()

# Maximum filename length (without extension)
MAX_FILENAME_LENGTH = 100

class SiteRAGPipeline:
    def __init__(
        self,
        base_url: str,
        max_pages: int = 150,
        crawl_delay: int = 1,
        render_wait: int = 5,
        headless: bool = True,
    ):
        """
        Initializes the pipeline with crawling and RAG parameters.

        Args:
            base_url: Root URL to start crawling.
            max_pages: Max pages to visit.
            crawl_delay: Seconds between page crawls.
            render_wait: Seconds to wait for rendering.
            headless: Launch browser headless if True.
        """

        self.documents_directory = Path("../data/documents")
        self.documents_directory.mkdir(parents=True, exist_ok=True)

        self.documents_screenshot_directory = Path("../data/documents/screenshots")
        self.documents_screenshot_directory.mkdir(parents=True, exist_ok=True)

        self.chroma_persist_directory = "../data/chroma_rag_store"
        Path(self.chroma_persist_directory).mkdir(parents=True, exist_ok=True)

        self.base_url = base_url
        self.max_pages = max_pages
        self.crawl_delay = crawl_delay
        self.render_wait = render_wait
        self.headless = headless
        self.docs = []
        self.vectordb = None
        self.rag_chain = None

        self.embeddings = OpenAIEmbeddings()

    def _make_safe_name(self, url: str) -> str:
        """
        Converts a URL path into a filesystem-safe name and truncates if too long,
        appending a short hash to avoid collisions.
        """
        raw = urlparse(url).path.strip('/').replace('/', '_') or 'index'
        if len(raw) > MAX_FILENAME_LENGTH:
            hash_suffix = hashlib.md5(raw.encode('utf-8')).hexdigest()[:8]
            raw = raw[:MAX_FILENAME_LENGTH] + '_' + hash_suffix
        return raw

    async def _extract_page(self, page, url: str) -> Document:
        # Wait for rendering and scroll
        await asyncio.sleep(self.render_wait)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        # Extract text and list items
        raw_text = await page.evaluate('''() => {
            const listItems = Array.from(document.querySelectorAll('li'))
                .map(li => '- ' + li.innerText.trim());
            const pageText = document.body.innerText;
            return pageText + '\\n' + listItems.join('\\n');
        }''')

        return Document(page_content=raw_text, metadata={"source": url})

    async def extract_full_page(self, page, url: str) -> Document:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            doc = await self._extract_page(page, url)

            # Screenshot with safe, truncated filename
            safe_name = self._make_safe_name(url)
            screenshot_path = self.documents_screenshot_directory / f"{safe_name}.png"
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"📸 Screenshot saved to {screenshot_path}")
            except Exception as e:
                print(f"❌ Failed to save screenshot: {e}")

            await browser.close()            
            return doc

    async def crawl(self):
        visited = set()
        to_visit = [self.base_url]

        while to_visit and len(visited) < self.max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
                    page = await browser.new_page()
                    await page.goto(url, timeout=60000)
                    doc = await self.extract_full_page(page, url)
                    self.docs.append(doc)

                     # Persist raw text file
                    safe_name = urlparse(url).path.strip('/').replace('/', '_') or 'index'
                    file_path = self.documents_directory / f"{safe_name}.txt"
                    file_path.write_text(doc.page_content, encoding='utf-8')

                    anchors = await page.eval_on_selector_all(
                        "a", "nodes => nodes.map(n => n.href)"
                    )
                    await browser.close()

                visited.add(url)
                print(f"✅ Crawled: {url}")

                for link in anchors:
                    if (
                        urlparse(link).netloc == urlparse(self.base_url).netloc
                        and link.startswith(self.base_url)
                        and link not in visited
                        and link not in to_visit
                    ):
                        to_visit.append(link)

                await asyncio.sleep(self.crawl_delay)

            except Exception as e:
                print(f"❌ Failed to crawl {url}: {e}")

        if not self.docs:
            raise ValueError("❌ No content extracted. Check selectors or page load.")

    def build_vectorstore(self):
        self.vectordb = Chroma.from_documents(
            self.docs, 
            embedding=self.embeddings,
            persist_directory=self.chroma_persist_directory)

    def build_rag_chain(self):        
        # Load persisted vectorstore
        retriever = Chroma(
            persist_directory=self.chroma_persist_directory,
            embedding_function=self.embeddings
        ).as_retriever()

        llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
        self.rag_chain = RetrievalQA.from_chain_type(
            llm=llm, retriever=retriever, return_source_documents=True
        )

    async def run(self) -> RetrievalQA:
        #await self.crawl()
        #self.build_vectorstore()
        self.build_rag_chain()
        return self.rag_chain


if __name__ == "__main__":
    nest_asyncio.apply()

    async def main():
        pipeline = SiteRAGPipeline(
            base_url="https://datascience.uchicago.edu/education/masters-programs/ms-in-applied-data-science/"
        )
        rag = await pipeline.run()

        question = "How do I apply to the MS in Applied Data Science program?"
        result = await rag.ainvoke(question)
        answer = result["result"]
        docs   = result["source_documents"]

        print("\n💬 Answer:\n", answer)
        print("\n📚 Sources:")
        for d in docs:
            print("-", d.metadata["source"])

    asyncio.run(main())