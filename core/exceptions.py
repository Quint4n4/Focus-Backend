from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    # Handle django-ratelimit Ratelimited exception
    try:
        from django_ratelimit.exceptions import Ratelimited
        if isinstance(exc, Ratelimited):
            return Response(
                {
                    'error': True,
                    'status_code': 429,
                    'detail': 'Demasiadas solicitudes. Intenta de nuevo más tarde.',
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
    except ImportError:
        pass

    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'error': True,
            'status_code': response.status_code,
            'detail': response.data,
        }

    return response
