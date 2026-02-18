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


# ---------------------------------------------------------------------------
# Phase-5E: recruitment boilerplate stopwords
# ---------------------------------------------------------------------------

def test_recruitment_process_terms_are_filtered() -> None:
    """Recruitment process terms added in Phase-5E must not appear in token stream."""
    text = (
        "Please apply now. Qualified candidates will be interviewed. "
        "We are hiring and onboarding applicants. Submit your application today."
    )
    stream = tokenize_stream(text)
    for term in ("apply", "applying", "applicant", "applicants", "application",
                 "applications", "submit", "submission", "candidate", "candidates",
                 "qualified", "interview", "interviewing", "hire", "hiring",
                 "onboard", "onboarding"):
        assert term not in stream, f"Expected '{term}' to be filtered as stopword, but found it in stream"


def test_recruitment_descriptor_terms_are_filtered() -> None:
    """Generic recruitment descriptor noise must not appear in token stream."""
    text = (
        "Competitive salary package with benefits and opportunities. "
        "We are seeking a responsible and successful candidate. Bonus nice to have."
    )
    stream = tokenize_stream(text)
    for term in ("competitive", "opportunity", "opportunities", "benefit", "benefits",
                 "package", "responsible", "seeking", "looking", "successful"):
        assert term not in stream, f"Expected '{term}' to be filtered as stopword, but found it in stream"


def test_technical_tokens_not_accidentally_filtered() -> None:
    """Stopword expansion must not remove legitimate technical tokens."""
    text = "Python TypeScript React AWS kubernetes terraform postgresql fastapi"
    stream = tokenize_stream(text)
    for term in ("python", "typescript", "react", "aws", "kubernetes", "terraform",
                 "postgresql", "fastapi"):
        assert term in stream, f"Expected technical token '{term}' to survive stopword filtering"
