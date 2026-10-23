"""Cyber Threat Entity Resolver for Query-Side Expansion (Optimization 1).

Extracts and indexes threat actor (intrusion-set) and software (malware/tool)
canonical names and aliases directly from MITRE ATT&CK STIX 2.1 corpus.

Supports:
- Variant V0: Baseline (no expansion, returns raw query unmodified)
- Variant V1: Prepend detected entity aliases (budget-capped at 64 tokens)
- Variant V2: Prepend canonical name + MITRE ID only
- Variant V3: Random entity ablation control (prepend random aliases of matched length, seed 42)

Collision Resolution & Normalization:
- Minimum alias length: 3 characters (avoids common English short-word collisions)
- Word boundary regex (\b...\b), case-insensitive matching
- Disambiguation: longest-match-first with preference for canonical names over secondary aliases
- Collision logging for multi-entity alias mappings
- STRICT CONTAMINATION GUARD: Never reads or references benchmark ground-truth datasets.
"""

import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.data_loader import STIXKnowledgeBase, load_stix_all_bundles

logger = logging.getLogger(__name__)


@dataclass
class STIXEntity:
    mitre_id: str
    canonical_name: str
    entity_type: str  # "intrusion-set", "malware", "tool"
    aliases: List[str]
    description: str


@dataclass
class DetectedEntity:
    matched_text: str
    entity: STIXEntity
    start_char: int
    end_char: int
    is_canonical: bool


