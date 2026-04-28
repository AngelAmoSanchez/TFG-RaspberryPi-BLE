from datetime import datetime

import pytest

from src.scanner.detection import Detection, Device, Zone


def test_zone_descriptions():
    """Valida que las descripciones de zona son correctas."""
    assert Zone.NEAR.get_description() == "Zona Cercana (0-2m)"
    assert Zone.MEDIUM.get_description() == "Zona Media (2-5m)"
    assert Zone.FAR.get_description() == "Zona Lejana (>5m)"


def test_detection_valid_creation():
    """Valida la creación de detección con datos válidos."""
    now = datetime.now()
    det = Detection(mac_address="AA:BB:CC:DD:EE:FF", rssi=-50, timestamp=now)
    assert det.mac_address == "AA:BB:CC:DD:EE:FF"
    assert det.to_dict()["rssi"] == -50


def test_detection_invalid_rssi_positive():
    """Valida que RSSI positivo debe lanzar ValueError."""
    with pytest.raises(ValueError, match="RSSI tiene que ser negativo"):
        Detection(mac_address="MAC", rssi=10, timestamp=datetime.now())


def test_detection_invalid_rssi_too_low():
    """Valida que RSSI fuera de rango razonable debe lanzar ValueError."""
    with pytest.raises(ValueError, match="RSSI demasiado bajo"):
        Detection(mac_address="MAC", rssi=-101, timestamp=datetime.now())


def test_device_invalid_hash_length():
    """Valida que el hash SHA-256 debe tener 64 carácteres."""
    with pytest.raises(ValueError, match="El hash tiene que tener 64 carácteres"):
        Device(device_hash="short_hash", rssi=-50, zone=Zone.NEAR, timestamp=datetime.now())


def test_device_from_detection_mapping():
    """Valida la transformación correcta de Detection a Device."""
    now = datetime.now()
    det = Detection(mac_address="MAC", rssi=-60, timestamp=now)
    dev = Device.from_detection(det, "a" * 64, Zone.NEAR)
    assert dev.rssi == -60
    assert dev.zone == Zone.NEAR
