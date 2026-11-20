from functools import wraps
from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import DuplicateKeyError
from ...common.context import get_service
from ...common.validation import valid_code, valid_email, valid_password

blueprint = Blueprint('auth', __name__)


def limited(limit, seconds):
    def decorate(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            key = f'{handler.__name__}:{request.remote_addr}'
            if not get_service('auth').allow_attempt(key, limit, seconds):
                response = jsonify({'error': 'Too many attempts. Please try again later.'})
                response.headers['Retry-After'] = str(seconds)
                return response, 429
            return handler(*args, **kwargs)
        return wrapped
    return decorate


def account_input():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not valid_email(data.get('email')):
        return None
    return {**data, 'email': data['email'].strip().casefold()}


@blueprint.route('/api/sign_in', methods=['POST'])
@limited(10, 60)
def confirm_sign_in():
    data = account_input()
    if not data or not isinstance(data.get('password'), str) or not 1 <= len(data['password']) <= 128:
        return jsonify({'error': 'A valid email and password are required'}), 400
    result = get_service('auth').sign_in(data['email'], data['password'])
    return jsonify(result), 200 if 'token' in result else 401


@blueprint.route('/api/sign_up', methods=['POST'])
@limited(5, 300)
def sign_up():
    data = account_input()
    if not data or not valid_password(data.get('password')):
        return jsonify({'error': 'A valid email and a password of 12-128 characters are required'}), 400
    if not valid_code(data.get('code')):
        return jsonify({'error': 'A six-digit verification code is required'}), 400
    try:
        result = get_service('auth').sign_up(data['email'], data['password'], data['code'])
    except DuplicateKeyError:
        return jsonify({'error': 'Email already used'}), 409
    return jsonify(result), 200 if result.get('confirmed') else 400


@blueprint.route('/api/send_code', methods=['POST'])
@limited(5, 900)
def send_code():
    data = account_input()
    if not data:
        return jsonify({'error': 'A valid email is required'}), 400
    auth = get_service('auth')
    if auth.email_in_use(data['email']):
        return jsonify({'error': 'Email already used'}), 409
    try:
        status = auth.send_code(data['email'])
    except Exception:
        current_app.logger.exception('Verification email delivery failed')
        return jsonify({'error': 'Unable to send a verification code. Please try again later.'}), 503
    if status == 202:
        return jsonify({'message': 'Code sent!'}), 200
    return jsonify({'error': 'Failed to send email'}), 503


@blueprint.route('/api/verify_code', methods=['POST'])
@limited(10, 600)
def verify_code():
    data = account_input()
    if not data or not valid_code(data.get('code')):
        return jsonify({'verified': False}), 400
    if get_service('auth').verify_code(data['email'], data['code']):
        return jsonify({'verified': True}), 200
    return jsonify({'verified': False}), 400
