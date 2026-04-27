import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MQTTConfig:
    """Configuración del cliente MQTT"""

    broker: str
    port: int
    topic: str
    username: Optional[str]
    password: Optional[str]
    max_buffer_size: int = 100

    @staticmethod
    def from_env() -> "MQTTConfig":
        """Carga configuración MQTT desde variables de entorno"""
        return MQTTConfig(
            broker=os.getenv("MQTT_BROKER", "broker.emqx.io"),
            port=int(os.getenv("MQTT_PORT", "1883")),
            topic=os.getenv("MQTT_TOPIC", "tfg/detections/raw"),
            username=os.getenv("MQTT_USERNAME"),
            password=os.getenv("MQTT_PASSWORD"),
            max_buffer_size=int(os.getenv("MQTT_BUFFER_SIZE", "100")),
        )


@dataclass
class HTTPConfig:
    """Configuración del cliente HTTP"""

    base_url: str
    api_key: Optional[str]
    timeout: int = 10

    @staticmethod
    def from_env() -> "HTTPConfig":
        """Carga configuración HTTP desde variables de entorno"""
        return HTTPConfig(
            base_url=os.getenv("HTTP_BASE_URL", "http://localhost:8000"),
            api_key=os.getenv("HTTP_API_KEY"),
            timeout=int(os.getenv("HTTP_TIMEOUT", "10")),
        )


@dataclass
class ScannerConfig:
    """Configuración del escáner BLE"""

    scan_duration: int = 10  # Duración de cada escaneo (segundos)
    scan_interval: int = 30  # Intervalo entre escaneos (segundos)
    near_threshold: int = -60  # RSSI para zona cercana
    medium_threshold: int = -75  # RSSI para zona media
    use_mock: bool = False  # Usar scanner mock (desarrollo)

    @staticmethod
    def from_env() -> "ScannerConfig":
        """Carga configuración del scanner desde variables de entorno"""
        return ScannerConfig(
            scan_duration=int(os.getenv("SCAN_DURATION", "10")),
            scan_interval=int(os.getenv("SCAN_INTERVAL", "30")),
            near_threshold=int(os.getenv("NEAR_THRESHOLD", "-60")),
            medium_threshold=int(os.getenv("MEDIUM_THRESHOLD", "-75")),
            use_mock=os.getenv("USE_MOCK_SCANNER", "false").lower() == "true",
        )


@dataclass
class AgentConfig:
    """Configuración general del agente IoT"""

    device_id: str
    communication_mode: str  # "mqtt" o "http"
    device_name: Optional[str] = None
    device_location: Optional[str] = None
    log_level: str = "INFO"
    mqtt: MQTTConfig = None
    http: HTTPConfig = None
    scanner: ScannerConfig = None
    
    @staticmethod
    def from_env() -> "AgentConfig":
        """Carga configuración completa desde variables de entorno"""
        device_id = os.getenv("DEVICE_ID")
        if not device_id:
            raise ValueError("Variable de entorno DEVICE_ID es necesaria")

        mode = os.getenv("COMMUNICATION_MODE", "mqtt").lower()
        if mode not in ["mqtt", "http"]:
            raise ValueError(f"Variable de entorno COMMUNICATION_MODE inválida: {mode}. Debe ser 'mqtt' o 'http'")

        return AgentConfig(
            device_id=device_id,
            device_name=os.getenv("DEVICE_NAME"),
            device_location=os.getenv("DEVICE_LOCATION"),
            communication_mode=mode,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            mqtt=MQTTConfig.from_env() if mode == "mqtt" else None,
            http=HTTPConfig.from_env() if mode == "http" else None,
            scanner=ScannerConfig.from_env(),
        )


    def validate(self):
        """
        Valida que la configuración es correcta

        Raises:
            ValueError: Si la configuración es inválida
        """
        # Validar device_id
        if not self.device_id or len(self.device_id) < 3:
            raise ValueError("Variable de entorno DEVICE_ID debe tener al menos 3 caracteres")

        # Validar log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            raise ValueError(f"Variable de entorno LOG_LEVEL inválida. Debe ser una de {valid_levels}")

        # Validar configuración según modo
        if self.communication_mode == "mqtt":
            if not self.mqtt:
                raise ValueError("MQTT config required when mode is 'mqtt'")
            if not self.mqtt.broker:
                raise ValueError("Variable de entorno MQTT_BROKER es necesaria")
            if not self.mqtt.topic:
                raise ValueError("Variable de entorno MQTT_TOPIC es necesaria")

        elif self.communication_mode == "http":
            if not self.http:
                raise ValueError("HTTP config required when mode is 'http'")
            if not self.http.base_url:
                raise ValueError("Variable de entorno HTTP_BASE_URL es necesaria")

        # Validar scanner
        if not self.scanner:
            raise ValueError("Scanner config is required")

        if self.scanner.scan_duration < 1 or self.scanner.scan_duration > 60:
            raise ValueError("Variable de entorno SCAN_DURATION inválida. Debe ser entre 1 y 60 segundos")

        if self.scanner.scan_interval < 5:
            raise ValueError("Variable de entorno SCAN_INTERVAL inválida. Debe ser al menos 5 segundos")

        if self.scanner.near_threshold >= 0:
            raise ValueError("Variable de entorno NEAR_THRESHOLD inválida. Debe ser un valor negativo (RSSI en dBm)")

        if self.scanner.medium_threshold >= self.scanner.near_threshold:
            raise ValueError("Variable de entorno MEDIUM_THRESHOLD inválida. Debe ser menor que NEAR_THRESHOLD")

    def __str__(self) -> str:
        """Representación legible de la configuración"""
        mqtt_info = ""
        if self.mqtt:
            mqtt_info = f"\n  MQTT: {self.mqtt.broker}:{self.mqtt.port} → {self.mqtt.topic}"

        http_info = ""
        if self.http:
            http_info = f"\n  HTTP: {self.http.base_url}"

        return (
            f"Configuración del Agente:\n"
            f"  ID del dispositivo: {self.device_id}\n"
            f"  Nombre: {self.device_name or 'Not set'}\n"
            f"  Ubicación: {self.device_location or 'Not set'}\n"
            f"  Modo: {self.communication_mode}\n"
            f"  Nivel de registro: {self.log_level}"
            f"{mqtt_info}"
            f"{http_info}\n"
            f"  Escaneo: escanea {self.scanner.scan_duration}s cada {self.scanner.scan_interval}s\n"
            f"  Zonas: NEAR ≥ {self.scanner.near_threshold} dBm, "
            f"MEDIUM ≥ {self.scanner.medium_threshold} dBm"
        )


def load_config_from_file(filepath: str = ".env") -> AgentConfig:
    """
    Carga configuración desde archivo .env

    Args:
        filepath: Ruta al archivo .env

    Devuelve:
        Configuración del agente
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(filepath)
    except ImportError:
        # Si python-dotenv no está instalado, intentar cargar sin él
        pass

    config = AgentConfig.from_env()
    config.validate()

    return config
