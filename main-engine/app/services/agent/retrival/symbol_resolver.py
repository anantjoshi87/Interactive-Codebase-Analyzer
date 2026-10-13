# app/services/agent/retrival/symbol_resolver.py
import re
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process


def clean_raw_input(query: str) -> str:
    """Strips code prefixes, parenthesis, and excess whitespace."""
    # Remove 'class', 'def', 'method', 'function' prefixes
    cleaned = re.sub(
        r"^(class|def|method|function)\s+", "", query.strip(), flags=re.IGNORECASE
    )
    # Remove trailing calls like () or args
    cleaned = re.sub(r"\(.*\)$", "", cleaned)
    return cleaned.strip()


def to_alphanumeric(text: str) -> str:
    """Reduces 'user service', 'user_service', 'UserService' all to 'userservice'."""
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()


class SymbolResolver:
    """
    In-memory fuzzy resolver. Caches all repository symbol names
    and resolves typos in sub-millisecond time.
    """

    def __init__(self, raw_symbols: List[str]):
        # Store canonical symbols (e.g. "UserService", "NotificationRepository")
        self.canonical_symbols: List[str] = raw_symbols

        # Map normalized string -> Canonical symbol name
        # e.g. "userservice" -> "UserService"
        self._normalized_map: Dict[str, str] = {}
        for sym in raw_symbols:
            # Extract the leaf symbol name if it's a qualified path
            leaf = sym.split("::")[-1].split(".")[-1]
            norm_leaf = to_alphanumeric(leaf)
            norm_full = to_alphanumeric(sym)

            if norm_leaf not in self._normalized_map:
                self._normalized_map[norm_leaf] = leaf
            if norm_full not in self._normalized_map:
                self._normalized_map[norm_full] = sym

        # Pre-computed list of keys for fuzzy distance searching
        self._searchable_keys: List[str] = list(self._normalized_map.keys())

    def resolve(
        self, query: str, score_cutoff: float = 75.0
    ) -> Tuple[str, Optional[str]]:
        """
        Takes raw user input and returns:
        (best_search_symbol, original_or_matched_canonical_name)
        """
        cleaned = clean_raw_input(query)
        normalized_query = to_alphanumeric(cleaned)

        if not normalized_query:
            return cleaned, None

        # Level 1: Exact Normalized Match (0ms)
        # Matches 'user service' or 'user_service' directly to 'UserService'
        if normalized_query in self._normalized_map:
            return self._normalized_map[normalized_query], self._normalized_map[normalized_query]

        # Level 2: Fuzzy Match for Typos (e.g. 'userrservic' -> 'userservice')
        match = process.extractOne(
            normalized_query,
            self._searchable_keys,
            scorer=fuzz.WRatio,
            score_cutoff=score_cutoff,
        )

        if match:
            best_key, score, _ = match
            resolved_symbol = self._normalized_map[best_key]
            return resolved_symbol, resolved_symbol

        # Level 3: Fallback to cleaned input if no high-confidence match found
        return cleaned, None