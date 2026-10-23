"""Optimization 2: Structure-Aware Chunking for MITRE ATT&CK STIX Corpus.

Implements:
- E0': Baseline RAGIntel splitter control with budget enforcement.
- E1a: Field-based chunking (identity_description, procedure_examples, mitigations, detection).
- E1b: Sibling expansion by parent technique_id under matched token budget B.
- E1c: Random sibling expansion control under matched token budget B (seed 42).
- Strict token budget accounting (B in {B*, 500, 1000, 2000, 4000}) with final chunk truncation.
"""

import copy
import random
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.data_loader import STIXKnowledgeBase, load_stix_all_bundles


def count_tokens(text: str) -> int:
    """Whitespace word tokenization standard across thesis budgeting."""
    return len(text.split())


def extract_parent_technique_id(mitre_id: str) -> str:
    """Extract root parent technique ID (e.g. 'T1059.001' -> 'T1059', 'T1059' -> 'T1059')."""
    if not mitre_id:
        return ""
    return mitre_id.split(".")[0].strip()


def truncate_to_token_budget(
    docs: List[Document],
    budget_tokens: int,
    tokenizer_fn: Optional[Callable[[str], int]] = None,
) -> List[Document]:
    """Strictly enforce token budget B across a sequence of Document objects.
    
    If adding a document causes the total token count to exceed budget_tokens,
    the document's text is truncated to fit the exact remaining budget and no further
    documents are included.
    """
    tok_fn = tokenizer_fn or count_tokens
    if budget_tokens <= 0:
        return []

    truncated_docs: List[Document] = []
    current_tokens = 0

    for doc in docs:
        doc_tokens = tok_fn(doc.page_content)
        if doc_tokens == 0:
            continue

        if current_tokens + doc_tokens <= budget_tokens:
            truncated_docs.append(copy.deepcopy(doc))
            current_tokens += doc_tokens
        else:
            remaining = budget_tokens - current_tokens
            if remaining > 0:
                words = doc.page_content.split()
                truncated_text = " ".join(words[:remaining])
                new_doc = Document(
                    page_content=truncated_text,
                    metadata=copy.deepcopy(doc.metadata),
                )
                new_doc.metadata["truncated"] = True
                new_doc.metadata["original_tokens"] = doc_tokens
                new_doc.metadata["budget_tokens_kept"] = remaining
                truncated_docs.append(new_doc)
                current_tokens += remaining
            break

    return truncated_docs


