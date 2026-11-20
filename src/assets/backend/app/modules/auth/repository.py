"""Expiring challenges and atomic request counters shared across workers."""
from datetime import timedelta
import calendar
import hashlib
from pymongo import ReturnDocument


class VerificationRepository:
    def __init__(self, database):
        self.database = database

    def ensure_indexes(self):
        # Legacy verif_codes contains multiple plaintext codes per email.
        # Isolate the new one-challenge-per-email schema without deleting data.
        self.database['verification_challenges'].create_index('email', unique=True)
        self.database['verification_challenges'].create_index('expires_at', expireAfterSeconds=0)
        self.database['auth_limits'].create_index('expires_at', expireAfterSeconds=0)

    def save_code(self, email, code_hash, sent_at, expires_at):
        return self.database['verification_challenges'].update_one(
            {'email': email},
            {'$set': {'code_hash': code_hash, 'sent_at': sent_at, 'expires_at': expires_at},
             '$unset': {'code': ''}}, upsert=True)

    def latest_code(self, email):
        return self.database['verification_challenges'].find_one({'email': email}, sort=[('sent_at', -1)])

    def consume_code(self, email, code_hash, now):
        return self.database['verification_challenges'].find_one_and_delete(
            {'email': email, 'code_hash': code_hash, 'expires_at': {'$gt': now}})

    def allow_attempt(self, key, limit, seconds, now):
        bucket = calendar.timegm(now.utctimetuple()) // seconds
        identifier = hashlib.sha256(f'{key}:{bucket}'.encode()).hexdigest()
        record = self.database['auth_limits'].find_one_and_update(
            {'_id': identifier},
            {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': now + timedelta(seconds=seconds * 2)}},
            upsert=True, return_document=ReturnDocument.AFTER)
        return record['count'] <= limit
