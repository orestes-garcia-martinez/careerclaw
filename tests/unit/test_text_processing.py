from __future__ import annotations

from careerclaw.core.text_processing import normalize_text, tokenize_stream, tokenize, extract_phrases


def test_normalize_text_is_deterministic_and_removes_nbsp() -> None:
    raw = "Customer\u00a0Service  —  Lead\n\tTraining"
    norm = normalize_text(raw)
    assert "  " not in norm
    assert "\u00a0" not in norm
    assert "Customer Service" in norm


def test_tokenize_stream_is_ordered_and_filters_stopwords() -> None:
    text = "Experienced in customer service and project management with strong communication."
    stream = tokenize_stream(text)
    # order preserved for phrases
    assert stream[:3] == ["experienced", "customer", "service"]
    # stopwords filtered
    assert "and" not in stream
    assert "with" not in stream


def test_tokenize_set_matches_stream_contents() -> None:
    text = "Customer service customer support."
    s = tokenize(text)
    stream = tokenize_stream(text)
    assert set(stream) == s
    assert "customer" in s
    assert "service" in s


def test_extract_phrases_bigrams_and_trigrams_are_stable() -> None:
    text = "Customer service operations and project management leadership."
    stream = tokenize_stream(text)
    phrases = extract_phrases(stream, ngrams=(2, 3), max_phrases=10)

    # bigrams
    assert "customer service" in phrases
    assert "service operations" in phrases
    assert "project management" in phrases

    # trigram (if present)
    assert "customer service operations" in phrases

    # deterministic ordering: first-seen bigram appears before later ones
    assert phrases.index("customer service") < phrases.index("project management")
