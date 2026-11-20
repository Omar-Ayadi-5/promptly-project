"""Errors shared between request validation and application services."""


class RequestValidationError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class ModelNotFoundError(LookupError):
    pass
