"""Account validation also rejects MongoDB operator objects."""
import re


def valid_email(value):
    return isinstance(value, str) and len(value) <= 254 and bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value))


def valid_password(value):
    return isinstance(value, str) and 12 <= len(value) <= 128


def valid_code(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9]{6}', value))
