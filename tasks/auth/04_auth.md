# Auth — 04: Schemas, Dependencies & Router

**Files:** `app/auth/schemas.py`, `app/auth/dependencies.py`, `app/auth/router.py`

---

## Schemas

**File:** `app/auth/schemas.py`

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str  # min length 8

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Returned to mobile/bot clients instead of setting cookies."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## Dependencies

**File:** `app/auth/dependencies.py`

```python
async def detect_client_type(request: Request) -> str:
    """Return 'mobile' if X-Client-Type header equals 'mobile', else 'web'."""
    ...

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the access token.
    Priority: cookie 'access_token' → Authorization: Bearer header.
    Raises HTTP 401 if missing or invalid.
    """
    ...

# Convenience type alias
ClientType = Annotated[str, Depends(detect_client_type)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

---

## Endpoints

**File:** `app/auth/router.py`

### `POST /auth/register`

- Hash password, create user via `register_user`
- Call `create_token_pair`
- **Web:** set cookies (use `set_auth_cookies` from overview), return `UserOut`
- **Mobile:** return `TokenResponse`

### `POST /auth/login`

- Authenticate via `authenticate_user`
- Call `create_token_pair`
- **Web:** set cookies, return `UserOut`
- **Mobile:** return `TokenResponse`

### `POST /auth/refresh`

- **Web:** read `refresh_token` from cookie
- **Mobile:** read from JSON body `{ "refresh_token": "..." }` — add a small request schema `RefreshRequest(BaseModel)`
- Call `rotate_refresh_token`
- **Web:** update cookies, return `UserOut`
- **Mobile:** return new `TokenResponse`

### `POST /auth/logout`

- Requires `CurrentUser`
- **Web:** read `refresh_token` from cookie
- **Mobile:** read from JSON body `{ "refresh_token": "..." }`
- Call `revoke_refresh_token`
- **Web:** delete both cookies (`response.delete_cookie`)
- Return `{ "detail": "logged out" }`

### `GET /auth/me`

- Requires `CurrentUser`
- Return `UserOut.model_validate(current_user)`

---

## Registration

In `main.py` (or wherever routers are included):

```python
app.include_router(auth_router, prefix="/auth", tags=["auth"])
```