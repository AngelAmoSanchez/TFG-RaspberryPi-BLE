import pytest

from src.config import Settings, get_settings

pytestmark = pytest.mark.unit


class TestSettingsDefaults:
    """Tests para valores por defecto de Settings."""

    def test_default_environment(self):
        """Environment por defecto es development."""
        settings = Settings()
        assert settings.environment == "development"

    def test_default_debug(self):
        """Debug por defecto es True."""
        settings = Settings()
        assert settings.debug is True

    def test_default_mqtt_enabled(self):
        """MQTT deshabilitado por defecto."""
        settings = Settings()
        assert settings.mqtt_enabled is False

    def test_default_websocket_enabled(self):
        """WebSocket habilitado por defecto."""
        settings = Settings()
        assert settings.websocket_enabled is True

    def test_default_thresholds(self):
        """Valores por defecto de umbrales RSSI."""
        settings = Settings()
        assert settings.near_threshold == -60
        assert settings.medium_threshold == -75

    def test_default_devices_per_person(self):
        """Ratio por defecto dispositivos/persona."""
        settings = Settings()
        assert settings.devices_per_person == 1.5

    def test_is_production_logic(self):
        """Prueba todas las ramas del método is_production."""

        # Desarrollo
        config_dev = Settings(environment="development")
        assert config_dev.is_production() is False

        # Producción por env
        config_prod = Settings(environment="production")
        assert config_prod.is_production() is True

    def test_get_settings_utility(self):
        """Valida que get_settings devuelva la instancia global."""

        settings_inst = get_settings()
        assert isinstance(settings_inst, Settings)
        # Validar que son la misma instancia
        assert settings_inst is get_settings()