def build_field_chunks_e1a(kb: STIXKnowledgeBase) -> List[Document]:
    """Build E1a field-based chunks for all active STIX objects.
    
    For attack-pattern (Techniques and Sub-techniques):
      1. identity_description: Technique ID, Name, Tactics, Platforms, Is Subtechnique, Description.
      2. procedure_examples: Known adversary/software procedures using this technique.
      3. mitigations: Security controls and mitigation strategies.
      4. detection: Detection data components, sensors, and detection strategies.
      
    For intrusion-set, malware, and tool:
      1. identity_description: Name, Canonical ID, Aliases, Description.
      2. procedure_examples: Associated procedures/techniques.
      
    All documents include structured metadata:
      - field: str in {'identity_description', 'procedure_examples', 'mitigations', 'detection'}
      - technique_id: root parent technique ID for techniques (e.g. 'T1059'), or canonical ID
      - mitre_id: full MITRE ID (e.g. 'T1059.001', 'G0032')
      - stix_id: STIX UUID
      - name: canonical name
      - type: STIX object type
    """
    valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]

    # 1. Index relationships by target_ref and source_ref for fast extraction
    target_rels: Dict[str, List[Dict[str, Any]]] = {}
    source_rels: Dict[str, List[Dict[str, Any]]] = {}
    for r in kb.relationships:
        t_ref = r.get("target_ref")
        s_ref = r.get("source_ref")
        if t_ref:
            target_rels.setdefault(t_ref, []).append(r)
        if s_ref:
            source_rels.setdefault(s_ref, []).append(r)

    # Map stix_id to object name for resolving relationship partners
    id_to_name: Dict[str, Tuple[str, str]] = {}  # stix_id -> (name, mitre_id)
    for obj in kb.attack_patterns + kb.intrusion_sets + kb.malware + kb.tools:
        stix_id = obj.get("id")
        name = obj.get("name", "Unknown")
        ext_refs = obj.get("external_references", [])
        m_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            "",
        )
        if stix_id:
            id_to_name[stix_id] = (name, m_id)

    field_documents: List[Document] = []

    # 2. Process Attack Patterns
    for obj in kb.attack_patterns:
        stix_id = obj.get("id", "")
        ext_refs = obj.get("external_references", [])
        mitre_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            "",
        )
        name = obj.get("name", "Unknown Technique")
        desc = obj.get("description", "").strip()
        tactics = [
            p.get("phase_name")
            for p in obj.get("kill_chain_phases", [])
            if p.get("kill_chain_name") in valid_sources
        ]
        is_sub = obj.get("x_mitre_is_subtechnique", False)
        technique_id = extract_parent_technique_id(mitre_id)

        # Base metadata common to all fields for this technique
        base_meta = {
            "stix_id": stix_id,
            "mitre_id": mitre_id,
            "technique_id": technique_id,
            "name": name,
            "type": "attack-pattern",
            "tactics": tactics,
            "is_subtechnique": is_sub,
        }

        # Field 1: identity_description
        tactics_str = ", ".join(tactics) if tactics else "None"
        platforms = ", ".join(obj.get("x_mitre_platforms", [])) or "None"
        ident_content = (
            f"Technique ID: {mitre_id or 'N/A'}\n"
            f"Parent Technique ID: {technique_id or 'N/A'}\n"
            f"Technique Name: {name}\n"
            f"Tactics: {tactics_str}\n"
            f"Platforms: {platforms}\n"
            f"Is Subtechnique: {is_sub}\n\n"
            f"Description:\n{desc}"
        )
        meta_ident = dict(base_meta, field="identity_description")
        field_documents.append(Document(page_content=ident_content, metadata=meta_ident))

        # Related relationships for this technique
        rels_targeting = target_rels.get(stix_id, [])

        # Field 2: procedure_examples (from 'uses' relationships where target is this technique)
        proc_rels = [r for r in rels_targeting if r.get("relationship_type") == "uses"]
        proc_lines = []
        for r in proc_rels:
            s_id = r.get("source_ref", "")
            actor_name, actor_m_id = id_to_name.get(s_id, ("Unknown Entity", ""))
            r_desc = r.get("description", "").strip()
            if r_desc:
                label = f"{actor_name} ({actor_m_id})" if actor_m_id else actor_name
                proc_lines.append(f"- {label}: {r_desc}")

        proc_body = "\n".join(proc_lines[:15]) if proc_lines else "No specific procedure examples documented."
        proc_content = (
            f"Technique: {name} ({mitre_id})\n"
            f"Field: Procedure Examples\n\n"
            f"{proc_body}"
        )
        meta_proc = dict(base_meta, field="procedure_examples")
        field_documents.append(Document(page_content=proc_content, metadata=meta_proc))

        # Field 3: mitigations (from 'mitigates' relationships targeting this technique)
        mit_rels = [r for r in rels_targeting if r.get("relationship_type") == "mitigates"]
        mit_lines = []
        for r in mit_rels:
            s_id = r.get("source_ref", "")
            mit_name, mit_m_id = id_to_name.get(s_id, ("Mitigation", ""))
            r_desc = r.get("description", "").strip()
            label = f"{mit_name} ({mit_m_id})" if mit_m_id else mit_name
            if r_desc:
                mit_lines.append(f"- {label}: {r_desc}")
            else:
                mit_lines.append(f"- {label}")

        mit_body = "\n".join(mit_lines[:10]) if mit_lines else "No specific mitigation controls documented."
        mit_content = (
            f"Technique: {name} ({mitre_id})\n"
            f"Field: Mitigations\n\n"
            f"{mit_body}"
        )
        meta_mit = dict(base_meta, field="mitigations")
        field_documents.append(Document(page_content=mit_content, metadata=meta_mit))

        # Field 4: detection (from detection descriptions and 'detects' relationships)
        det_rels = [r for r in rels_targeting if r.get("relationship_type") == "detects"]
        det_lines = []
        for r in det_rels:
            s_id = r.get("source_ref", "")
            det_name, det_m_id = id_to_name.get(s_id, ("Data Component", ""))
            r_desc = r.get("description", "").strip()
            label = f"{det_name} ({det_m_id})" if det_m_id else det_name
            if r_desc:
                det_lines.append(f"- {label}: {r_desc}")
            else:
                det_lines.append(f"- {label}")

        det_notes = obj.get("x_mitre_detection", "").strip()
        det_section = f"Detection Guidance:\n{det_notes}\n\n" if det_notes else ""
        det_body = "\n".join(det_lines[:10]) if det_lines else "No specific data component sensors documented."
        det_content = (
            f"Technique: {name} ({mitre_id})\n"
            f"Field: Detection\n\n"
            f"{det_section}Detection Components:\n{det_body}"
        )
        meta_det = dict(base_meta, field="detection")
        field_documents.append(Document(page_content=det_content, metadata=meta_det))

    # 3. Process Intrusion Sets (Threat Groups)
    for obj in kb.intrusion_sets:
        stix_id = obj.get("id", "")
        ext_refs = obj.get("external_references", [])
        mitre_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            "",
        )
        name = obj.get("name", "Unknown Group")
        desc = obj.get("description", "").strip()
        aliases = list(obj.get("aliases", []))
        if name not in aliases:
            aliases.insert(0, name)

        base_meta = {
            "stix_id": stix_id,
            "mitre_id": mitre_id,
            "technique_id": mitre_id,
            "name": name,
            "aliases": aliases,
            "type": "intrusion-set",
        }

        # Field 1: identity_description
        ident_content = (
            f"Threat Group ID: {mitre_id or 'N/A'}\n"
            f"Canonical Name: {name}\n"
            f"Known Aliases: {', '.join(aliases)}\n\n"
            f"Description:\n{desc}"
        )
        meta_ident = dict(base_meta, field="identity_description")
        field_documents.append(Document(page_content=ident_content, metadata=meta_ident))

        # Field 2: procedure_examples (techniques used by this threat actor)
        s_rels = source_rels.get(stix_id, [])
        tech_rels = [r for r in s_rels if r.get("relationship_type") == "uses"]
        tech_lines = []
        for r in tech_rels:
            t_id = r.get("target_ref", "")
            t_name, t_m_id = id_to_name.get(t_id, ("", ""))
            r_desc = r.get("description", "").strip()
            if t_m_id.startswith("T"):
                if r_desc:
                    tech_lines.append(f"- {t_name} ({t_m_id}): {r_desc}")
                else:
                    tech_lines.append(f"- {t_name} ({t_m_id})")

        tech_body = "\n".join(tech_lines[:15]) if tech_lines else "No specific techniques documented."
        tech_content = (
            f"Threat Group: {name} ({mitre_id})\n"
            f"Field: Procedure Examples (Techniques Used)\n\n"
            f"{tech_body}"
        )
        meta_proc = dict(base_meta, field="procedure_examples")
        field_documents.append(Document(page_content=tech_content, metadata=meta_proc))

    # 4. Process Malware & Tools
    for obj in kb.malware + kb.tools:
        stix_id = obj.get("id", "")
        ext_refs = obj.get("external_references", [])
        mitre_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            "",
        )
        name = obj.get("name", "Unknown Software")
        desc = obj.get("description", "").strip()
        obj_type = obj.get("type", "software")

        base_meta = {
            "stix_id": stix_id,
            "mitre_id": mitre_id,
            "technique_id": mitre_id,
            "name": name,
            "type": obj_type,
        }

        # Field 1: identity_description
        ident_content = (
            f"Software ID: {mitre_id or 'N/A'}\n"
            f"Software Name: {name}\n"
            f"Type: {obj_type}\n\n"
            f"Description:\n{desc}"
        )
        meta_ident = dict(base_meta, field="identity_description")
        field_documents.append(Document(page_content=ident_content, metadata=meta_ident))

        # Field 2: procedure_examples
        s_rels = source_rels.get(stix_id, [])
        tech_rels = [r for r in s_rels if r.get("relationship_type") == "uses"]
        tech_lines = []
        for r in tech_rels:
            t_id = r.get("target_ref", "")
            t_name, t_m_id = id_to_name.get(t_id, ("", ""))
            r_desc = r.get("description", "").strip()
            if t_m_id.startswith("T"):
                if r_desc:
                    tech_lines.append(f"- {t_name} ({t_m_id}): {r_desc}")
                else:
                    tech_lines.append(f"- {t_name} ({t_m_id})")

        tech_body = "\n".join(tech_lines[:15]) if tech_lines else "No specific techniques documented."
        tech_content = (
            f"Software: {name} ({mitre_id})\n"
            f"Field: Procedure Examples (Techniques Used)\n\n"
            f"{tech_body}"
        )
        meta_proc = dict(base_meta, field="procedure_examples")
        field_documents.append(Document(page_content=tech_content, metadata=meta_proc))

    return field_documents


