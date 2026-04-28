from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

import src.sender.http_client as http_mod
from src.scanner.detection import Device, Zone
from src.sender.http_client import HTTPClient


@pytest.fixture
def http_client():
    return HTTPClient(base_url="http://test.api", device_id="RPI_01", timeout=1)


def test_http_connect_success(http_client):
    """Valida conectividad exitosa con el backend."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        assert http_client.connect() is True
        mock_get.assert_called_with("http://test.api/health", timeout=1)


def test_http_connect_fail_status(http_client):
    """Valida conectividad fallida con el backend (ej: 500)."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        assert http_client.connect() is False


def test_http_connect_exception(http_client):
    """Valida conectividad fallida con el backend (ej: ConnectionError)."""
    with patch("requests.get", side_call=requests.exceptions.ConnectionError):
        assert http_client.connect() is False


def test_publish_detections_empty(http_client):
    """Valida publicación de lista de detecciones vacía."""
    assert http_client.publish_detections([]) is True


def test_publish_detections_success(http_client):
    """Valida publicación exitosa de múltiples detecciones."""
    detections = [Device(device_hash="h" * 64, rssi=-60, zone=Zone.NEAR, timestamp=datetime.now())]
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 201
        assert http_client.publish_detections(detections) is True

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert payload["device_id"] == "RPI_01"
        assert len(payload["detections"]) == 1
        assert payload["detections"][0]["zone"] == "near"


def test_publish_detections_timeout(http_client, caplog):
    """Valida publicación fallida por timeout."""
    detections = [Device(device_hash="h" * 64, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())]
    with patch("requests.post", side_effect=requests.exceptions.Timeout):
        assert http_client.publish_detections(detections) is False
        assert "ERROR - Timeout en solicitud HTTP" in caplog.text


def test_http_client_import_error_logic(monkeypatch):
    """Valida que se lance ImportError si Requests no está disponible."""
    monkeypatch.setattr(http_mod, "REQUESTS_AVAILABLE", False)

    with pytest.raises(ImportError, match="La librería Requests no está instalada"):
        http_mod.HTTPClient(base_url="http://test.api", device_id="RPI_01")


def test_http_connect_generic_exception(http_client, caplog):
    """Valida la captura de excepciones genéricas en la conexión."""
    with patch("requests.get", side_effect=Exception("Error inesperado")):
        result = http_client.connect()
        assert result is False
        assert "ERROR - Error de conectividad HTTP: Error inesperado" in caplog.text


def test_http_is_connected_wrapper(http_client):
    """Valida que is_connected invoca correctamente a connect."""
    with patch.object(HTTPClient, "connect", return_value=True) as mock_connect:
        assert http_client.is_connected() is True
        mock_connect.assert_called_once()


def test_publish_detections_with_config_and_api_key(http_client):
    """Valida la inclusión de ubicación y X-API-Key en el envío."""
    # Datos opcionles
    http_client.config = MagicMock()
    http_client.config.device_name = "Sensor-Principal"
    http_client.config.device_location = "Laboratorio-A"
    http_client.api_key = "secret-token-123"

    valid_hash = "a" * 64
    detections = [
        Device(device_hash=valid_hash, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())
    ]

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        http_client.publish_detections(detections)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["name"] == "Sensor-Principal"
        assert kwargs["json"]["location"] == "Laboratorio-A"
        assert kwargs["headers"]["X-API-Key"] == "secret-token-123"


def test_publish_detections_server_error_logging(http_client, caplog):
    """Valida el log de error cuando el servidor responde diferente a 200/201"""
    valid_hash = "a" * 64
    detections = [
        Device(device_hash=valid_hash, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())
    ]
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 403
        mock_post.return_value.text = "Forbidden Access"

        assert http_client.publish_detections(detections) is False
        assert "ERROR - Publicación HTTP fallida (estado: 403" in caplog.text


def test_publish_detections_connection_error(http_client, caplog):
    """Valida el error de conexión física durante la publicación."""
    valid_hash = "a" * 64
    detections = [
        Device(device_hash=valid_hash, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())
    ]
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        assert http_client.publish_detections(detections) is False
        assert "ERROR - Error de conexión HTTP" in caplog.text


def test_publish_detections_generic_exception(http_client, caplog):
    """Valida el log de error para errores no controlados durante la publicación."""
    valid_hash = "a" * 64
    detections = [
        Device(device_hash=valid_hash, rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())
    ]
    with patch("requests.post", side_effect=RuntimeError("Memory Fault")):
        assert http_client.publish_detections(detections) is False
        assert "ERROR - Error de publicación HTTP" in caplog.text


def test_get_buffer_size_is_always_zero(http_client):
    """Valida que el cliente HTTP no tiene buffer por ser síncrono."""
    assert http_client.get_buffer_size() == 0


def test_http_client_dependency_check(monkeypatch):
    """Valida el estado de REQUESTS_AVAILABLE."""
    monkeypatch.setattr(http_mod, "REQUESTS_AVAILABLE", True)
    assert http_mod.REQUESTS_AVAILABLE is True


def test_connect_connection_error_logging(http_client, caplog):
    """Valida el log de error cuando no se puede alcanzar el backend (error de conexión)."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        result = http_client.connect()
        assert result is False
        assert "ERROR - No se puede alcanzar el backend (error de conexión)" in caplog.text


def test_connect_timeout_logging(http_client, caplog):
    """Valida el log de error cuando la conexión al backend excede el timeout"""
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        result = http_client.connect()
        assert result is False
        assert "ERROR - Backend timeout" in caplog.text


def test_connect_generic_exception_logging(http_client, caplog):
    """Valida el log de error para excepciones genéricas en la conexión."""
    with patch("requests.get", side_effect=RuntimeError("Error inesperado")):
        result = http_client.connect()
        assert result is False
        assert "ERROR - Error de conectividad HTTP: Error inesperado" in caplog.text
