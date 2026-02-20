"""
NDA Shield — Custom DRF Exception Handler
Returns consistent, clean JSON error responses for all API errors.
"""
import logging
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Consistent JSON error format:
    {
        "error": "Error Type",
        "message": "Human-readable description",
        "details": {...}  // only for validation errors
        "status": 400
    }
    """
    response = exception_handler(exc, context)

    if isinstance(exc, Http404):
        return Response(
            {"error": "Not Found", "message": "The requested resource does not exist.", "status": 404},
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, exceptions.ValidationError):
        details = exc.detail
        # Flatten single-field errors
        if isinstance(details, dict):
            messages = []
            for field, errs in details.items():
                if isinstance(errs, list):
                    for e in errs:
                        messages.append(f"{field}: {e}")
                else:
                    messages.append(f"{field}: {errs}")
            msg = "; ".join(messages)
        elif isinstance(details, list):
            msg = "; ".join(str(d) for d in details)
        else:
            msg = str(details)

        return Response(
            {"error": "Validation Error", "message": msg, "details": details, "status": 400},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, exceptions.AuthenticationFailed):
        return Response(
            {"error": "Authentication Failed", "message": str(exc.detail), "status": 401},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, exceptions.NotAuthenticated):
        return Response(
            {"error": "Not Authenticated", "message": "Authentication credentials were not provided.", "status": 401},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, exceptions.PermissionDenied):
        return Response(
            {"error": "Permission Denied", "message": str(exc.detail), "status": 403},
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, exceptions.Throttled):
        return Response(
            {
                "error": "Rate Limited",
                "message": f"Too many requests. Try again in {exc.wait:.0f} seconds.",
                "retry_after": int(exc.wait) if exc.wait else 60,
                "status": 429,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(int(exc.wait) if exc.wait else 60)},
        )

    if isinstance(exc, exceptions.MethodNotAllowed):
        return Response(
            {"error": "Method Not Allowed", "message": str(exc.detail), "status": 405},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    if response is not None:
        data = {
            "error": type(exc).__name__,
            "message": str(exc.detail) if hasattr(exc, "detail") else "An error occurred.",
            "status": response.status_code,
        }
        response.data = data
        return response

    # Unhandled exceptions — log and return 500
    logger.exception(f"Unhandled exception: {exc}")
    return Response(
        {"error": "Internal Server Error", "message": "An unexpected error occurred.", "status": 500},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
