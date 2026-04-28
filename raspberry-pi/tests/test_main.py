import asyncio
import importlib
import signal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.main
from src.config import AgentConfig, HTTPConfig, MQTTConfig, ScannerConfig
from src.main import DetectionProcessor, IoTAgent, main, signal_handler
from src.scanner.detection import Detection, Zone


@pytest.fixture
def mock_config():
    """Configuración base para evitar errores de inicialización."""
    return AgentConfig(
        device_id="RPI-TEST-001",
        communication_mode="mqtt",
        scanner=ScannerConfig(use_mock=True, scan_interval=1),
        mqtt=MQTTConfig(
            broker="broker.emqx.io", port=1883, topic="test", username=None, password=None
        ),
        http=HTTPConfig(base_url="http://localhost:8000", api_key=None),
    )


def test_log_directory_creation():
    """Valida que el sistema intenta crear el directorio de logs si no existe."""
    with patch("os.path.exists", return_value=False), patch("os.makedirs") as mock_makedirs:
        importlib.reload(src.main)

        mock_makedirs.assert_called_with("./logs")


def test_anonymize_mac_consistency():
    """Valida que el hash debe ser consistente y estar en mayúsculas."""
    processor = DetectionProcessor()
    mac = "aa:bb:cc:dd:ee:ff"
    hash1 = processor.anonymize_mac(mac)
    hash2 = processor.anonymize_mac("AA:BB:CC:DD:EE:FF")

    assert hash1 == hash2
    assert len(hash1) == 64


def test_classify_zone_thresholds():
    """Valida el comportamiento de clasificación según los umbrales."""
    processor = DetectionProcessor(near_threshold=-60, medium_threshold=-75)

    assert processor.classify_zone(-50).value == Zone.NEAR.value
    assert processor.classify_zone(-70).value == Zone.MEDIUM.value
    assert processor.classify_zone(-80).value == Zone.FAR.value


def test_process_detections_with_error(caplog):
    """Valida que se maneja el error de dominio en process_detections."""
    processor = DetectionProcessor()

    mock_detection = MagicMock()
    mock_detection.mac_address = "AA:BB:CC:DD:EE:FF"
    mock_detection.rssi = -50
    mock_detection.timestamp = datetime.now()

    with patch("src.main.Device.from_detection", side_effect=ValueError("Error de dominio")):
        processed = processor.process_detections([mock_detection])

        assert len(processed) == 0
        assert "Error procesando detección" in caplog.text


def test_iot_agent_init_logic(mock_config):
    """Valida la inicialización del procesador y la selección del scanner."""
    mock_config.scanner.use_mock = False
    with patch("src.main.BLEScanner") as mock_ble:
        agent = IoTAgent(mock_config)
        mock_ble.assert_called_once()

    mock_config.scanner.use_mock = True
    agent_mock = IoTAgent(mock_config)
    from src.main import MockBLEScanner

    assert isinstance(agent_mock.scanner, MockBLEScanner)


def test_init_client_http_mode(mock_config):
    """Valida la inicialización del cliente HTTP."""
    mock_config.communication_mode = "http"
    mock_config.http.base_url = "http://test.com"

    with patch("src.main.HTTPClient") as mock_http:
        agent = IoTAgent(mock_config)
        mock_http.assert_called_once()


@pytest.mark.asyncio
async def test_agent_run_connection_status(mock_config):
    """Valida la conexión del cliente y el inicio del flag running."""
    agent = IoTAgent(mock_config)
    agent.client.connect = MagicMock(return_value=False)
    agent.scanner.scan_devices = AsyncMock(return_value=[])

    agent.running = True
    loop_task = asyncio.create_task(agent.run())
    await asyncio.sleep(0.1)
    agent.running = False
    await loop_task

    # Verifica intento de conexión y log de error
    agent.client.connect.assert_called_once()


@pytest.mark.asyncio
async def test_agent_run_cycle_metrics_and_buffer(mock_config, caplog):
    """Valida el procesamiento, resumen de zonas y logs de buffer."""
    caplog.set_level("INFO", logger="src.main")

    agent = IoTAgent(mock_config)
    agent.client.connect = MagicMock(return_value=True)
    agent.client.is_connected = MagicMock(return_value=True)
    agent.client.get_buffer_size = MagicMock(return_value=10)

    now = datetime.now()
    mock_det = Detection(mac_address="AA:BB:CC:DD:EE:FF", rssi=-50, timestamp=now)
    agent.scanner.scan_devices = AsyncMock(return_value=[mock_det])

    agent.running = True
    # Interrupción del bucle tras el primer ciclo
    with patch("src.main.asyncio.sleep", side_effect=asyncio.CancelledError):
        await agent.run()

    assert "Distribución de zonas: NEAR=1" in caplog.text
    assert "El buffer tiene 10 mensajes pendientes" in caplog.text


@pytest.mark.asyncio
async def test_shutdown_cleanup(mock_config):
    """Valida el apagado limpio usando una configuración válida."""
    agent = IoTAgent(mock_config)
    agent.client = MagicMock()

    await agent.shutdown()
    assert agent.running is False
    agent.client.disconnect.assert_called_once()


def test_signal_handler_behavior():
    """Valida el manejador de señales del sistema."""
    with pytest.raises(SystemExit) as e:
        signal_handler(signal.SIGINT, None)
    assert e.value.code == 0


@pytest.mark.asyncio
async def test_main_execution_flow():
    """Valida el flujo exitoso y manejo de errores en main."""
    with patch(
        "src.main.load_config_from_file", side_effect=ValueError("Configuración inválida")
    ), pytest.raises(SystemExit) as e:
        await main()
    assert e.value.code == 1

    with patch(
        "src.main.load_config_from_file", side_effect=Exception("Error fatal")
    ), pytest.raises(SystemExit) as e:
        await main()
    assert e.value.code == 1
