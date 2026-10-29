from typing import Any


class BackendError(Exception):
    def __init__(self, code: str, message: str, status: int = 502, retryable: bool = False):
        super().__init__(message)
        self.code, self.message, self.status, self.retryable = code, message, status, retryable


def error_body(error: BackendError, request_id: str, details: Any = None) -> dict:
    return {"error": {"code": error.code, "message": error.message,
                      "retryable": error.retryable, "details": details}, "request_id": request_id}
