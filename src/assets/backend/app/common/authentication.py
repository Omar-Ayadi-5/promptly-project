"""Validate expiring bearer tokens before protected routes."""
from functools import wraps
from bson import ObjectId
from flask import current_app, jsonify, request
import jwt


def token_required(handler):
    @wraps(handler)
    def decorated(*args, **kwargs):
        authorization = request.headers.get('Authorization', '')
        if not authorization:
            return jsonify({'message': 'Token is missing!'}), 401
        parts = authorization.split(' ', 1)
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Token format is invalid!'}), 401
        if not parts[1].strip():
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            payload = jwt.decode(parts[1], current_app.config['TOKEN_SECRET'], algorithms=['HS256'],
                                 options={'require': ['exp', 'user_id']})
            user_id = payload['user_id']
            if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
                raise jwt.InvalidTokenError('Invalid subject')
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        return handler(user_id, *args, **kwargs)
    return decorated
