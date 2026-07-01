"""보안 모듈 단위 테스트 — DB 없이 실행 가능."""
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_device_id,
    mask_real_name,
)


def test_token_round_trip():
    token = create_access_token(subject="user-123", device_id="hash-abc", is_admin=False)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["device_id"] == "hash-abc"
    assert payload["is_admin"] is False


def test_admin_token():
    token = create_access_token(subject="admin", device_id="dev1", is_admin=True)
    payload = decode_access_token(token)
    assert payload["is_admin"] is True


def test_invalid_token():
    assert decode_access_token("not.a.real.token") is None


def test_device_hash_deterministic():
    h1 = hash_device_id("device-abc-123")
    h2 = hash_device_id("device-abc-123")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_device_hash_different_inputs():
    assert hash_device_id("device-a") != hash_device_id("device-b")


def test_mask_real_name():
    assert mask_real_name("김철수") == "김○○"
    assert mask_real_name("이영") == "이○"
    assert mask_real_name("이") == "이"
    assert mask_real_name("") == ""
    assert mask_real_name("Alexander") == "A○○○○○○○○"
