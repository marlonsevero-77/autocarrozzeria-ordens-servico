"""
Configurações do projeto AutoCarrozzeria Di Girolamo – Ordens de Serviço.

Todas as informações sensíveis (chave secreta, banco de dados, hosts) vêm de
variáveis de ambiente. Nenhum segredo fica no código ou no repositório.
Veja o arquivo .env.example para a lista completa.
"""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _carregar_env(caminho: Path) -> None:
    """Carrega um arquivo .env simples (CHAVE=valor) apenas no desenvolvimento."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(BASE_DIR / ".env")


def _bool(nome: str, padrao: bool = False) -> bool:
    return os.environ.get(nome, str(padrao)).strip().lower() in {"1", "true", "sim", "yes"}


def _lista(nome: str, padrao: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(nome, padrao).split(",") if item.strip()]


def _banco_a_partir_da_url(url: str) -> dict:
    """Converte DATABASE_URL (ex.: fornecida pelo Neon) para o formato do Django."""
    partes = urlparse(url)
    if partes.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL deve usar o esquema postgres:// ou postgresql://")
    # Parâmetros como sslmode=require (enviados pelo Neon) são repassados ao psycopg.
    opcoes = {chave: valores[-1] for chave, valores in parse_qs(partes.query).items()}
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(partes.path.lstrip("/")),
        "USER": unquote(partes.username or ""),
        "PASSWORD": unquote(partes.password or ""),
        "HOST": partes.hostname or "",
        "PORT": str(partes.port or ""),
        "OPTIONS": opcoes,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


# --- Segurança básica -------------------------------------------------------

DEBUG = _bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "chave-apenas-para-desenvolvimento-local-nao-usar-em-producao"
    else:
        raise ImproperlyConfigured("Defina a variável de ambiente SECRET_KEY.")

ALLOWED_HOSTS = _lista("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _lista("CSRF_TRUSTED_ORIGINS")

# O Render define RENDER_EXTERNAL_HOSTNAME automaticamente.
_host_render = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _host_render:
    ALLOWED_HOSTS.append(_host_render)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_host_render}")


# --- Aplicações -------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "oficina",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "oficina.middleware.ContentSecurityPolicyMiddleware",
    # O django-axes deve ser o último middleware.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Banco de dados (PostgreSQL) -------------------------------------------
# Local: PostgreSQL instalado na máquina. Produção: PostgreSQL gerenciado no Neon.

_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    DATABASES = {"default": _banco_a_partir_da_url(_database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "oficina"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Autenticação (RNF01) ----------------------------------------------------
# Senhas: PBKDF2 com SHA-256, salt e iterações padrão do Django 5.2 (hasher nativo).

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "oficina:painel"
LOGOUT_REDIRECT_URL = "login"

# Bloqueio após 5 falhas seguidas por 15 minutos (django-axes).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "registration/bloqueado.html"

# Sessão de 8 horas (uma jornada de trabalho).
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True


# --- Configurações de produção (RNF02) -------------------------------------

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 60 * 60 * 24 * 30))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

SILENCED_SYSTEM_CHECKS = [
    # Não pedimos inclusão na lista de preload de HSTS dos navegadores.
    "security.W021",
]


# --- Internacionalização ----------------------------------------------------

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True


# --- Arquivos estáticos (WhiteNoise) ----------------------------------------
# Bootstrap e Bootstrap Icons são servidos localmente, sem depender de CDN.

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# --- Registro de erros sem detalhes técnicos para o usuário ----------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
