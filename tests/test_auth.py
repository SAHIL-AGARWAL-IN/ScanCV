"""JWT auth — token verification and the get_current_user dependency.

Uses forged HS256 tokens signed with a test secret (the real Supabase secret
from .env is never used or asserted against).
"""
import time

import jwt as pyjwt
import pytest
from fastapi import HTTPException

import backend.api.auth as auth

TEST_SECRET = 'test-only-secret-0123456789abcdef0123456789abcdef'
AUD = 'authenticated'


def _make_token(secret=TEST_SECRET, alg='HS256', **claims):
    payload = {'sub': 'user-123', 'aud': AUD, 'exp': int(time.time()) + 3600}
    payload.update(claims)
    return pyjwt.encode(payload, secret, algorithm=alg)


@pytest.fixture(autouse=True)
def _configure_secrets(monkeypatch):
    """Point auth at the test secret; keep JWKS (ES256) path disabled."""
    monkeypatch.setattr(auth, 'SUPABASE_JWT_SECRET', TEST_SECRET)
    monkeypatch.setattr(auth, 'SUPABASE_URL', '')


class TestVerifyToken:
    def test_valid_hs256_token(self):
        payload = auth._verify_token(_make_token())
        assert payload['sub'] == 'user-123'

    def test_expired_token_rejected(self):
        with pytest.raises(pyjwt.ExpiredSignatureError):
            auth._verify_token(_make_token(exp=int(time.time()) - 10))

    def test_wrong_secret_rejected(self):
        with pytest.raises(pyjwt.InvalidTokenError):
            auth._verify_token(_make_token(secret='wrong-secret'))

    def test_wrong_audience_rejected(self):
        with pytest.raises(pyjwt.InvalidTokenError):
            auth._verify_token(_make_token(aud='other-audience'))

    def test_garbage_token_rejected(self):
        with pytest.raises(pyjwt.InvalidTokenError):
            auth._verify_token('not-a-jwt')

    def test_unsupported_algorithm_rejected(self):
        # "none" alg must not silently pass
        token = pyjwt.encode({'sub': 'x'}, key='', algorithm='none')
        with pytest.raises(pyjwt.InvalidTokenError, match='Unsupported'):
            auth._verify_token(token)


class TestGetCurrentUser:
    def test_missing_header_is_401(self):
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user(creds=None)
        assert exc_info.value.status_code == 401

    def test_returns_user_id_for_valid_token(self):
        creds = type('Creds', (), {'credentials': _make_token()})()
        assert auth.get_current_user(creds=creds) == 'user-123'

    def test_token_without_subject_is_401(self):
        token = _make_token(sub=None)
        creds = type('Creds', (), {'credentials': token})()
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user(creds=creds)
        assert 'subject' in exc_info.value.detail.lower()
