from ..error_translation import ERRORS, DEFAULT_ERROR_LANGUAGE


class LocalBaseException(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, exception_type: str = None, status_code=500, lang=DEFAULT_ERROR_LANGUAGE, exception=None, kwargs=None):
        if exception_type is None and exception is None:
            self.message = "either exception_type or exception must be provided"
        elif exception is not None:
            self.message = exception
        elif exception_type not in ERRORS.keys():
            self.message = "unknown exception type"
        else:
            error = ERRORS[exception_type]
            if lang not in error.keys():
                lang = DEFAULT_ERROR_LANGUAGE
            self.message = error[lang]
            if kwargs is not None:
                self.message = self.message.format(**kwargs)
        self.status_code = status_code
        super().__init__(self.message)
