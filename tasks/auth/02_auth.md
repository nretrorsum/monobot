# Auth — 02: JWT Tokens

**File:** `app/auth/tokens.py`

---

## Goal

Generate and validate access and refresh JWTs.  
Refresh tokens carry a `jti` (UUID) which is later stored in the DB for revocation.

---

## Token shapes

**Access token payload:**
```json
{ "sub": "<user_id>", "type": "access", "exp": "<timestamp>" }
```

**Refresh token payload:**
```json
{ "jti": "<uuid4>", "type": "refresh", "exp": "<timestamp>" }
```

---

## Functions to implement

```python
def create_access_token(subject: int | str, extra: dict | None = None) -> str:
    """Create a signed access JWT for the given subject (user id)."""
    ...

def create_refresh_token() -> tuple[str, str]:
    """
    Create a signed refresh JWT.
    Returns (signed_jwt, jti) — jti is a uuid4 string embedded in the payload.
    """
    ...

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises HTTP 401 if the token is expired or invalid.
    """
    ...
```

---

## Rules

- Read `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` from project settings
- Use `python-jose` (`from jose import jwt, JWTError`)
- Use `datetime.now(UTC)` for expiry calculation
- `decode_token` must raise `HTTPException(status_code=401)` on any `JWTError` or expiry — never let raw exceptions propagate
- `create_refresh_token` must return both the signed JWT **and** the raw `jti` — the caller needs the jti to hash and store it