class StructureAwareIndex:
    """Index of field chunks providing sibling lookup and budget-aware expansion."""

    def __init__(self, field_chunks: List[Document]):
        self.field_chunks = field_chunks
        self.by_technique_id: Dict[str, List[Document]] = {}
        self.by_mitre_id: Dict[str, List[Document]] = {}

        for doc in field_chunks:
            tech_id = doc.metadata.get("technique_id", "")
            mitre_id = doc.metadata.get("mitre_id", "")
            if tech_id:
                self.by_technique_id.setdefault(tech_id, []).append(doc)
            if mitre_id:
                self.by_mitre_id.setdefault(mitre_id, []).append(doc)

        self.all_technique_ids = sorted(list(self.by_technique_id.keys()))

    def get_siblings(self, seed_doc: Document) -> List[Document]:
        """Return sibling chunks sharing the same parent technique_id."""
        tech_id = seed_doc.metadata.get("technique_id", "")
        if not tech_id:
            m_id = seed_doc.metadata.get("mitre_id", "")
            tech_id = extract_parent_technique_id(m_id)
        if not tech_id or tech_id not in self.by_technique_id:
            return []
        seed_content = seed_doc.page_content
        return [d for d in self.by_technique_id[tech_id] if d.page_content != seed_content]

    def expand_siblings_e1b(
        self,
        seed_docs: List[Document],
        budget_tokens: int,
        tokenizer_fn: Optional[Callable[[str], int]] = None,
    ) -> List[Document]:
        """E1b: Expand retrieved seed documents with sibling chunks under budget B.
        
        Specification C2: Siblings are inserted IMMEDIATELY AFTER their parent hit,
        then the sequence is truncated at token budget B.
        """
        expanded: List[Document] = []
        seen_contents: Set[str] = set()
        field_order = {
            "identity_description": 0,
            "procedure_examples": 1,
            "mitigations": 2,
            "detection": 3,
        }

        for seed in seed_docs:
            if seed.page_content not in seen_contents:
                expanded.append(seed)
                seen_contents.add(seed.page_content)

            siblings = self.get_siblings(seed)
            sorted_sibs = sorted(
                siblings,
                key=lambda d: (
                    field_order.get(d.metadata.get("field", ""), 9),
                    d.metadata.get("mitre_id", ""),
                ),
            )
            for sib in sorted_sibs:
                if sib.page_content not in seen_contents:
                    expanded.append(sib)
                    seen_contents.add(sib.page_content)

        return truncate_to_token_budget(expanded, budget_tokens, tokenizer_fn=tokenizer_fn)

    def expand_random_siblings_e1c(
        self,
        seed_docs: List[Document],
        budget_tokens: int,
        random_seed: int = 42,
        target_sibling_count: Optional[int] = None,
        tokenizer_fn: Optional[Callable[[str], int]] = None,
    ) -> List[Document]:
        """E1c: Control arm expanding with random chunks from unrelated technique_ids under budget B.
        
        Inserts the same number of random siblings as E1b, using deterministic per-query seed.
        """
        if target_sibling_count is None:
            e1b_docs = self.expand_siblings_e1b(seed_docs, budget_tokens, tokenizer_fn=tokenizer_fn)
            seed_contents = {d.page_content for d in seed_docs}
            target_sibling_count = sum(1 for d in e1b_docs if d.page_content not in seed_contents)

        expanded: List[Document] = []
        seen_contents: Set[str] = set()
        seed_tech_ids = {
            d.metadata.get("technique_id") or extract_parent_technique_id(d.metadata.get("mitre_id", ""))
            for d in seed_docs
        }
        seed_tech_ids = {t for t in seed_tech_ids if t}

        unrelated_chunks = [
            d for d in self.field_chunks
            if d.metadata.get("technique_id") not in seed_tech_ids
        ]

        rng = random.Random(random_seed)
        shuffled = list(unrelated_chunks)
        rng.shuffle(shuffled)
        random_pool_idx = 0

        sibs_inserted = 0
        for seed in seed_docs:
            if seed.page_content not in seen_contents:
                expanded.append(seed)
                seen_contents.add(seed.page_content)

            while sibs_inserted < target_sibling_count and random_pool_idx < len(shuffled):
                cand = shuffled[random_pool_idx]
                random_pool_idx += 1
                if cand.page_content not in seen_contents:
                    expanded.append(cand)
                    seen_contents.add(cand.page_content)
                    sibs_inserted += 1
                    break

        while sibs_inserted < target_sibling_count and random_pool_idx < len(shuffled):
            cand = shuffled[random_pool_idx]
            random_pool_idx += 1
            if cand.page_content not in seen_contents:
                expanded.append(cand)
                seen_contents.add(cand.page_content)
                sibs_inserted += 1

        return truncate_to_token_budget(expanded, budget_tokens, tokenizer_fn=tokenizer_fn)


