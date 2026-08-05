from app.core.security import generate_token, hash_password, verify_password


def test_hash_password_produces_argon2_hash():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed.startswith("$argon2")
    assert hashed != "correct-horse-battery-staple"


def test_hash_password_is_salted_and_nondeterministic():
    first = hash_password("same-password")
    second = hash_password("same-password")
    assert first != second


def test_verify_password_accepts_correct_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password(hashed, "correct-horse-battery-staple") is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password(hashed, "wrong-password") is False


def test_verify_password_rejects_malformed_hash_instead_of_raising():
    assert verify_password("not-a-real-argon2-hash", "anything") is False


def test_generate_token_is_url_safe_and_sufficiently_long():
    token = generate_token()
    assert len(token) >= 32
    assert all(c.isalnum() or c in "-_" for c in token)


def test_generate_token_is_unique_per_call():
    tokens = {generate_token() for _ in range(50)}
    assert len(tokens) == 50
