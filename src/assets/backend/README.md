# Promptly backend

The Flask API keeps feature modules with controllers, services, repositories, serializers, and provider adapters. React is the view layer. See the [root README](../../../README.md) for setup, environment variables, tests, and deployment.

## Responsibilities

- `app/__init__.py`: application factory, dependency injection, blueprint registration, indexes, and request limits.
- `app/config.py`: environment configuration and CORS origins.
- `app/common/`: bearer-token validation, account input validation, shared errors, and service lookup.
- `app/modules/auth/`: registration, sign-in, hashed expiring verification codes, and MongoDB-backed rate counters.
- `app/modules/users/`: password changes scoped to the token subject and account deletion.
- `app/modules/chats/`: conversation and message persistence.
- `app/modules/generation/`: request validation, model-aware provider requests, and assistant-message persistence.
- `app/modules/catalog/`: free-model metadata and header-authenticated catalog refresh.
- `app/modules/voice/`: bounded audio uploads, transcription, storage, and account-owned recording deletion.
- `app/infrastructure/`: MongoDB, OpenRouter, AssemblyAI, and SendGrid adapters.

Services do not import Flask. Repositories receive their database through the factory. Controllers resolve services from `app.extensions["promptly"]`. Tests inject `database`, `ai_client`, `transcription`, `mailer`, and `catalog_provider` to avoid network calls and real writes.

## Authentication contract

`POST /api/send_code` sends a six-digit code. `POST /api/verify_code` can check validity, but does not authorize signup. `POST /api/sign_up` must include `email`, a 12-128 character `password`, and `code`; it atomically consumes the unexpired challenge. Codes expire after ten minutes and only their HMAC hashes are stored.

`POST /api/sign_in` returns an HS256 JWT with a one-hour expiry. Protected routes require `Authorization: Bearer <token>`. Non-expiring legacy tokens are rejected. Failed login responses are generic; other validation and authorization failures use HTTP 4xx responses.

`GET /update_models` requires `X-Admin-Key`. Missing configuration and query-string secrets are rejected. The route path and HTTP method remain compatible with the existing architecture.

Provider-specific variable spellings are preserved in `.env.example`. The SendGrid sender is environment configuration. Requirements and transitive constraints are pinned. Startup fails on a missing or weak signing secret; `.env` is loaded from the backend directory regardless of the working directory.

Use `main:app` as the WSGI target. For unit and HTTP tests, use the factory directly rather than importing `main`, which initializes real connections.
