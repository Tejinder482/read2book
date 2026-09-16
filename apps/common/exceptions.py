from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
            response.data = {
                "error": True,
                "detail": detail["detail"],
                "code": getattr(exc, "default_code", "error"),
            }
        else:
            response.data = {
                "error": True,
                "detail": detail,
                "code": getattr(exc, "default_code", "error"),
            }
    return response
