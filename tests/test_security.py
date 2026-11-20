"""Regression tests for authentication, configuration, and account isolation."""
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import MagicMock, patch
import jwt
from bson import ObjectId
import test_backend_contracts as contracts
from test_backend_contracts import USER, EMAIL, SECRET
from app import create_app
from app.modules.auth.repository import VerificationRepository


class SecurityTests(unittest.TestCase):
    setUp = contracts.BackendContracts.setUp
    request = contracts.BackendContracts.request
    existing_user = contracts.BackendContracts.existing_user

    def signup(self, **changes):
        payload = {"email": EMAIL, "password": "a-long-test-password", "code": "123456"}
        payload.update(changes)
        return self.http.post('/api/sign_up', json=payload)

    def test_signup_cannot_skip_verification(self):
        self.assertEqual(self.signup(code=None).status_code, 400)
        self.assertEqual(self.signup().status_code, 400)
        self.database['users'].insert_one.assert_not_called()

    def test_signup_rejects_weak_password_before_consuming_code(self):
        for password in ('x', '', 'a' * 129, {'$ne': None}):
            self.assertEqual(self.signup(password=password).status_code, 400)
        self.database['verification_challenges'].find_one_and_delete.assert_not_called()

    def test_code_consumption_is_atomic_and_cannot_be_replayed(self):
        self.database['verification_challenges'].find_one_and_delete.side_effect = [{"email": EMAIL}, None]
        self.assertEqual(self.signup().status_code, 200)
        self.assertEqual(self.signup().status_code, 400)
        self.assertEqual(self.database['users'].insert_one.call_count, 1)
        query = self.database['verification_challenges'].find_one_and_delete.call_args.args[0]
        self.assertEqual(query['email'], EMAIL)
        self.assertEqual(query['code_hash'], self.app.extensions['promptly']['auth'].code_hash(EMAIL, '123456'))
        self.assertIsInstance(query['expires_at']['$gt'], datetime)

    def test_expired_or_legacy_code_is_rejected(self):
        auth = self.app.extensions['promptly']['auth']
        for record in ({'code': '123456'}, {'code_hash': auth.code_hash(EMAIL, '123456'), 'expires_at': datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)}):
            self.database['verification_challenges'].find_one.return_value = record
            self.assertFalse(auth.verify_code(EMAIL, '123456'))

    def test_malformed_login_data_cannot_be_used_as_mongo_operators(self):
        for payload in ([], None, {'email': {'$ne': None}, 'password': 'password'}, {'email': EMAIL, 'password': {'$ne': None}}):
            self.assertEqual(self.http.post('/api/sign_in', json=payload).status_code, 400)
        self.database['users'].find_one.assert_not_called()

    def test_rate_limit_is_enforced_with_retry_header(self):
        self.database['auth_limits'].find_one_and_update.return_value = {'count': 11}
        response = self.http.post('/api/sign_in', json={'email': EMAIL, 'password': 'password'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '60')
        self.database['users'].find_one.assert_not_called()

    def test_rate_counter_uses_atomic_increment_and_expiring_buckets(self):
        repo = VerificationRepository(self.database)
        now = datetime(2026, 1, 1)
        self.database['auth_limits'].find_one_and_update.return_value = {'count': 2}
        self.assertFalse(repo.allow_attempt('sign-in:test-ip', 1, 60, now))
        query, update = self.database['auth_limits'].find_one_and_update.call_args.args
        self.assertNotIn('test-ip', query['_id'])
        self.assertEqual(update['$inc'], {'count': 1})
        self.assertGreater(update['$setOnInsert']['expires_at'], now)

    def test_missing_admin_secret_rejects_access_without_calling_provider(self):
        self.app.config['ADMIN_SECRET'] = None
        self.assertEqual(self.http.get('/update_models').status_code, 403)
        self.catalog.fetch_models.assert_not_called()

    def test_admin_query_secret_is_not_accepted(self):
        self.assertEqual(self.http.get('/update_models?key=test-admin').status_code, 403)
        self.catalog.fetch_models.assert_not_called()

    def test_non_expiring_tokens_and_other_schemes_are_rejected(self):
        token = jwt.encode({'user_id': USER}, SECRET, algorithm='HS256')
        for value in (f'Bearer {token}', f'Basic {token}'):
            response = self.http.get('/api/Load_models', headers={'Authorization': value})
            self.assertEqual(response.status_code, 401)
        self.database['models'].find.assert_not_called()

    def test_missing_or_invalid_subject_is_rejected(self):
        for claims in ({}, {'user_id': {}}, {'user_id': 'bad-id'}):
            token = jwt.encode({**claims, 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}, SECRET, algorithm='HS256')
            self.assertEqual(self.http.get('/api/Load_models', headers={'Authorization': f'Bearer {token}'}).status_code, 401)

    def test_password_change_uses_token_identity_instead_of_submitted_email(self):
        self.existing_user()
        payload = {'userId': USER, 'userEmail': 'another@example.com', 'currentPassword': 'original-password', 'newPassword': 'a-new-long-password'}
        self.assertEqual(self.request('POST', '/api/change_password', json=payload).status_code, 200)
        self.database['users'].find_one.assert_called_with({'_id': ObjectId(USER)})
        self.assertEqual(self.database['users'].update_one.call_args.args[0], {'_id': ObjectId(USER)})

    def test_password_change_rejects_short_passwords(self):
        self.assertEqual(self.request('POST', '/api/change_password', json={'userId': USER, 'currentPassword': 'password', 'newPassword': 'x'}).status_code, 400)
        self.database['users'].update_one.assert_not_called()

    def test_upload_size_limit_is_enforced_before_audio_processing(self):
        self.app.config['MAX_CONTENT_LENGTH'] = 100
        response = self.request('POST', '/api/save_voice_message', data=b'x' * 101, content_type='application/octet-stream')
        self.assertEqual(response.status_code, 413)
        self.transcription.transcribe.assert_not_called()

    def test_startup_does_not_index_or_modify_duplicate_legacy_codes(self):
        from pymongo.errors import DuplicateKeyError

        names = ('users', 'verif_codes', 'verification_challenges', 'auth_limits')
        collections = {name: MagicMock(name=name) for name in names}
        database = MagicMock()
        database.__getitem__.side_effect = collections.__getitem__
        collections['verif_codes'].create_index.side_effect = DuplicateKeyError('legacy duplicate emails')
        with patch('app.create_database', return_value=database):
            app = create_app({'TOKEN_SECRET': SECRET}, ai_client=MagicMock(),
                             transcription=MagicMock(), mailer=MagicMock(),
                             catalog_provider=MagicMock())
        self.assertEqual(app.test_client().get('/api/server_health').status_code, 200)
        self.assertEqual(collections['verif_codes'].mock_calls, [])
        collections['verification_challenges'].create_index.assert_any_call('email', unique=True)
        collections['verification_challenges'].create_index.assert_any_call('expires_at', expireAfterSeconds=0)
        collections['auth_limits'].create_index.assert_called_once_with('expires_at', expireAfterSeconds=0)

    def test_weak_signing_secrets_fail_before_database_creation(self):
        for secret in (None, '', 'short', 'replace-with-a-random-token-signing-secret'):
            with patch('app.create_database') as database:
                with self.assertRaises(ValueError):
                    create_app({'TOKEN_SECRET': secret})
                database.assert_not_called()


if __name__ == '__main__':
    unittest.main()
