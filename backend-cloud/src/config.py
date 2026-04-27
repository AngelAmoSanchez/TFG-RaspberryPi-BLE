import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Conifuración centralizada para el backend de la aplicación"""

    # Aplicación
    app_name: str = "TFG Bluetooth Detection Backend"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    api_version: str = "v1"

    # Servidor
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Base de datos (PostgreSQL)
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/tfg_detections"
    )

    # MQTT Broker
    mqtt_enabled: bool = os.getenv("MQTT_ENABLED", "false").lower() == "true"
    mqtt_broker: Optional[str] = os.getenv("MQTT_BROKER")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "tfg/detections/raw")
    mqtt_username: Optional[str] = os.getenv("MQTT_USERNAME")
    mqtt_password: Optional[str] = os.getenv("MQTT_PASSWORD")

    # WebSocket
    websocket_enabled: bool = os.getenv("WEBSOCKET_ENABLED", "true").lower() == "true"

    # CORS
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://*.vercel.app",
    ]

    # Seguridad
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    api_key: Optional[str] = os.getenv("API_KEY")

    # Estadisticas
    devices_per_person: float = float(os.getenv("DEVICES_PER_PERSON", "1.5"))

    # Umbrales de zonas RSSI
    near_threshold: int = int(os.getenv("NEAR_THRESHOLD", "-60"))
    medium_threshold: int = int(os.getenv("MEDIUM_THRESHOLD", "-75"))
    # Logs
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Railway
    railway_environment: Optional[str] = os.getenv("RAILWAY_ENVIRONMENT")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_database_url_sync(self) -> str:
        """Devuelve la URL de la base de datos para conexiones síncronas"""
        return self.database_url.replace("+asyncpg", "")

    def is_production(self) -> bool:
        """Devuelve True si se está ejecutando en producción"""
        return self.environment == "production" or self.railway_environment == "production"


# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """Devuelve la instancia global de configuración"""
    return settings