class CyberEntityResolver:
    """Query-side entity detector and expander grounded strictly in STIX 2.1."""

    def __init__(
        self,
        stix_kb: Optional[STIXKnowledgeBase] = None,
        min_alias_len: int = 3,
        random_seed: int = 42,
    ):
        self.stix_kb = stix_kb or load_stix_all_bundles()
        self.min_alias_len = min_alias_len
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)

        self.entities_by_id: Dict[str, STIXEntity] = {}
        self.alias_to_entities: Dict[str, List[Tuple[STIXEntity, bool]]] = {}
        self.alias_patterns: List[Tuple[re.Pattern, str, STIXEntity, bool]] = []
        self.collision_log: Dict[str, List[str]] = {}

        self._build_entity_index()

    def _build_entity_index(self) -> None:
        """Index all intrusion sets, malware, and tools from STIX KB."""
        valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]

        # 1. Intrusion Sets
        for obj in self.stix_kb.intrusion_sets:
            name = obj.get("name")
            ext_refs = obj.get("external_references", [])
            mitre_id = next(
                (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
                None,
            )
            if not mitre_id or not name:
                continue

            raw_aliases = set(obj.get("aliases", []))
            if obj.get("x_mitre_aliases"):
                raw_aliases.update(obj.get("x_mitre_aliases", []))
            raw_aliases.add(name)

            clean_aliases = [
                a.strip() for a in raw_aliases if len(a.strip()) >= self.min_alias_len
            ]

            entity = STIXEntity(
                mitre_id=mitre_id,
                canonical_name=name.strip(),
                entity_type="intrusion-set",
                aliases=sorted(clean_aliases),
                description=obj.get("description", ""),
            )
            self.entities_by_id[mitre_id] = entity

        # 2. Malware & Tools
        for obj in self.stix_kb.malware + self.stix_kb.tools:
            name = obj.get("name")
            ext_refs = obj.get("external_references", [])
            mitre_id = next(
                (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
                None,
            )
            if not mitre_id or not name:
                continue

            obj_type = obj.get("type", "software")
            raw_aliases = set(obj.get("x_mitre_aliases", []))
            if obj.get("aliases"):
                raw_aliases.update(obj.get("aliases", []))
            raw_aliases.add(name)

            clean_aliases = [
                a.strip() for a in raw_aliases if len(a.strip()) >= self.min_alias_len
            ]

            entity = STIXEntity(
                mitre_id=mitre_id,
                canonical_name=name.strip(),
                entity_type=obj_type,
                aliases=sorted(clean_aliases),
                description=obj.get("description", ""),
            )
            self.entities_by_id[mitre_id] = entity

        # 3. Build alias dictionary and detect collisions
        for entity in self.entities_by_id.values():
            for alias in entity.aliases:
                norm = alias.lower()
                is_canonical = (norm == entity.canonical_name.lower())
                if norm not in self.alias_to_entities:
                    self.alias_to_entities[norm] = []
                self.alias_to_entities[norm].append((entity, is_canonical))

        # Log collisions
        for norm_alias, ent_list in self.alias_to_entities.items():
            if len(ent_list) > 1:
                self.collision_log[norm_alias] = [
                    f"{e.canonical_name} ({e.mitre_id}, {e.entity_type})"
                    for e, _ in ent_list
                ]

        # 4. Precompile regex patterns sorted by alias length descending (longest match first)
        # For collisions, pick canonical match first, then first registered
        sorted_aliases = sorted(
            self.alias_to_entities.keys(),
            key=lambda x: (len(x), any(is_c for _, is_c in self.alias_to_entities[x])),
            reverse=True,
        )

        for alias_norm in sorted_aliases:
            candidates = self.alias_to_entities[alias_norm]
            # Prioritize canonical entity
            canonical_cand = next((e for e, is_c in candidates if is_c), None)
            selected_entity, is_canon = (
                (canonical_cand, True) if canonical_cand else candidates[0]
            )

            # Word boundary regex, case-insensitive
            # Escape regex special characters in alias
            pattern_str = r"\b" + re.escape(alias_norm) + r"\b"
            pattern = re.compile(pattern_str, re.IGNORECASE)
            self.alias_patterns.append((pattern, alias_norm, selected_entity, is_canon))

    def detect_entities(self, text: str) -> List[DetectedEntity]:
        """Detect non-overlapping entity mentions in text using longest-match first."""
        detected: List[DetectedEntity] = []
        occupied_spans: List[Tuple[int, int]] = []

        for pattern, alias_str, entity, is_canon in self.alias_patterns:
            for match in pattern.finditer(text):
                start, end = match.span()
                # Check overlap with already accepted spans
                overlaps = any(
                    not (end <= occ_start or start >= occ_end)
                    for occ_start, occ_end in occupied_spans
                )
                if not overlaps:
                    occupied_spans.append((start, end))
                    detected.append(
                        DetectedEntity(
                            matched_text=match.group(),
                            entity=entity,
                            start_char=start,
                            end_char=end,
                            is_canonical=is_canon,
                        )
                    )

        # Sort by occurrence order in text
        detected.sort(key=lambda x: x.start_char)
        return detected

    def expand_query(
        self,
        query: str,
        variant: str = "V1",
        max_expansion_tokens: int = 64,
    ) -> Tuple[str, List[DetectedEntity]]:
        """Expand query with entity resolution variants.
        
        Variants:
        - V0: Baseline (no expansion)
        - V1: Prepend detected entity aliases (budget-capped)
        - V2: Prepend canonical name + MITRE ID only
        - V3: Random entity ablation control (length-matched)
        """
        if variant == "V0":
            return query, []

        detected = self.detect_entities(query)
        if not detected and variant != "V3":
            return query, []

        # Unique entities by MITRE ID
        unique_entities: Dict[str, STIXEntity] = {}
        for d in detected:
            if d.entity.mitre_id not in unique_entities:
                unique_entities[d.entity.mitre_id] = d.entity

        if variant == "V1":
            expansion_parts = []
            current_tokens = 0
            for ent in unique_entities.values():
                # Form: [Entity: CanonicalName (ID), Known Aliases: A1, A2, ...]
                aliases_to_add = [a for a in ent.aliases if a != ent.canonical_name][:6]
                if aliases_to_add:
                    ent_str = f"[{ent.canonical_name} ({ent.mitre_id}) aliases: {', '.join(aliases_to_add)}]"
                else:
                    ent_str = f"[{ent.canonical_name} ({ent.mitre_id})]"

                ent_tokens = len(ent_str.split())
                if current_tokens + ent_tokens <= max_expansion_tokens:
                    expansion_parts.append(ent_str)
                    current_tokens += ent_tokens
                else:
                    break

            if expansion_parts:
                prefix = " ".join(expansion_parts) + " "
                return prefix + query, detected
            return query, detected

        elif variant == "V2":
            # Canonical name + MITRE ID only
            expansion_parts = [
                f"[{ent.canonical_name} ({ent.mitre_id})]"
                for ent in unique_entities.values()
            ]
            prefix = " ".join(expansion_parts) + " "
            return prefix + query, detected

        elif variant == "V3":
            # Random entity control with matched token length
            # Determine target token count from what V1 would produce
            target_tokens = 0
            if unique_entities:
                v1_str, _ = self.expand_query(query, variant="V1", max_expansion_tokens=max_expansion_tokens)
                target_tokens = len(v1_str.split()) - len(query.split())
            if target_tokens == 0:
                target_tokens = 15  # default budget if no entities detected

            all_entities = list(self.entities_by_id.values())
            random_sample = self.rng.sample(all_entities, min(len(all_entities), 5))
            random_parts = []
            curr_tokens = 0
            for ent in random_sample:
                r_str = f"[{ent.canonical_name} ({ent.mitre_id}) aliases: {', '.join(ent.aliases[:4])}]"
                r_tokens = len(r_str.split())
                if curr_tokens + r_tokens <= max_expansion_tokens:
                    random_parts.append(r_str)
                    curr_tokens += r_tokens
                if curr_tokens >= target_tokens:
                    break

            prefix = " ".join(random_parts) + " "
            return prefix + query, detected

        else:
            raise ValueError(f"Unknown entity resolution variant: {variant}")
