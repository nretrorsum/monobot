# Auth System — Overview

## Goal

Implement JWT-based authentication for a FastAPI application.  
Web clients receive tokens via `httpOnly` cookies.  
Mobile / bot clients receive tokens in the JSON response body and send them via `Authorization: Bearer`.

## Related tasks

- `01_auth.md` — password hashing layer
- `02_auth.md` — JWT generation & validation
- `03_auth.md` — refresh token DB model & service
- `04_auth.md` — schemas, dependencies, endpoints

> Complete tasks in order — each one builds on the previous.

---



> Inspect the existing project before creating files.  
> If a `User` model already exists — use it. If not — create a minimal one with `id`, `email`, `hashed_password`, `created_at`.  
> Follow the existing DB session / base / settings patterns already present in the project.

---

## Client detection

All endpoints that return tokens must detect the client type from the request header:

```
X-Client-Type: mobile
```

Absent or any other value → `"web"`.

A FastAPI dependency `detect_client_type(request: Request) -> str` should encapsulate this logic and be reused across all endpoints.

---

## Cookie settings

Use this helper for setting cookies consistently:

```python
def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
```

---

## Settings

Ensure the following variables exist in the project settings (create if missing):

```
SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
SECURE_COOKIES=true
```

---

## General rules

- Every function must have full type annotations on arguments and return type
- All DB calls must use `AsyncSession`
- Use `datetime.now(UTC)` — never `datetime.utcnow()`
- Add a short docstring to every public function
- Register the auth router in the main app with prefix `/auth` and tag `"auth"`