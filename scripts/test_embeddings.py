import time
from sentence_transformers import SentenceTransformer

print("Loading local embedding model: nomic-ai/nomic-embed-text-v1.5 ...")
start = time.time()
try:
    model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
    elapsed = time.time() - start
    print(f"Loaded nomic-ai/nomic-embed-text-v1.5 in {elapsed:.2f}s")
    test_emb = model.encode(["search_query: APT28 cyber attack on critical infrastructure"])
    print(f"Embedding shape: {test_emb.shape}")
except Exception as e:
    print(f"Error loading nomic: {e}")
    print("Falling back to sentence-transformers/all-MiniLM-L6-v2 ...")
    start = time.time()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    elapsed = time.time() - start
    print(f"Loaded all-MiniLM-L6-v2 in {elapsed:.2f}s")
    test_emb = model.encode(["APT28 cyber attack on critical infrastructure"])
    print(f"Embedding shape: {test_emb.shape}")
