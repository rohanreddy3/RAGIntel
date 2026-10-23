import time
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from flashrank import Ranker, RerankRequest

# 1. Test docs
docs = [
    Document(page_content="Technique T1071: Application Layer Protocol. Adversaries may communicate using application layer protocols.", metadata={"mitre_id": "T1071"}),
    Document(page_content="Technique T1573: Encrypted Channel. Adversaries may employ a known encryption algorithm to conceal command and control traffic.", metadata={"mitre_id": "T1573"}),
    Document(page_content="Threat Group G0007: APT28. Russia-based threat group active since at least 2004.", metadata={"mitre_id": "G0007", "name": "APT28"}),
    Document(page_content="Technique T1059: Command and Scripting Interpreter. Adversaries may abuse command and script interpreters.", metadata={"mitre_id": "T1059"}),
]

print("Initializing embeddings: all-MiniLM-L6-v2 ...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

print("Building FAISS index...")
vs = FAISS.from_documents(docs, embeddings)
dense = vs.as_retriever(search_kwargs={"k": 3})

print("Building BM25 index...")
bm25 = BM25Retriever.from_documents(docs)
bm25.k = 3

print("Initializing FlashRank Ranker (ms-marco-MiniLM-L-12-v2)...")
ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")

def hybrid_retriever(query: str, top_k: int = 3):
    dense_docs = dense.invoke(query)
    bm25_docs = bm25.invoke(query)
    combined = dense_docs + bm25_docs
    deduped = list({doc.page_content: doc for doc in combined}.values())

    passages = [
        {"id": idx, "text": doc.page_content, "meta": doc.metadata}
        for idx, doc in enumerate(deduped)
    ]
    rerank_req = RerankRequest(query=query, passages=passages)
    reranked = ranker.rerank(rerank_req)

    # Return top_k Document objects
    final_docs = []
    for r in reranked[:top_k]:
        final_docs.append(Document(page_content=r["text"], metadata=r.get("meta", {})))
    return final_docs

print("\nQuery: 'Russian cyber threat group APT28'")
results = hybrid_retriever("Russian cyber threat group APT28", top_k=2)
print(f"Retrieved {len(results)} reranked docs:")
for i, doc in enumerate(results):
    print(f"  [{i+1}] {doc.page_content[:80]} | meta={doc.metadata}")
