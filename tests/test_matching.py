"""Keyword/skill matching — normalization, aliases, fuzzy matching."""
from backend.utils.matching import fuzzy_match_keywords, normalize_skill


class TestNormalizeSkill:
    def test_lowercases_and_strips(self):
        assert normalize_skill('  Python ') == 'python'

    def test_common_aliases(self):
        assert normalize_skill('ReactJS') == 'react'
        assert normalize_skill('Node') == 'node.js'
        assert normalize_skill('K8s') == 'kubernetes'
        assert normalize_skill('sklearn') == 'scikit-learn'
        assert normalize_skill('Postgres') == 'postgresql'

    def test_unknown_skill_passes_through(self):
        assert normalize_skill('Rust') == 'rust'


class TestFuzzyMatchKeywords:
    def test_exact_match(self):
        result = fuzzy_match_keywords(['python', 'sql'], ['python'])
        assert result['matched'] == ['python']
        assert result['missing'] == []

    def test_alias_match_counts_as_matched(self):
        # "postgres" on the resume should satisfy a JD asking for "postgresql"
        result = fuzzy_match_keywords(['postgres'], ['postgresql'])
        assert 'postgresql' in result['matched']

    def test_fuzzy_match_on_typos(self):
        # A JD typo ("pyton") should still fuzzy-match "python" at 80
        result = fuzzy_match_keywords(['python'], ['pyton'], threshold=80)
        assert 'pyton' in result['matched']

    def test_missing_keyword(self):
        result = fuzzy_match_keywords(['python'], ['kubernetes'])
        assert result['matched'] == []
        assert result['missing'] == ['kubernetes']

    def test_empty_resume_keywords(self):
        result = fuzzy_match_keywords([], ['python', 'aws'])
        assert result['matched'] == []
        assert sorted(result['missing']) == ['aws', 'python']

    def test_empty_jd_keywords(self):
        result = fuzzy_match_keywords(['python'], [])
        assert result['matched'] == [] and result['missing'] == []
