from types import SimpleNamespace

from backend.config_validation import validate_runtime_settings


def settings(**overrides):
    values = {
        "app_env": "production",
        "jwt_secret": "dev-only-change-me-in-production",
        "mongodb_uri": "mongodb://localhost:27017",
        "redis_host": "localhost",
        "frontend_origin": "http://localhost:5173",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_production_defaults_are_rejected():
    errors = validate_runtime_settings(settings())

    assert "JWT_SECRET must be set to a strong value in production" in errors
    assert "MONGODB_URI must not point to localhost in production" in errors
    assert "REDIS_HOST must not be localhost in production" in errors
    assert "FRONTEND_ORIGIN must be an https URL in production" in errors


def test_valid_production_settings_pass():
    errors = validate_runtime_settings(
        settings(
            jwt_secret="strong-random-secret",
            mongodb_uri="mongodb://mongo:27017",
            redis_host="redis",
            frontend_origin="https://app.example.com",
        )
    )

    assert errors == []


def test_unknown_environment_is_rejected():
    errors = validate_runtime_settings(settings(app_env="staging"))

    assert errors == ["APP_ENV must be development, testing, or production"]


def test_example_jwt_placeholder_is_rejected():
    errors = validate_runtime_settings(
        settings(
            jwt_secret="replace-with-a-random-secret",
            mongodb_uri="mongodb://mongo:27017",
            redis_host="redis",
            frontend_origin="https://app.example.com",
        )
    )

    assert errors == ["JWT_SECRET must be set to a strong value in production"]
