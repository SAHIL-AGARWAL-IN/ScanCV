import pytest
from backend.services.grammar_checker import check_grammar_and_spelling
from backend.services.cache_service import get_cache_key, get_cached_analysis, set_cached_analysis, clear_cache
from backend.api.auth import get_optional_user


class TestGrammarChecker:
    def test_clean_text_returns_perfect_score(self):
        clean_text = "Developed full-stack web applications using FastAPI and React. Led team of 5 engineers."
        result = check_grammar_and_spelling(clean_text)
        assert result['grammar_score'] >= 95.0
        assert result['penalty_applied'] == 0.0
        assert len(result['critical_errors']) == 0

    def test_detects_common_resume_typos(self):
        typo_text = "Acheived high perfomance and was reponsible for database managment."
        result = check_grammar_and_spelling(typo_text)
        assert len(result['critical_errors']) >= 3
        assert result['penalty_applied'] > 0
        assert result['grammar_score'] < 100.0

    def test_detects_repeated_words(self):
        repeated_text = "Deployed to the the production server in in the cloud."
        result = check_grammar_and_spelling(repeated_text)
        assert len(result['moderate_errors']) >= 1


class TestCacheService:
    def setup_method(self):
        clear_cache()

    def test_cache_hit_and_miss(self):
        file_bytes = b"Sample resume binary data"
        jd = "Software Engineer job description"
        key = get_cache_key(file_bytes, jd)

        assert get_cached_analysis(key) is None

        mock_result = {"ats_score": 88, "status": "analyzed"}
        set_cached_analysis(key, mock_result)

        cached = get_cached_analysis(key)
        assert cached is not None
        assert cached["ats_score"] == 88


class TestGuestAuth:
    def test_get_optional_user_none_creds(self):
        assert get_optional_user(None) == "guest_user"
