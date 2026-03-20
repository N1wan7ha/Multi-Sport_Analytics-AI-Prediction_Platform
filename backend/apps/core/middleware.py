"""Security middleware for hardened response headers."""


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self' ws: wss:; frame-ancestors 'none';"
        )
        response.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        response.setdefault('Cross-Origin-Embedder-Policy', 'require-corp')
        return response
