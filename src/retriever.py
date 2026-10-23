"""Hybrid Retrieval (Dense + BM25) and FlashRank Reranker for MITRE STIX Corpus.

Implements RAGIntel's exact retrieval architecture:
1. Dense Retrieval (FAISS + sentence-transformers/all-MiniLM-L6-v2)
2. BM25 Sparse Retrieval (BM25Retriever)
3. Hybrid Union & Deduplication
4. FlashRank Cross-Encoder Reranking (ms-marco-MiniLM-L-12-v2)
5. Disk-persisted index caching for fast restarts.
"""

import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from flashrank import Ranker, RerankRequest
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.corpus import build_stix_raw_documents, split_documents_baseline
from src.data_loader import STIXKnowledgeBase, load_stix_bundle


class HybridSTIXRetriever:
    """Hybrid Dense + BM25 + FlashRank Reranker over STIX knowledge base."""

    def __init__(
        self,
        stix_kb: Optional[STIXKnowledgeBase] = None,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        rerank_model_name: str = "ms-marco-MiniLM-L-12-v2",
        cache_dir: str = ".cache/retriever_index",
        dense_k: int = 15,
        bm25_k: int = 15,
        enable_query_chunking: bool = False,
        custom_documents: Optional[List[Document]] = None,
    ):
        self.embedding_model_name = embedding_model_name
        self.rerank_model_name = rerank_model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.dense_k = dense_k
        self.bm25_k = bm25_k
        self.enable_query_chunking = enable_query_chunking
        self.custom_documents = custom_documents

        # Load embedding model
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        # Load FlashRank ranker
        self.ranker = Ranker(model_name=self.rerank_model_name)

        # Index documents
        self.stix_kb = stix_kb or load_stix_bundle()
        self._initialize_indices()

    def _initialize_indices(self) -> None:
        faiss_cache_path = self.cache_dir / "faiss_index"
        bm25_cache_path = self.cache_dir / "bm25_index.pkl"
        docs_cache_path = self.cache_dir / "child_docs.pkl"

        if (
            faiss_cache_path.exists()
            and bm25_cache_path.is_file()
            and docs_cache_path.is_file()
        ):
            print(f"Loading cached FAISS and BM25 indices from {self.cache_dir}...")
            self.vector_store = FAISS.load_local(
                str(faiss_cache_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            with open(bm25_cache_path, "rb") as f:
                self.bm25_retriever = pickle.load(f)
            with open(docs_cache_path, "rb") as f:
                self.child_docs = pickle.load(f)
            print(f"Loaded {len(self.child_docs)} child documents from cache.")
        else:
            if self.custom_documents is not None:
                print(f"Building fresh indices from {len(self.custom_documents)} custom documents...")
                self.child_docs = self.custom_documents
            else:
                print("Building fresh STIX corpus and indices...")
                raw_docs = build_stix_raw_documents(self.stix_kb)
                parent_docs, self.child_docs = split_documents_baseline(raw_docs)
                print(f"STIX raw docs: {len(raw_docs)}, parents: {len(parent_docs)}, child chunks: {len(self.child_docs)}")

            print("Encoding child chunks with FAISS...")
            self.vector_store = FAISS.from_documents(self.child_docs, self.embeddings)
            self.vector_store.save_local(str(faiss_cache_path))

            print("Building BM25 retriever...")
            self.bm25_retriever = BM25Retriever.from_documents(self.child_docs)
            self.bm25_retriever.k = self.bm25_k
            with open(bm25_cache_path, "wb") as f:
                pickle.dump(self.bm25_retriever, f)

            with open(docs_cache_path, "wb") as f:
                pickle.dump(self.child_docs, f)

            print(f"Successfully cached FAISS and BM25 indices to {self.cache_dir}")

        self.dense_retriever = self.vector_store.as_retriever(search_kwargs={"k": self.dense_k})
        self.bm25_retriever.k = self.bm25_k

    def _split_query_into_windows(
        self, query: str, max_words: int = 150, overlap: int = 30
    ) -> List[str]:
        """Split a long threat report query into overlapping windows to prevent embedding truncation."""
        words = query.split()
        if len(words) <= max_words:
            return [query]
        windows = []
        step = max(1, max_words - overlap)
        for i in range(0, len(words), step):
            win = " ".join(words[i : i + max_words])
            windows.append(win)
            if i + max_words >= len(words):
                break
        return windows

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        enable_query_chunking: Optional[bool] = None,
    ) -> List[Document]:
        """Hybrid retrieval + FlashRank reranking returning top_k documents.
        
        If query chunking is enabled and query exceeds max_words, applies passage chunking
        with MaxSim score pooling across windows to avoid embedding truncation.
        """
        use_chunking = (
            self.enable_query_chunking
            if enable_query_chunking is None
            else enable_query_chunking
        )

        if not use_chunking:
            windows = [query]
        else:
            windows = self._split_query_into_windows(query, max_words=150, overlap=30)

        # 2. FlashRank Cross-Encoder Rerank with MaxSim pooling
        if len(windows) == 1:
            dense_docs = self.dense_retriever.invoke(windows[0])
            bm25_docs = self.bm25_retriever.invoke(windows[0])
            deduped = list({doc.page_content: doc for doc in (dense_docs + bm25_docs)}.values())
            if not deduped:
                return []
            passages = [
                {"id": idx, "text": doc.page_content, "meta": doc.metadata}
                for idx, doc in enumerate(deduped)
            ]
            all_reranked = []
            batch_size = 20
            for i in range(0, len(passages), batch_size):
                batch = passages[i : i + batch_size]
                rerank_req = RerankRequest(query=windows[0], passages=batch)
                all_reranked.extend(self.ranker.rerank(rerank_req))

            all_reranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            final_docs: List[Document] = []
            for r in all_reranked[:top_k]:
                final_docs.append(Document(page_content=r["text"], metadata=r.get("meta", {})))
            return final_docs
        else:
            # Multi-window MaxSim pooling:
            # For each window, retrieve local hybrid candidates and score them against the window.
            # MaxSim score is tracked per unique passage across all windows.
            doc_max_scores: Dict[str, Tuple[float, Document]] = {}
            for win in windows:
                dense_docs = self.dense_retriever.invoke(win)
                bm25_docs = self.bm25_retriever.invoke(win)
                win_candidates = list({doc.page_content: doc for doc in (dense_docs + bm25_docs)}.values())
                if not win_candidates:
                    continue
                passages = [
                    {"id": idx, "text": doc.page_content, "meta": doc.metadata}
                    for idx, doc in enumerate(win_candidates)
                ]
                win_reranked = []
                batch_size = 20
                for i in range(0, len(passages), batch_size):
                    batch = passages[i : i + batch_size]
                    rerank_req = RerankRequest(query=win, passages=batch)
                    win_reranked.extend(self.ranker.rerank(rerank_req))

                for r in win_reranked:
                    p_text = r["text"]
                    score = float(r.get("score", 0.0))
                    if p_text not in doc_max_scores or score > doc_max_scores[p_text][0]:
                        doc_max_scores[p_text] = (score, Document(page_content=p_text, metadata=r.get("meta", {})))

            if not doc_max_scores:
                return []

            # Sort by max score descending across all windows
            sorted_docs = sorted(doc_max_scores.values(), key=lambda x: x[0], reverse=True)
            return [doc for score, doc in sorted_docs[:top_k]]

    def invoke(self, query: str, top_k: int = 10) -> List[Document]:
        """LangChain standard invoke interface."""
        return self.retrieve(query, top_k=top_k)
