import traceback


class BaseExceptionHandlerMixin:
    def handle_exception(self, e):
        try:
            raise e
        except:
            traceback.print_exc()
            if hasattr(e, "message"):
                error = e.message
            elif hasattr(e, "detail"):
                error = e.detail
            elif hasattr(e, "errors"):
                error = e.errors
            elif hasattr(e, "error"):
                error = e.error
            elif hasattr(e, "error_description"):
                error = e.error_description
            else:
                error = str(e)
            if hasattr(e, "status_code"):
                status_code = e.status_code
            elif hasattr(e, "code"):
                status_code = e.code
            elif hasattr(e, "status"):
                status_code = e.status
            else:
                status_code = 500
            print("status_code", status_code)
            if isinstance(error, dict) or isinstance(error, list):
                return self.format_response(errors=error, status_code=status_code)
            else:
                return self.format_response(errors={"error": error}, status_code=status_code)
