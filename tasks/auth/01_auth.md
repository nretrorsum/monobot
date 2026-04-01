# Auth — 01: Password Hashing

**File:** `app/auth/hashing.py`

---

## Goal

Provide async wrappers around `passlib` bcrypt so that hashing never blocks the event loop.  
All CPU work runs in a thread pool via `run_in_executor`.

---

## Implementation

```python
import asyncio
from passlib.context import CryptContext

_crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _crypt_context.hash, plain)

async def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _crypt_context.verify, plain, hashed)
```

## Rules

- `bcrypt` must **never** be called synchronously anywhere in the codebase outside this module
- Both functions must be `async`
- Do not expose the `_crypt_context` object outside this module