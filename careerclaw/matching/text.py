from __future__ import annotations

# Backwards-compatible shim.
# Text processing now lives in careerclaw.core.text_processing so multiple modules
# (matching, resume intelligence, requirements, etc.) share one implementation.

from careerclaw.core.text_processing import tokenize, tokenize_stream, tokens_from_list

__all__ = ["tokenize", "tokenize_stream", "tokens_from_list"]
