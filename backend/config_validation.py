from urllib.parse import urlparse

DEFAULT_JWT_SECRET = "dev-only-change-me-in-production"
EXAMPLE_JWT_SECRET = "replace-with-a-random-secret"
DEFAULT_LIVEKIT_API_KEY = "devkey"
DEFAULT_LIVEKIT_API_SECRET = "secret"
DEFAULT_LIVEKIT_URL = "http://localhost:7880"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_runtime_settings(settings) -> list[str]:
    errors = []

    if settings.app_env not in {"development", "testing", "production"}:
        errors.append("APP_ENV must be development, testing, or production")

    if settings.app_env == "production":
        if not settings.jwt_secret or settings.jwt_secret in {
            DEFAULT_JWT_SECRET,
            EXAMPLE_JWT_SECRET,
        }:
            errors.append("JWT_SECRET must be set to a strong value in production")
        if not settings.mongodb_uri or settings.mongodb_uri.startswith("mongodb://localhost"):
            errors.append("MONGODB_URI must not point to localhost in production")
        if settings.redis_host == "localhost":
            errors.append("REDIS_HOST must not be localhost in production")
        if not settings.frontend_origin or not settings.frontend_origin.startswith("https://"):
            errors.append("FRONTEND_ORIGIN must be an https URL in production")
        if (
            not settings.livekit_api_key
            or settings.livekit_api_key == DEFAULT_LIVEKIT_API_KEY
        ):
            errors.append(
                "LIVEKIT_API_KEY must be set to a non-default value in production"
            )
        if (
            not settings.livekit_api_secret
            or settings.livekit_api_secret == DEFAULT_LIVEKIT_API_SECRET
        ):
            errors.append(
                "LIVEKIT_API_SECRET must be set to a non-default "
                "value in production"
            )
        livekit_url = settings.livekit_url or ""
        if (
            urlparse(livekit_url).hostname in LOCAL_HOSTS
            or livekit_url == DEFAULT_LIVEKIT_URL
        ):
            errors.append("LIVEKIT_URL must not point to localhost in production")

    return errors
