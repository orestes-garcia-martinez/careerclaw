from careerclaw.matching.scoring import (
    experience_alignment_score,
    salary_alignment_score,
    clamp01,
)

def test_experience_alignment_clamped_linear():
    assert experience_alignment_score(6, 3) == 1.0
    assert experience_alignment_score(3, 6) == 0.5
    assert experience_alignment_score(0, 5) == 0.0
    assert experience_alignment_score(5, 0) == 1.0  # no requirement => match

def test_salary_alignment_neutral_when_missing():
    assert salary_alignment_score(120000, None, None) == 0.5
    assert salary_alignment_score(None, 100000, 150000) == 0.5

def test_salary_alignment_perfect_match():
    assert salary_alignment_score(120000, 120000, 160000) == 1.0
    assert salary_alignment_score(120000, 130000, 160000) == 1.0

def test_salary_alignment_partial_match():
    assert salary_alignment_score(120000, 100000, 140000) == 0.8

def test_salary_alignment_hard_mismatch_decays():
    # job max below user min => should be < 0.5
    s = salary_alignment_score(120000, 80000, 100000)
    assert 0.0 <= s < 0.5

def test_clamp01():
    assert clamp01(-1) == 0.0
    assert clamp01(2) == 1.0
    assert clamp01(0.25) == 0.25
