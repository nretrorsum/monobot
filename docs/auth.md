# Authentication API

JWT-based автентифікація з підтримкою web та mobile клієнтів.

## Огляд

- **Access token** — короткоживучий JWT (15 хв), містить `sub` (user ID) та `type: "access"`
- **Refresh token** — довгоживучий JWT (30 днів), містить `jti` (UUID) та `type: "refresh"`
- Web клієнти отримують токени через `httpOnly` cookies
- Mobile клієнти отримують токени в JSON body та надсилають через `Authorization: Bearer`

## Визначення клієнта

Усі ендпоінти визначають тип клієнта через заголовок:

```
X-Client-Type: mobile
```

Якщо заголовок відсутній або має інше значення — вважається `web`.

## Ендпоінти

### POST /auth/register

Реєстрація нового користувача.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "minimum8chars"
}
```

**Response (mobile):** `TokenResponse`
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Response (web):** `UserOut` + cookies
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-04-01T12:00:00Z"
}
```

### POST /auth/login

Автентифікація існуючого користувача.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**Response:** аналогічно `/auth/register`.

### POST /auth/refresh

Оновлення пари токенів. Старий refresh token інвалідується (rotation).

**Web:** refresh token читається з cookie, тіло запиту порожнє.

**Mobile:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:** аналогічно `/auth/login`.

**Token theft detection:** якщо refresh token вже був використаний (повторне використання), сервер повертає `401 Token reuse detected`.

### POST /auth/logout

Вимагає автентифікацію (access token).

**Web:** refresh token читається з cookie, cookies видаляються.

**Mobile:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "detail": "logged out"
}
```

### GET /auth/me

Повертає поточного автентифікованого користувача. Вимагає access token.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-04-01T12:00:00Z"
}
```

## Змінні середовища

| Змінна | За замовчуванням | Опис |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Ключ для підпису JWT |
| `ALGORITHM` | `HS256` | Алгоритм JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Час життя access token (хв) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Час життя refresh token (днів) |
| `SECURE_COOKIES` | `true` | Secure flag для cookies (вимкнути для HTTP) |

## Безпека

- Паролі хешуються через `bcrypt`
- Refresh token `jti` зберігається в БД як `sha256` хеш
- При ротації старий refresh token видаляється з БД
- Повторне використання refresh token (theft detection) тригерить `401`
- Cookies мають прапори `httpOnly`, `secure`, `samesite=lax`

## Архітектура файлів

| Файл | Відповідальність |
|---|---|
| `src/core/hashing.py` | Async bcrypt хешування |
| `src/core/jwt.py` | Створення та декодування JWT |
| `src/core/dependencies.py` | FastAPI dependencies (client type, current user, cookies) |
| `src/schemas/jwt_auth.py` | Pydantic схеми запитів/відповідей |
| `src/services/jwt_auth.py` | Бізнес-логіка (реєстрація, автентифікація, ротація токенів) |
| `src/routers/jwt_auth.py` | HTTP ендпоінти |
| `src/models/refresh_token.py` | ORM модель для зберігання refresh tokens |
