"""Scoring engine — component scores, clamping, and the overall blend."""
import pytest

from backend.services.ats_scorer import (
    _calc_ats_compatibility_score,
    _calc_content_score,
    _calc_formatting_score,
    _calc_keywords_score,
    _calc_skill_validation_score,
    _tier_score,
    calculate_overall_score,
)


class TestTierScore:
    def test_hits_first_qualifying_tier(self):
        assert _tier_score(15, [(15, 5.0), (10, 4.0)]) == 5.0

    def test_falls_through_to_lower_tier(self):
        assert _tier_score(12, [(15, 5.0), (10, 4.0)]) == 4.0

    def test_below_all_tiers_is_zero(self):
        assert _tier_score(0, [(1, 2.0)]) == 0.0


def _rich_parsed_resume():
    # Descriptions are >= 20 chars: the ATS-compat score penalizes short sections.
    return {
        'experience': [{'job_title': 'SWE', 'description': 'Built large-scale distributed systems'}],
        'education': [{'degree': 'BSc Computer Science', 'institution': 'Massachusetts Tech'}],
        'skills': ['python', 'sql', 'aws', 'docker'],
        'professional_summary': 'A summary that is definitely longer than thirty characters.',
        'projects': [{'name': 'ATS scorer', 'description': 'This project'}],
    }


class TestFormattingScore:
    def test_complete_resume_scores_high(self):
        text = '\n'.join(['• bullet one'] * 20)
        score = _calc_formatting_score(_rich_parsed_resume(), text)
        assert 15.0 <= score <= 20.0

    def test_empty_resume_scores_zero(self):
        assert _calc_formatting_score({}, '') == 0.0

    def test_never_exceeds_max(self):
        text = '\n'.join(['• bullet'] * 200)
        assert _calc_formatting_score(_rich_parsed_resume(), text) <= 20.0


class TestKeywordsScore:
    def test_rich_keyword_profile_scores_well(self):
        score = _calc_keywords_score(
            resume_keywords=[f'kw{i}' for i in range(20)],
            skills=[f'skill{i}' for i in range(15)],
        )
        assert score >= 15.0

    def test_sparse_profile_scores_poorly(self):
        score = _calc_keywords_score(resume_keywords=[], skills=[])
        assert score == 0.0

    def test_jd_match_adds_points(self):
        with_jd = _calc_keywords_score(
            resume_keywords=['python', 'sql', 'aws', 'docker', 'react'],
            skills=['python', 'sql', 'aws'],
            jd_keywords=['python', 'sql', 'aws', 'docker', 'react'],
        )
        without_jd = _calc_keywords_score(
            resume_keywords=['python', 'sql', 'aws', 'docker', 'react'],
            skills=['python', 'sql', 'aws'],
        )
        assert with_jd > without_jd

    def test_clamped_to_25(self):
        score = _calc_keywords_score(
            resume_keywords=[f'kw{i}' for i in range(50)],
            skills=[f'skill{i}' for i in range(50)],
            jd_keywords=['kw1', 'kw2'],
        )
        assert score <= 25.0


class TestContentScore:
    def test_quantified_achievements_score(self):
        text = 'increased revenue by 40% and served 2M users, saved $500'
        score = _calc_content_score(
            text, action_verbs=['led', 'built', 'shipped'] * 5, grammar_results={},
        )
        assert score > 10.0

    def test_plain_text_gets_only_grammar_baseline(self):
        # No action verbs, no quantified achievements — the only points come
        # from the 10-point clean-grammar sub-score baked into content score.
        score = _calc_content_score(
            'did some stuff', action_verbs=[], grammar_results={},
        )
        assert score == 10.0

    def test_grammar_penalty_reduces_score(self):
        base = _calc_content_score('built x', ['led'], {})
        penalized = _calc_content_score('built x', ['led'], {'penalty_applied': 10.0})
        assert penalized < base


class TestSkillValidationScore:
    def test_passes_through_validation_score(self):
        assert _calc_skill_validation_score({'validation_score': 12.0}) == 12.0

    def test_clamped_to_max_15(self):
        assert _calc_skill_validation_score({'validation_score': 99.0}) == 15.0

    def test_defaults_to_zero(self):
        assert _calc_skill_validation_score({}) == 0.0


class TestAtsCompatibilityScore:
    def test_clean_resume_keeps_full_score(self):
        score = _calc_ats_compatibility_score(
            'Clean text', {'penalty_applied': 0.0}, _rich_parsed_resume(),
        )
        assert score == 15.0

    def test_location_penalty_is_deducted(self):
        score = _calc_ats_compatibility_score(
            'Clean text', {'penalty_applied': 5.0}, _rich_parsed_resume(),
        )
        assert score == 10.0

    def test_table_characters_are_deducted(self):
        text = 'resume │ with ├ box ═ chars' * 5
        score = _calc_ats_compatibility_score(
            text, {'penalty_applied': 0.0}, _rich_parsed_resume(),
        )
        assert score < 15.0


class TestCalculateOverallScore:
    def _inputs(self, **overrides):
        base = dict(
            text='Built systems • led teams • grew metrics by 50%',
            parsed_resume=_rich_parsed_resume(),
            skills=['python', 'sql', 'aws'],
            keywords=['python', 'sql', 'aws', 'docker'],
            action_verbs=['built', 'led', 'grew'],
            skill_validation_results={'validation_score': 12.0},
            grammar_results={},
            location_results={'penalty_applied': 0.0},
        )
        base.update(overrides)
        return base

    def test_result_is_within_0_100(self):
        result = calculate_overall_score(**self._inputs())
        assert 0.0 <= result['overall_score'] <= 100.0

    def test_weak_resume_scores_lower_than_strong(self):
        strong = calculate_overall_score(**self._inputs())['overall_score']
        weak = calculate_overall_score(
            text='stuff',
            parsed_resume={},
            skills=[],
            keywords=[],
            action_verbs=[],
            skill_validation_results={'validation_score': 0.0},
            grammar_results={'penalty_applied': 10.0},
            location_results={'penalty_applied': 5.0},
        )['overall_score']
        assert weak < strong

    def test_penalties_recorded(self):
        result = calculate_overall_score(
            **self._inputs(
                grammar_results={'penalty_applied': 4.0},
                location_results={'penalty_applied': 5.0},
            )
        )
        assert 'grammar' in result.get('penalties', {})
        assert 'location_privacy' in result.get('penalties', {})

    def test_component_scores_present(self):
        result = calculate_overall_score(**self._inputs())
        for key in ('formatting_score', 'keywords_score', 'content_score',
                    'skill_validation_score', 'ats_compatibility_score'):
            assert key in result
