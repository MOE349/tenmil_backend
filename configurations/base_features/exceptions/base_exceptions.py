import logging
from django.conf import settings
from rest_framework.response import Response
from ..error_translation import ERRORS, DEFAULT_ERROR_LANGUAGE

logger = logging.getLogger("django")

class LocalBaseException(Exception):
    """
    A base exception for the Tenmil platform.
    Supports translated messages, debug info, structured API responses, and logging.
    """

    def __init__(
        self,
        exception_type: str = None,
        status_code: int = 500,
        lang: str = DEFAULT_ERROR_LANGUAGE,
        exception: str = None,
        kwargs: dict = None,
        debug_message: str = None,
    ):
        self.status_code = int(status_code)
        self.code = exception_type or "custom_exception"
        self.kwargs = kwargs or {}
        self.debug_message = debug_message

        # Determine message
        if exception_type is None and exception is None:
            self.message = "Either exception_type or exception must be provided."
        elif exception:
            self.message = exception
        elif exception_type not in ERRORS:
            self.message = "Unknown exception type."
        else:
            error = ERRORS[exception_type]
            if lang not in error:
                lang = DEFAULT_ERROR_LANGUAGE
            try:
                self.message = error[lang].format(**self.kwargs)
            except Exception as e:
                self.message = f"Error formatting message: {str(e)}"

        super().__init__(self.message)

    def to_dict(self) -> dict:
        data = {
            "status": "error",
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "context": self.kwargs,
        }
        if settings.DEBUG and self.debug_message:
            data["debug"] = self.debug_message
        return data

    def get_response(self) -> Response:
        return Response(self.to_dict(), status=self.status_code)

    def log(self, level: str = "error"):
        log_msg = f"[{self.code}] {self.message}"
        if self.debug_message:
            log_msg += f" | Debug: {self.debug_message}"
        if level == "warning":
            logger.warning(log_msg)
        elif level == "info":
            logger.info(log_msg)
        else:
            logger.error(log_msg)

