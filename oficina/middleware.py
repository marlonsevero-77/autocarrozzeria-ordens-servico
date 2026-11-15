"""Middleware de segurança complementar."""

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "font-src 'self'",
        "img-src 'self' data:",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
    ]
)


class ContentSecurityPolicyMiddleware:
    """Adiciona o cabeçalho Content-Security-Policy (proteção contra XSS, RNF02).

    Só permite scripts, estilos e fontes do próprio domínio e bloqueia
    scripts embutidos na página.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # O Django Admin usa estilos e scripts próprios servidos do mesmo domínio,
        # então a mesma política vale para todo o sistema.
        response.headers.setdefault("Content-Security-Policy", CSP)
        return response
