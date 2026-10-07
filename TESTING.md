# Testing

FastAPI project root: `services/api`. Frontend project root: `uis/backoffice`.

## Run

```bash
cd services/api
uv run pytest
uv run pytest --cov
```

```bash
cd uis/backoffice
npx jest --coverage
```

## Register — `POST /users`

`tests/test_register.py`

- Happy path: a new email and password create an active account and a profile. The password hash is not returned.
- Edge case: the stored role is `user`.
- Failure: a duplicate email is rejected. An empty password is rejected.

Included because a duplicate account and an empty password are the registration failures covered here.

## Login — `POST /auth/login`

`tests/test_login.py`

- Happy path: the correct email and password produce a token whose subject is that user id.
- Edge case: an inactive account is rejected.
- Failure: a wrong password, an unknown email, and an empty password are rejected.

Included because login must accept only an active account with the stored password.

## Token — `GET /auth/me`

`tests/test_token.py`

- Happy path: a valid token resolves to that user and includes the profile.
- Edge case: a signed token with no subject is rejected. A user with no profile returns `profile: null`.
- Failure: an expired token, a malformed token, a missing token, and a token for an inactive or deleted user are rejected.

Included because the reported outage was token expiration, and a signed token can still be unusable.

## Coverage

`uv run pytest --cov` from `services/api` (statement coverage):

| Module | Coverage |
| --- | --- |
| `security.py` | 100% |
| `users.py` | 100% |
| `deps.py` | 100% |
| `profiles.py` | 100% |

Authentication module (`security.py`, `users.py`, `deps.py`): 100%.

## Extra — users and profiles

`tests/test_users.py` and `tests/test_profiles.py`

- Users: list and read hide the password hash. Editing another user is forbidden. An admin can change role and password. A member cannot change role. A duplicate email on update is rejected. Update or delete of a missing user fails. Deleting a user removes the profile.
- Profiles: read and update keep fields that were not sent. An empty name can be saved. A missing profile is rejected.

`users.py` and `profiles.py` statement coverage: 100%.

## Extra — frontend session helpers

`uis/backoffice/tests/session.test.ts`

- `getToken`: returns the stored token; returns null when none is stored.
- `setToken`: writes the token; throws when no browser storage exists.
- `clearToken`: removes the token; stays empty when nothing was stored.

`npx jest --coverage` from `uis/backoffice`: `session.ts` 100% lines, 88.88% statements.
