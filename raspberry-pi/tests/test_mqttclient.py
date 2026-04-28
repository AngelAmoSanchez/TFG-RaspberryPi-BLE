import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import src.sender.mqtt_client as mqtt_mod
from src.scanner.detection import Device, Zone
from src.sender.mqtt_client import MockMQTTClient, MQTTClient


@pytest.fixture
def mqtt_client():
    return MQTTClient(
        broker="localhost", port=1883, topic="test/topic", device_id="RPI_01", max_buffer_size=5
    )


def test_mqtt_buffer_logic(mqtt_client):
    """Valida que los mensajes se guardan si no hay conexión."""
    det = Device(device_hash="h" * 64, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())

    # Intentar publicar sin estar conectado
    mqtt_client.publish_detections([det])

    assert mqtt_client.get_buffer_size() == 1
    assert mqtt_client.is_connected() is False


def test_mqtt_buffer_overflow(mqtt_client):
    """Valida que se descarte el mensaje más antiguo cuando el buffer está lleno."""
    mqtt_client.max_buffer_size = 2

    mqtt_client._buffer_message({"id": 1})
    mqtt_client._buffer_message({"id": 2})
    mqtt_client._buffer_message({"id": 3})  # Debería sacar el id: 1

    assert mqtt_client.get_buffer_size() == 2
    assert mqtt_client._buffer[0]["id"] == 2


@patch("paho.mqtt.client.Client")
def test_mqtt_connect_fail(mock_paho, mqtt_client):
    """Valida el comportamiento cuando la conexión inicial falla."""
    mock_paho.return_value.connect.side_effect = Exception("Auth fail")
    assert mqtt_client.connect() is False


def test_mqtt_on_connect_callback(mqtt_client):
    """Valida las diferentes ramas del callback on_connect."""
    # Éxito
    mqtt_client._on_connect(None, None, None, 0)
    assert mqtt_client.is_connected() is True

    # Error (ej: rc=5, No autorizado)
    mqtt_client._on_connect(None, None, None, 5)
    assert mqtt_client.is_connected() is False


def test_mqtt_on_connect_success(mqtt_client):
    """Valida rama exitosa (rc == 0)."""
    mqtt_client._on_connect(None, None, None, 0)
    assert mqtt_client.is_connected() is True


def test_mqtt_on_connect_fail(mqtt_client):
    """Valida rama fallida (rc != 0)."""
    mqtt_client._on_connect(None, None, None, 5)
    assert mqtt_client.is_connected() is False


def test_publish_message_failure_buffers(mqtt_client):
    """Valida que si la publicación falla, el mensaje se guarda en el buffer."""
    mqtt_client._connected = True
    mqtt_client._client = MagicMock()
    # rc=1 da error de publicación
    mqtt_client._client.publish.return_value.rc = 1

    success = mqtt_client._publish_message({"detections": []})
    assert success is False
    assert mqtt_client.get_buffer_size() == 1


def test_mqtt_client_import_error_logic(monkeypatch):
    """Verifica que se lanza ImportError si paho-mqtt no está instalado."""
    import src.sender.mqtt_client as mqtt_mod

    monkeypatch.setattr(mqtt_mod, "MQTT_AVAILABLE", False)

    with pytest.raises(ImportError, match="Dependencia paho-mqtt no instalada"):
        mqtt_mod.MQTTClient(broker="localhost", port=1883, topic="t", device_id="D1")


@patch("paho.mqtt.client.Client")
def test_mqtt_connect_with_auth(mock_paho, mqtt_client):
    """Valida la configuración de usuario/contraseña y el inicio del loop."""
    mqtt_client.username = "user"
    mqtt_client.password = "pass"

    # Simular que se conecta instantáneamente para evitar el timeout
    def side_effect(*args, **kwargs):
        mqtt_client._connected = True
        return 0

    mock_paho.return_value.connect.side_effect = side_effect

    assert mqtt_client.connect() is True
    mock_paho.return_value.username_pw_set.assert_called_with("user", "pass")
    mock_paho.return_value.loop_start.assert_called_once()


def test_mqtt_disconnect_logic(mqtt_client):
    """Valida la limpieza de recursos al desconectar."""
    mqtt_client._client = MagicMock()
    mqtt_client._connected = True

    mqtt_client.disconnect()

    mqtt_client._client.loop_stop.assert_called_once()
    mqtt_client._client.disconnect.assert_called_once()
    assert mqtt_client.is_connected() is False


