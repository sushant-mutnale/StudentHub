DEFAULT_JWT_SECRET = "dev-only-change-me-in-production"
EXAMPLE_JWT_SECRET = "replace-with-a-random-secret"


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

    return errors