class TestSettingsFromEnvironment:
    """Tests para cargar configuración desde variables de entorno."""

    def test_environment_from_env(self, monkeypatch):
        """Cargar environment desde ENV."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.environment == "production"

    def test_debug_from_env_false(self, monkeypatch):
        """Cargar debug=false desde ENV."""
        monkeypatch.setenv("DEBUG", "false")
        settings = Settings()
        assert settings.debug is False

    def test_debug_from_env_true(self, monkeypatch):
        """Cargar debug=true desde ENV."""
        monkeypatch.setenv("DEBUG", "true")
        settings = Settings()
        assert settings.debug is True

    def test_mqtt_enabled_from_env(self, monkeypatch):
        """Cargar mqtt_enabled desde ENV."""
        monkeypatch.setenv("MQTT_ENABLED", "true")
        settings = Settings()
        assert settings.mqtt_enabled is True

    def test_thresholds_from_env(self, monkeypatch):
        """Cargar umbrales desde ENV."""
        monkeypatch.setenv("NEAR_THRESHOLD", "-55")
        monkeypatch.setenv("MEDIUM_THRESHOLD", "-70")

        settings = Settings()
        assert settings.near_threshold == -55
        assert settings.medium_threshold == -70

    def test_database_url_from_env(self, monkeypatch):
        """Cargar DATABASE_URL desde ENV."""
        test_url = "postgresql+asyncpg://user:pass@localhost/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)

        settings = Settings()
        assert settings.database_url == test_url


class TestGetDatabaseUrlSync:
    """Tests para conversión de URL async a sync."""

    def test_convert_asyncpg_to_sync(self):
        """Convertir postgresql+asyncpg a postgresql."""
        settings = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")

        sync_url = settings.get_database_url_sync()

        assert sync_url == "postgresql://user:pass@localhost/db"
        assert "+asyncpg" not in sync_url

    def test_already_sync_url(self):
        """URL ya es sync, no cambia."""
        settings = Settings(database_url="postgresql://user:pass@localhost/db")

        sync_url = settings.get_database_url_sync()

        assert sync_url == "postgresql://user:pass@localhost/db"

    def test_sqlite_url_unchanged(self):
        """URL SQLite no cambia."""
        settings = Settings(database_url="sqlite:///./test.db")

        sync_url = settings.get_database_url_sync()

        assert sync_url == "sqlite:///./test.db"

    def test_complex_url_with_params(self):
        """URL con parámetros se convierte correctamente."""
        settings = Settings(database_url="postgresql+asyncpg://user:pass@host:5432/db?ssl=true")

        sync_url = settings.get_database_url_sync()

        assert sync_url == "postgresql://user:pass@host:5432/db?ssl=true"
        assert "+asyncpg" not in sync_url


class TestCorsOrigins:
    """Tests para configuración de CORS."""

    def test_cors_origins_parsing(self):
        """Parsear CORS origins como lista."""
        settings = Settings(cors_origins=["http://localhost:3000", "https://app.com"])

        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) == 2
        assert settings.cors_origins == ["http://localhost:3000", "https://app.com"]

    def test_cors_origins_empty_list(self):
        """CORS origins lista vacía."""
        settings = Settings(cors_origins=[])
        assert settings.cors_origins == []

    def test_cors_origins_single_item(self):
        """CORS origins con un solo item."""
        settings = Settings(cors_origins=["http://localhost:3000"])

        assert len(settings.cors_origins) == 1

    def test_cors_origins_wildcard(self):
        """CORS origins con wildcard."""
        settings = Settings(cors_origins=["*"])

        assert settings.cors_origins == ["*"]


class TestSettingsValidation:
    """Tests para validación de configuración."""

    def test_threshold_order_valid(self):
        """Umbrales en orden correcto."""
        settings = Settings(near_threshold=-60, medium_threshold=-75)

        assert settings.near_threshold > settings.medium_threshold

    def test_threshold_order_invalid(self):
        """Detectar orden incorrecto de umbrales."""
        settings = Settings(near_threshold=-90, medium_threshold=-75)

        assert settings.near_threshold == -90
        assert settings.medium_threshold == -75

    def test_negative_threshold_values(self):
        """Umbrales son valores negativos."""
        settings = Settings()

        assert settings.near_threshold < 0
        assert settings.medium_threshold < 0

    def test_devices_per_person_positive(self):
        """Devices per person debe ser positivo."""
        settings = Settings(devices_per_person=1.5)
        assert settings.devices_per_person > 0


class TestSecretKeys:
    """Tests para claves secretas."""

    def test_secret_key_default(self):
        """Secret key tiene valor por defecto."""
        settings = Settings()
        assert settings.secret_key is not None
        assert len(settings.secret_key) > 0

    def test_api_key_default(self):
        """API key tiene valor por defecto."""
        settings = Settings()
        assert settings.api_key is not None
        assert len(settings.api_key) > 0

    def test_secret_key_from_env(self, monkeypatch):
        """Cargar secret key desde ENV."""
        monkeypatch.setenv("SECRET_KEY", "custom-secret-123")
        settings = Settings()
        assert settings.secret_key == "custom-secret-123"

    def test_api_key_from_env(self, monkeypatch):
        """Cargar API key desde ENV."""
        monkeypatch.setenv("API_KEY", "custom-api-456")
        settings = Settings()
        assert settings.api_key == "custom-api-456"


class TestLogLevel:
    """Tests para nivel de log."""

    def test_log_level_default(self):
        """Log level por defecto."""
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_log_level_from_env(self, monkeypatch):
        """Cargar log level desde ENV."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_log_level_valid_values(self, monkeypatch):
        """Probar diferentes niveles de log."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            monkeypatch.setenv("LOG_LEVEL", level)
            settings = Settings()
            assert settings.log_level == level


class TestCompleteConfiguration:
    """Tests para configuración completa del sistema."""

    def test_production_configuration(self, monkeypatch):
        """Configuración típica de producción."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("MQTT_ENABLED", "true")
        monkeypatch.setenv("WEBSOCKET_ENABLED", "true")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        settings = Settings()

        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.mqtt_enabled is True
        assert settings.websocket_enabled is True
        assert settings.log_level == "WARNING"

    def test_development_configuration(self):
        """Configuración típica de desarrollo."""
        settings = Settings()

        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.mqtt_enabled is False
        assert settings.log_level == "INFO"

    def test_test_configuration(self, monkeypatch):
        """Configuración típica de testing."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("MQTT_ENABLED", "false")
        monkeypatch.setenv("WEBSOCKET_ENABLED", "false")

        settings = Settings()

        assert settings.environment == "test"
        assert settings.debug is True
        assert settings.mqtt_enabled is False
        assert settings.websocket_enabled is False
