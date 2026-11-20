"""Resolve application-scoped services at the HTTP boundary."""
from flask import current_app


def get_service(name):
    return current_app.extensions["promptly"][name]
