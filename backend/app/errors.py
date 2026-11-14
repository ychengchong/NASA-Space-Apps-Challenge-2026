"""Errors with the codes and HTTP statuses of spec section 10.

The tool layer raises these; the adapters map them to their own error shape.
A record that is too short, or a place with no data, is a normal result and not an error.
"""

from typing import ClassVar

from pydantic import ValidationError


class AppError(Exception):
    code: ClassVar[str] = "bad_request"
    http_status: ClassVar[int] = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnknownVariableError(AppError):
    code = "unknown_variable"
    http_status = 400


class BadPlaceError(AppError):
    code = "bad_place"
    http_status = 400


class BadPeriodError(AppError):
    code = "bad_period"
    http_status = 400


class UnsupportedRequestError(AppError):
    """Spec 10: a valid request the app does not support, such as a world mean of snow."""

    code = "unsupported_request"
    http_status = 422


class BadRequestError(AppError):
    code = "bad_request"
    http_status = 400


class RateLimitedError(AppError):
    code = "rate_limited"
    http_status = 429


class SourceUnavailableError(AppError):
    code = "source_unavailable"
    http_status = 502


class AiUnavailableError(AppError):
    code = "ai_unavailable"
    http_status = 503


def first_problem(error: ValidationError) -> str:
    """The first problem's field path and rule, without the rejected value.

    The adapters put it in their plain message for input that does not validate, in place of
    pydantic's own text, which holds the model's name, the rejected value and a link (spec 10).
    """
    problem = error.errors()[0]
    location = ".".join(str(part) for part in problem["loc"])
    return f"{location}: {problem['msg']}" if location else problem["msg"]
