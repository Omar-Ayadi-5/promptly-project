"""Registration and sign-in rules independent of HTTP and providers."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import jwt
from werkzeug.security import check_password_hash, generate_password_hash


def utc_now():
    # PyMongo returns UTC datetimes without tzinfo by default.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthService:
    def __init__(self, users, chats, verification, mailer, signing_secret):
        self.users, self.chats = users, chats
        self.verification, self.mailer = verification, mailer
        self.signing_secret = signing_secret
        self.dummy_hash = generate_password_hash(secrets.token_urlsafe(32))

    def sign_in(self, email, password):
        user = self.users.find_by_email(email)
        valid = check_password_hash(user['password'] if user else self.dummy_hash, password)
        if not user or not valid:
            return {'error': 'Invalid email or password'}
        now = datetime.now(timezone.utc)
        payload = {'user_id': str(user['_id']), 'user_email': user['email'],
                   'iat': now, 'exp': now + timedelta(hours=1)}
        token = jwt.encode(payload, self.signing_secret, algorithm='HS256')
        return {'token': token, 'user_id': str(user['_id']), 'user_email': user['email']}

    def sign_up(self, email, password, code):
        if self.users.find_by_email(email):
            return {'error': 'Email already used'}
        # Final registration consumes the challenge atomically. The browser's
        # separate verification endpoint never authorizes account creation.
        if not self.verification.consume_code(email, self.code_hash(email, code), utc_now()):
            return {'error': 'Verification code is invalid or expired'}
        user = self.users.create_user(email, generate_password_hash(password))
        self.chats.create_chat(user.inserted_id, 'Your First Chat')
        return {'confirmed': True}

    def email_in_use(self, email):
        return self.users.find_by_email(email)

    def code_hash(self, email, code):
        return hmac.new(self.signing_secret.encode(), f'{email}:{code}'.encode(), hashlib.sha256).hexdigest()

    def send_code(self, email):
        code = f'{secrets.randbelow(1_000_000):06d}'
        now = utc_now()
        self.verification.save_code(email, self.code_hash(email, code), now, now + timedelta(minutes=10))
        return self.mailer.send_verification_email(email, code)

    def verify_code(self, email, code):
        record = self.verification.latest_code(email)
        return bool(record and record.get('expires_at', datetime.min) > utc_now()
                    and hmac.compare_digest(record.get('code_hash', ''), self.code_hash(email, code)))

    def allow_attempt(self, key, limit, seconds):
        return self.verification.allow_attempt(key, limit, seconds, utc_now())
