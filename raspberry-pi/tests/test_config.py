import os
from unittest.mock import patch

import pytest

from src.config import (
    AgentConfig,
    HTTPConfig,
    MQTTConfig,
    ScannerConfig,
    load_config_from_file,
)


def test_mqtt_config_from_env_defaults(monkeypatch):
    """Valida los valores por defecto de MQTT."""
    monkeypatch.delenv("MQTT_BROKER", raising=False)
    config = MQTTConfig.from_env()
    assert config.broker == "broker.emqx.io"


def test_agent_config_validation_no_device_id(monkeypatch):
    """Valida si el DEVICE_ID no definido."""
    monkeypatch.delenv("DEVICE_ID", raising=False)
    with pytest.raises(ValueError, match="DEVICE_ID es necesaria"):
        AgentConfig.from_env()


def test_agent_config_validation_invalid_mode(monkeypatch):
    """Valida que el modo de comunicación no soportado lanza ValueError."""
    monkeypatch.setenv("DEVICE_ID", "RPI01")
    monkeypatch.setenv("COMMUNICATION_MODE", "ftp")
    with pytest.raises(ValueError, match="COMMUNICATION_MODE inválida"):
        AgentConfig.from_env()


def test_config_validate_method_errors():
    """Valida la lógica de validación manual."""

    conf = AgentConfig(device_id="12", communication_mode="mqtt")
    with pytest.raises(ValueError, match="al menos 3 caracteres"):
        conf.validate()

    conf = AgentConfig(
        device_id="RPI01",
        communication_mode="http",
        http=HTTPConfig(base_url="http://localhost:8000", api_key=None),
        scanner=ScannerConfig(scan_duration=70),
    )
    with pytest.raises(ValueError, match="SCAN_DURATION inválida"):
        conf.validate()

    conf.scanner = ScannerConfig(near_threshold=10)
    with pytest.raises(ValueError, match="NEAR_THRESHOLD inválida"):
        conf.validate()

    conf.scanner = ScannerConfig(near_threshold=-60, medium_threshold=-50)
    with pytest.raises(ValueError, match="menor que NEAR_THRESHOLD"):
        conf.validate()


def test_http_config_from_env_defaults(monkeypatch):
    """Valida los valores por defecto de HTTP desde el entorno."""
    monkeypatch.delenv("HTTP_BASE_URL", raising=False)
    config = HTTPConfig.from_env()
    assert config.base_url == "http://localhost:8000"
    assert config.timeout == 10


def test_scanner_config_from_env_defaults(monkeypatch):
    """Valida los valores por defecto del Scanner."""
    monkeypatch.setenv("USE_MOCK_SCANNER", "true")
    config = ScannerConfig.from_env()
    assert config.use_mock is True
    assert config.scan_duration == 10


def test_agent_config_log_level_upper(monkeypatch):
    """Valida que el LOG_LEVEL se convierte a mayúsculas."""
    monkeypatch.setenv("DEVICE_ID", "RPI-01")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    config = AgentConfig.from_env()
    assert config.log_level == "DEBUG"


def test_validate_log_level_error():
    """Valida el error por nivel de log inválido."""
    conf = AgentConfig(device_id="RPI01", communication_mode="mqtt", log_level="VERBOSE")
    with pytest.raises(ValueError, match="LOG_LEVEL inválida"):
        conf.validate()


def test_validate_mqtt_missing_fields():
    """Valida los errores por configuración MQTT incompleta."""
    # Modo MQTT activo pero objeto mqtt es None
    conf = AgentConfig(device_id="RPI01", communication_mode="mqtt", mqtt=None)
    with pytest.raises(
        ValueError, match="Configuración de MQTT es necesaria cuando el modo es 'mqtt"
    ):
        conf.validate()

    # Falta el broker
    conf.mqtt = MQTTConfig(broker="", port=1883, topic="test", username=None, password=None)
    with pytest.raises(ValueError, match="MQTT_BROKER es necesaria"):
        conf.validate()

    # Falta el topic
    conf.mqtt.broker = "localhost"
    conf.mqtt.topic = ""
    with pytest.raises(ValueError, match="MQTT_TOPIC es necesaria"):
        conf.validate()


def test_validate_http_missing_config():
    """Valida los errores por configuración HTTP incompleta."""
    # Modo HTTP activo pero objeto http es None
    conf = AgentConfig(device_id="RPI01", communication_mode="http", http=None)
    with pytest.raises(
        ValueError, match="Configuración de HTTP es necesaria cuando el modo es 'http'"
    ):
        conf.validate()

    # Falta base_url
    conf.http = HTTPConfig(base_url="", api_key=None)
    with pytest.raises(ValueError, match="HTTP_BASE_URL es necesaria"):
        conf.validate()


def test_validate_scanner_missing_and_interval(monkeypatch):
    """Valida la existencia del scanner e intervalo."""
    conf = AgentConfig(
        device_id="RPI01",
        communication_mode="mqtt",
        mqtt=MQTTConfig("localhost", 1883, "t", None, None),
    )

    conf.scanner = None
    with pytest.raises(ValueError, match="Configuración del scanner es necesaria"):
        conf.validate()

    # Intervalo menor a 5 segundos
    conf.scanner = ScannerConfig(scan_interval=2)
    with pytest.raises(ValueError, match="SCAN_INTERVAL inválida"):
        conf.validate()


def test_agent_config_str_representation():
    """Valida el método __str__ para ambos modos de comunicación."""
    # Caso MQTT
    conf_mqtt = AgentConfig(
        device_id="RPI01",
        communication_mode="mqtt",
        mqtt=MQTTConfig("broker.test", 1883, "topic/test", None, None),
        scanner=ScannerConfig(),
    )
    res_mqtt = str(conf_mqtt)
    assert "MQTT: broker.test:1883 → topic/test" in res_mqtt
    assert "Not set" in res_mqtt  # Para nombre/ubicación no definidos

    # Caso HTTP
    conf_http = AgentConfig(
        device_id="RPI02",
        communication_mode="http",
        http=HTTPConfig("http://api.test", None),
        scanner=ScannerConfig(),
    )
    res_http = str(conf_http)
    assert "HTTP: http://api.test" in res_http


def test_load_config_from_file_integration(tmp_path):
    """Valida la carga completa simulando el entorno del sistema."""

    # Crea el archivo temporal .env
    d = tmp_path / "subdir"
    d.mkdir()
    env_file = d / ".env"
    env_file.write_text("DEVICE_ID=FILE-ID\nCOMMUNICATION_MODE=mqtt\nMQTT_BROKER=file.broker")

    with patch("dotenv.load_dotenv"), patch.dict(
        os.environ,
        {
            "DEVICE_ID": "FILE-ID",
            "COMMUNICATION_MODE": "mqtt",
            "MQTT_BROKER": "file.broker",
            "MQTT_TOPIC": "tfg/test",
        },
    ):
        config = load_config_from_file(str(env_file))

        assert config.device_id == "FILE-ID"
        assert config.communication_mode == "mqtt"
        assert config.mqtt.broker == "file.broker"
