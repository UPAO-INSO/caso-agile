from __future__ import annotations

from typing import Any, Mapping

import logging
from flask import jsonify


class ErrorHandler:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger

    def respond(self, message: str, status_code: int = 400, **extra: Any):
        payload = {'success': False, 'message': message}
        if extra:
            payload.update(extra)
        return jsonify(payload), status_code

    def log_and_respond(
        self,
        exc: Exception,
        log_message: str,
        response_message: str | None = None,
        status_code: int = 500,
        log_extra: Mapping[str, Any] | None = None,
        **response_extra: Any,
    ):
        context = dict(log_extra or {})
        context.setdefault('exception_type', type(exc).__name__)

        if self.logger:
            self.logger.exception(log_message, extra=context)

        return self.respond(response_message or log_message, status_code, **response_extra)
