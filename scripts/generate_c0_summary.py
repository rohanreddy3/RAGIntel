"""Generate C0 inspection summary and determine primary budget B*."""

import json
from pathlib import Path
import pickle
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load child docs
with open(REPO_ROOT / ".cache" / "retriever_index_all" / "child_docs.pkl", "rb") as f:
    child_docs = pickle.load(f)

# Group by type
type_stats = {}
for obj_type in ["attack-pattern", "intrusion-set", "malware", "tool"]:
    matching = [
        d for d in child_docs
        if d.metadata.get("type") == obj_type
        or (obj_type in ["malware", "tool"] and d.metadata.get("type") in ["malware", "tool", "software"])
    ]
    char_lens = [len(d.page_content) for d in matching]
    word_lens = [len(d.page_content.split()) for d in matching]
    type_stats[obj_type] = {
        "chunk_count": len(matching),
        "chars_mean": round(float(np.mean(char_lens)), 1),
        "chars_median": round(float(np.median(char_lens)), 1),
        "tokens_words_mean": round(float(np.mean(word_lens)), 1),
        "tokens_words_median": round(float(np.median(word_lens)), 1),
    }

# Compute 10-chunk context distribution (sampling 500 contiguous and random 10-chunk sets from corpus)
rng = np.random.default_rng(42)
top10_word_lengths = []
for _ in range(500):
    sample_10 = rng.choice(child_docs, size=10, replace=False)
    total_words = sum(len(d.page_content.split()) for d in sample_10)
    top10_word_lengths.append(total_words)

mean_words = round(float(np.mean(top10_word_lengths)), 1)
median_words = round(float(np.median(top10_word_lengths)), 1)
# B* rounded to nearest 50 tokens
# Median words is ~356-360 words. In subword tokens (MiniLM 1.33x ratio) it is ~475 tokens.
# Rounded to nearest 50: in words = 350 words, in subwords = 500 tokens.
# Let B* = 500 tokens (or 350 words). We pre-register B* = 500 tokens.
b_star = 500

c0_summary = {
    "corpus_chunk_distribution_by_type": type_stats,
    "top10_context_distribution": {
        "mean_words": mean_words,
        "median_words": median_words,
        "median_subwords_minilm": round(median_words * 1.33, 1),
        "B_star_tokens": b_star,
    },
    "pre_registered_primary_budget_B_star": b_star,
    "secondary_budgets": [500, 1000, 2000, 4000],
}

out_path = REPO_ROOT / "results" / "phase_2" / "c0_inspection_summary.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(c0_summary, f, indent=2)

print(f"C0 summary generated successfully at {out_path}")
print(f"Pre-registered Primary Budget B* = {b_star} tokens")
