# Auth — 03: Refresh Token Storage

**Files:** `app/models/refresh_token.py`, `app/auth/service.py`

---

## Goal

Persist refresh token identifiers in the database to enable per-device revocation and token theft detection.  
The raw `jti` is **never** stored — only its `sha256` hash.

---

## ORM model

**File:** `app/models/refresh_token.py`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `jti_hash` | str, unique | `sha256(jti)` |
| `user_id` | int, FK → User | |
| `client_type` | str | `"web"` or `"mobile"` |
| `expires_at` | datetime | for future cleanup jobs |
| `created_at` | datetime | auto |

Add a composite index on `(user_id, client_type)` for fast per-device lookup.

---

## Service functions

**File:** `app/auth/service.py`

```python
async def register_user(db: AsyncSession, data: RegisterRequest) -> UserOut:
    """Hash password and persist a new User. Raises 400 if email already exists."""
    ...

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Load user by email and verify password. Raises 401 on failure."""
    ...

async def create_token_pair(
    db: AsyncSession, user_id: int, client_type: str
) -> tuple[str, str]:
    """
    Generate an access + refresh token pair.
    Persists sha256(jti) to the DB and returns (access_token, refresh_jwt).
    """
    ...

async def rotate_refresh_token(
    db: AsyncSession, old_refresh_jwt: str, client_type: str
) -> tuple[str, str]:
    """
    Validate the old refresh JWT, delete its jti_hash, issue a new pair.
    Returns (new_access_token, new_refresh_jwt).

    Token theft detection:
    If jti_hash is not found in DB (already rotated), revoke ALL refresh tokens
    for this user_id and raise HTTP 401 with detail='Token reuse detected'.
    """
    ...

async def revoke_refresh_token(db: AsyncSession, jti: str) -> None:
    """Delete the refresh token record matching sha256(jti). Silent if not found."""
    ...
```

---

## jti hashing helper (private)

Add a small private helper inside `service.py`:

```python
def _hash_jti(jti: str) -> str:
    """Return sha256 hex digest of a jti string."""
    import hashlib
    return hashlib.sha256(jti.encode()).hexdigest()
```