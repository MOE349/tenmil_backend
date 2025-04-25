from rest_framework import status
from rest_framework.response import Response


class ResponseFormatterMixin(object):
    """
        A mixin for Django REST Framework API views that provides a response formatter
        method for handling data, errors, and status codes.
    """

    def format_response(self, data=None, errors=None, status_code=None, fields=None):
        """
            Formats a response based on success, data, errors, and status code.

            Handles scenarios where both data and errors are provided,
            indicating potentially partial success.

            Args:
                data (Optional[List or Dict]): Data to include in the response.
                    - List: When applicable, suitable for multiple responses (e.g., bulk operations).
                    - Dict: Used for a single response or a structured response.
                errors (Optional[List or Dict]): Errors to include in the response.
                    - List: Used for a list of errors, possibly related to multiple operations.
                    - Dict: Suitable for a single error or a more detailed error object.
                status (int, optional): The HTTP status code to use.

            Returns:
                rest_framework.response.Response: The formatted response object.
        """

        if data and errors:
            # Partial success: some data processed with errors
            response_data, status_code = self.handle_complixe_data(data, errors, status_code)
        elif not errors and not data:
            response_data, status_code = self.handle_null_response()
        elif data:
            # Successful operation with data and status code (no errors)
            response_data, status_code = self.handle_data(data, status_code)
        else:
            # Handle errors and use appropriate status code
            response_data, status_code = self.handle_errors(errors, status_code)
        resonse_meta_data = {}
        resonse_meta_data['success'] = False if errors else True
        total = 0
        if data:
            if isinstance(data, list):
                total = len(data)
            else:
                total = 1
        resonse_meta_data['total'] = total
        resonse_meta_data['status_code'] = status_code
        response_data['meta_data'] = resonse_meta_data
        if fields:
            response_data['fields'] = fields
        return Response(response_data, status=status_code)

    def handle_complixe_data(self, data, errors, status_code=None):
        status_code = status_code or status.HTTP_207_MULTI_STATUS
        response_data = {"data": data, "errors": errors}
        return response_data, status_code

    def handle_null_response(self, status_code=None):
        status_code = status_code or status.HTTP_200_OK
        response_data = {"data": [], "errors": []}
        return response_data, status_code

    def handle_data(self, data, status_code=None):
        status_code = status_code or status.HTTP_200_OK
        response_data = {"data": data}
        return response_data, status_code

    def handle_errors(self, errors, status_code=None):
        status_code = status_code or status.HTTP_500_INTERNAL_SERVER_ERROR
        if not errors:
            errors = {"message": "Internal server error"}
        response_data = {"errors": errors}
        return response_data, status_code
