"""
NDA Shield — Custom Error Handlers
Returns consistent JSON for all API errors + HTML for browser requests.
"""
from django.http import JsonResponse


def api_404(request, exception=None):
    """Custom 404 handler — JSON for API, redirect hint for frontend."""
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "error": "Not Found",
                "message": f"The endpoint '{request.path}' does not exist.",
                "status": 404,
                "hint": "Check the API documentation at /api/docs/",
            },
            status=404,
        )
    # For non-API paths, return JSON that frontend can handle
    return JsonResponse(
        {"error": "Page not found", "status": 404},
        status=404,
    )


def api_500(request):
    """Custom 500 handler — generic error, no details leaked."""
    return JsonResponse(
        {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "status": 500,
        },
        status=500,
    )


def api_400(request, exception=None):
    """Custom 400 handler."""
    return JsonResponse(
        {
            "error": "Bad Request",
            "message": "The request was malformed or invalid.",
            "status": 400,
        },
        status=400,
    )


def api_403(request, exception=None):
    """Custom 403 handler."""
    return JsonResponse(
        {
            "error": "Forbidden",
            "message": "You do not have permission to access this resource.",
            "status": 403,
        },
        status=403,
    )