def test_publish_detections_with_location_metadata(mqtt_client):
    """Valida añadir los campos name/location en el mensaje MQTT"""
    mqtt_client.config = MagicMock()
    mqtt_client.config.device_name = "RPI-Lab"
    mqtt_client.config.device_location = "Piso-1"
    mqtt_client._connected = True
    mqtt_client._client = MagicMock()
    mqtt_client._client.publish.return_value.rc = 0

    det = Device(device_hash="h" * 64, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())

    mqtt_client.publish_detections([det])

    args, kwargs = mqtt_client._client.publish.call_args
    payload = json.loads(kwargs["payload"])
    assert payload["name"] == "RPI-Lab"
    assert payload["location"] == "Piso-1"


def test_mqtt_flush_buffer_retry_on_failure(mqtt_client):
    """Valida el reintento de envío del buffer y el break si falla."""
    mqtt_client._buffer = [{"id": 1}, {"id": 2}]
    mqtt_client._connected = True
    mqtt_client._client = MagicMock()

    mqtt_client._client.publish.return_value.rc = 1

    mqtt_client._flush_buffer()

    # Al fallar el primero, se detiene
    assert mqtt_client.get_buffer_size() == 1


def test_mqtt_callbacks_logging(mqtt_client, caplog):
    """Valida los logs de los callbacks on_disconnect y on_publish."""

    caplog.set_level("DEBUG", logger="src.sender.mqtt_client")

    # Desconexión inesperada (rc != 0) aparce un WARNING
    mqtt_client._on_disconnect(None, None, 1)
    assert "MQTT desconectado repentinamente" in caplog.text

    # Publicación exitosa publica DEBUG
    mqtt_client._on_publish(None, None, 123)
    assert "Mensaje 123 publicado exitosamente" in caplog.text


def test_mock_mqtt_client_full_coverage():
    """Valida todos los métodos de la clase MockMQTTClient."""
    mock = MockMQTTClient(device_id="MOCK_D1")

    assert mock.connect() is True
    assert mock.is_connected() is True
    assert mock.get_buffer_size() == 0

    dets = [Device(device_hash="h" * 64, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())] * 5

    assert mock.publish_detections(dets) is True
    mock.disconnect()
    assert mock.is_connected() is False


def test_mqtt_import_check():
    """Valida si la librería MQTT está disponible."""
    assert hasattr(mqtt_mod, "MQTT_AVAILABLE")


@patch("paho.mqtt.client.Client")
def test_mqtt_connect_timeout(mock_paho, mqtt_client):
    """Valida el error por timeout de conexión."""
    mqtt_client._connected = False

    # [start_time, current_time (loop), current_time (logger), ...]
    time_values = [0, 11, 11, 11, 11, 11]

    with patch("time.time", side_effect=time_values), patch("time.sleep", return_value=None):
        result = mqtt_client.connect()
        assert result is False


def test_publish_detections_no_config(mqtt_client):
    """Valida cuando existen detections pero no hay objeto config."""
    mqtt_client.config = None
    mqtt_client._connected = True
    mqtt_client._client = MagicMock()
    mqtt_client._client.publish.return_value.rc = 0

    det = Device(device_hash="a" * 64, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())

    assert mqtt_client.publish_detections([det]) is True


def test_flush_buffer_with_error_logging(mqtt_client, caplog):
    """Valida el log de error cuando falla el vaciado del buffer."""
    mqtt_client._buffer = [{"msg": "test"}]
    mqtt_client._connected = True
    mqtt_client._client = MagicMock()

    # Fallo de publicación durante el flush
    mqtt_client._client.publish.return_value.rc = 1

    mqtt_client._flush_buffer()
    assert "ERROR - Error al publicar mensaje del buffer" in caplog.text


def test_on_publish_callback_debug_log(mqtt_client, caplog):
    """Valida el log de depuración tras completar publicación."""
    caplog.set_level("DEBUG")
    mqtt_client._on_publish(None, None, 999)
    assert "Mensaje 999 publicado exitosamente" in caplog.text


def test_mock_client_init_and_disconnect_logs(caplog):
    """Valida los logs de inicialización y desconexión del Mock."""
    caplog.set_level("INFO", logger="src.sender.mqtt_client")

    mock = MockMQTTClient(device_id="RPI-MOCK")
    assert "[MOCK] Cliente MQTT inicializado" in caplog.text

    mock.disconnect()
    assert "[MOCK] MQTT desconectado (simulado)" in caplog.text
