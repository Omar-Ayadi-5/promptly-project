# Security

Do not commit real `.env` files, database exports, provider keys, private keys, or browser recordings containing personal information. Commit only `.env.example` templates. Frontend environment variables are visible to visitors.

If a credential has ever been published, revoke or rotate it at its provider. Creating a new repository does not revoke previously exposed credentials. Rotate the JWT signing secret to invalidate tokens signed with the old value.

Before publishing, run `python scripts/check_secrets.py` and inspect the staged file list. The scanner catches common credential patterns; it is an additional check, not a guarantee that every kind of secret is detected.

To report a vulnerability, use this repository's GitHub private vulnerability reporting option when available. If it is unavailable, contact the maintainer privately through their GitHub profile. Do not include credentials or exploit details in a public issue.

The deployment limitations and session behavior are documented in the main README. This project is a portfolio application and has not undergone an independent security audit.