class StructureAwareSTIXRetriever:
    """Retriever wrapper for structure-aware chunking arms (E0', E1a, E1b, E1c) under budget B."""

    def __init__(
        self,
        stix_kb: Optional[STIXKnowledgeBase] = None,
        budget_tokens: int = 500,
        baseline_cache_dir: str = ".cache/retriever_index_all",
        field_cache_dir: str = ".cache/retriever_index_field_chunks",
    ):
        from src.retriever import HybridSTIXRetriever
        self.stix_kb = stix_kb or load_stix_all_bundles()
        self.budget_tokens = budget_tokens
        self.retriever_baseline = HybridSTIXRetriever(stix_kb=self.stix_kb, cache_dir=baseline_cache_dir)
        field_chunks = build_field_chunks_e1a(self.stix_kb)
        self.sa_index = StructureAwareIndex(field_chunks)
        self.retriever_field = HybridSTIXRetriever(
            stix_kb=self.stix_kb,
            cache_dir=field_cache_dir,
            custom_documents=field_chunks,
        )

    def retrieve(
        self,
        query: str,
        arm: str = "E1b",
        budget_tokens: Optional[int] = None,
        top_k: int = 15,
        enable_query_chunking: bool = False,
        random_seed: int = 42,
    ) -> List[Document]:
        budget = budget_tokens if budget_tokens is not None else self.budget_tokens

        if arm == "E0_prime":
            raw_retrieved = self.retriever_baseline.retrieve(
                query, top_k=top_k, enable_query_chunking=enable_query_chunking
            )
            return truncate_to_token_budget(raw_retrieved, budget_tokens=budget)
        elif arm == "E1a":
            raw_field = self.retriever_field.retrieve(
                query, top_k=top_k, enable_query_chunking=enable_query_chunking
            )
            return truncate_to_token_budget(raw_field, budget_tokens=budget)
        elif arm == "E1b":
            raw_field = self.retriever_field.retrieve(
                query, top_k=top_k, enable_query_chunking=enable_query_chunking
            )
            return self.sa_index.expand_siblings_e1b(raw_field, budget_tokens=budget)
        elif arm == "E1c":
            raw_field = self.retriever_field.retrieve(
                query, top_k=top_k, enable_query_chunking=enable_query_chunking
            )
            return self.sa_index.expand_random_siblings_e1c(
                raw_field, budget_tokens=budget, random_seed=random_seed
            )
        else:
            raw_field = self.retriever_field.retrieve(
                query, top_k=top_k, enable_query_chunking=enable_query_chunking
            )
            return truncate_to_token_budget(raw_field, budget_tokens=budget)

