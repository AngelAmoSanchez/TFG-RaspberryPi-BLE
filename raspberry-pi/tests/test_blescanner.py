import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import src.scanner.ble_scanner as ble_mod
from src.scanner.ble_scanner import SPAIN_TZ, BLEScanner, MockBLEScanner
from src.scanner.detection import Detection


@pytest.mark.asyncio
async def test_mock_scanner_generation():
    """Valida que el mock genera el número solicitado de dispositivos."""
    scanner = MockBLEScanner(num_devices=3)
    detections = await scanner.scan_devices()

    # El mock genera entre num-2 y num+2 dispositivos
    assert len(detections) >= 1
    assert all(d.mac_address is not None for d in detections)


@pytest.mark.asyncio
async def test_ble_scanner_import_error(monkeypatch):
    """Valida la simulación de fallo si Bleak no está instalado."""

    monkeypatch.setattr(ble_mod, "BLEAK_AVAILABLE", False)

    with pytest.raises(ImportError, match="Bleak no se encuentra instalado"):
        ble_mod.BLEScanner()


@pytest.mark.asyncio
async def test_ble_scanner_generic_exception():
    """Valida el control de excepciones durante el escaneo."""
    with patch("bleak.BleakScanner.start", side_effect=Exception("Bluetooth error")):
        scanner = BLEScanner(scan_duration=1)
        results = await scanner.scan_devices()
        assert results == []  # Devuelve lista vacía y loguea el error


def test_ble_scanner_dependency_check(monkeypatch):
    """Valida el estado de disponibilidad."""

    # Disponible
    monkeypatch.setattr(ble_mod, "BLEAK_AVAILABLE", True)
    scanner = ble_mod.BLEScanner(scan_duration=1)
    assert scanner.is_available() is True

    # No disponible
    monkeypatch.setattr(ble_mod, "BLEAK_AVAILABLE", False)
    assert scanner.is_available() is False


@pytest.mark.asyncio
async def test_ble_scanner_callback_logic():
    """Valida el procesamiento de dispositivos nuevos y actualizaciones de RSSI."""
    scanner = BLEScanner(scan_duration=1)

    mock_device = MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"
    mock_device.name = "Test Device"

    mock_data = MagicMock()
    mock_data.rssi = -60

    # Parcheamos la clase
    with patch("src.scanner.ble_scanner.BleakScanner") as mock_scanner_class:
        # Inicio del escaneo
        scan_task = asyncio.create_task(scanner.scan_devices())
        await asyncio.sleep(0.1)  # Permitir que se ejecute la inicialización

        # Capturamos el callback pasado al constructor
        args, kwargs = mock_scanner_class.call_args
        callback = kwargs.get("detection_callback")

        # Primera detección
        callback(mock_device, mock_data)
        assert mock_device.address in scanner._devices_cache

        # Actualización con RSSI más cercano
        mock_data.rssi = -50
        callback(mock_device, mock_data)
        assert scanner._devices_cache[mock_device.address].rssi == -50

        # Ignorar si el RSSI es más lejano
        mock_data.rssi = -70
        callback(mock_device, mock_data)
        assert scanner._devices_cache[mock_device.address].rssi == -50

        await scan_task


@pytest.mark.asyncio
async def test_ble_scanner_logging_output(caplog):
    """Valida los mensajes de log durante el escaneo."""
    caplog.set_level("DEBUG", logger="src.scanner.ble_scanner")

    scanner = BLEScanner(scan_duration=0.1)
    mock_data = {
        f"00:00:00:00:00:0{i}": Detection(
            mac_address=f"00:00:00:00:00:0{i}", rssi=-60, timestamp=datetime.now(SPAIN_TZ)
        )
        for i in range(7)
    }

    with patch("src.scanner.ble_scanner.BleakScanner.start", return_value=None), patch(
        "src.scanner.ble_scanner.BleakScanner.stop", return_value=None
    ):
        task = asyncio.create_task(scanner.scan_devices())
        await asyncio.sleep(0.05)
        scanner._devices_cache.update(mock_data)
        await task

        assert "Escaneo completado: 7 dispositivos detectados" in caplog.text
        assert "... y 2 dispositivos más" in caplog.text


def test_scanners_availability():
    """Valida el método is_available en ambos tipos de scanner."""

    scanner_real = BLEScanner(scan_duration=1)
    assert scanner_real.is_available() == scanner_real.is_available()  # Depende de BLEAK_AVAILABLE

    scanner_mock = MockBLEScanner()
    assert scanner_mock.is_available() is True
