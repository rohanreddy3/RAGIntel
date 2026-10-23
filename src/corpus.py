"""MITRE ATT&CK STIX Document Corpus Builder and Baseline Splitter.

Builds Document objects from active STIX objects and applies RAGIntel's
original parent-child chunking (2000/200 parent, 500/50 child).
"""

from typing import Any, Dict, List, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.data_loader import STIXKnowledgeBase, load_stix_bundle


def build_stix_raw_documents(kb: STIXKnowledgeBase) -> List[Document]:
    """Convert active STIX objects into LangChain Document objects."""
    documents: List[Document] = []

    valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]

    # 1. Attack Patterns (Techniques & Sub-techniques)
    for obj in kb.attack_patterns:
        ext_refs = obj.get("external_references", [])
        mitre_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            None,
        )
        name = obj.get("name", "Unknown Technique")
        desc = obj.get("description", "")
        tactics = [
            p.get("phase_name")
            for p in obj.get("kill_chain_phases", [])
            if p.get("kill_chain_name") in valid_sources
        ]
        is_sub = obj.get("x_mitre_is_subtechnique", False)

        tactics_str = ", ".join(tactics) if tactics else "None"
        content = (
            f"Technique ID: {mitre_id or 'N/A'}\n"
            f"Technique Name: {name}\n"
            f"Tactics: {tactics_str}\n"
            f"Is Subtechnique: {is_sub}\n\n"
            f"Description:\n{desc}"
        )

        doc = Document(
            page_content=content,
            metadata={
                "stix_id": obj.get("id"),
                "mitre_id": mitre_id or "",
                "name": name,
                "type": "attack-pattern",
                "tactics": tactics,
                "is_subtechnique": is_sub,
            },
        )
        documents.append(doc)

    # 2. Intrusion Sets (Threat Groups & Actors)
    for obj in kb.intrusion_sets:
        ext_refs = obj.get("external_references", [])
        mitre_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            None,
        )
        name = obj.get("name", "Unknown Group")
        aliases = list(obj.get("aliases", []))
        if name not in aliases:
            aliases.insert(0, name)
        desc = obj.get("description", "")

        aliases_str = ", ".join(aliases)
        content = (
            f"Threat Group ID: {mitre_id or 'N/A'}\n"
            f"Canonical Name: {name}\n"
            f"Known Aliases: {aliases_str}\n\n"
            f"Description:\n{desc}"
        )

        doc = Document(
            page_content=content,
            metadata={
                "stix_id": obj.get("id"),
                "mitre_id": mitre_id or "",
                "name": name,
                "aliases": aliases,
                "type": "intrusion-set",
            },
        )
        documents.append(doc)

    # 3. Malware & Tools
    for obj in kb.malware + kb.tools:
        ext_refs = obj.get("external_references", [])
        mitre_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
            None,
        )
        name = obj.get("name", "Unknown Software")
        desc = obj.get("description", "")
        obj_type = obj.get("type", "software")

        content = (
            f"Software ID: {mitre_id or 'N/A'}\n"
            f"Software Name: {name}\n"
            f"Type: {obj_type}\n\n"
            f"Description:\n{desc}"
        )

        doc = Document(
            page_content=content,
            metadata={
                "stix_id": obj.get("id"),
                "mitre_id": mitre_id or "",
                "name": name,
                "type": obj_type,
            },
        )
        documents.append(doc)

    return documents


def split_documents_baseline(documents: List[Document]) -> Tuple[List[Document], List[Document]]:
    """RAGIntel's original parent-child document splitting.
    
    Parent splitter: RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    Child splitter:  RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    """
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    parent_docs = parent_splitter.split_documents(documents)
    child_docs = []

    for parent in parent_docs:
        _child_docs = child_splitter.split_documents([parent])
        parent_id = str(hash(parent.page_content))
        for child in _child_docs:
            child.metadata["parent_id"] = parent_id
        child_docs.extend(_child_docs)

    return parent_docs, child_docs


def split_documents_control_e0_prime(documents: List[Document]) -> List[Document]:
    """Control arm E0': STIX-derived text with RAGIntel's ORIGINAL single-level splitter (2000/500 char).
    E1 (structure-aware) will be compared against E0' later.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
    return splitter.split_documents(documents)
