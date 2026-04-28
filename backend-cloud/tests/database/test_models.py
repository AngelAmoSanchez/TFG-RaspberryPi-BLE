from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.database.models import (
    AggregatedStats,
    Detection,
    Device,
    ZoneEnum,
    _get_spain_now,
)


@pytest.mark.unit
class TestModels:
    def test_get_spain_now(self):
        """Valida que el helper de tiempo devuelva la zona horaria correcta."""
        now = _get_spain_now()
        assert now.tzinfo == ZoneInfo("Europe/Madrid")
        assert isinstance(now, datetime)

    def test_detection_to_dict(self):
        """Valida la serialización del modelo Detection."""
        dt = _get_spain_now()
        detection = Detection(
            id=1,
            device_hash="abc123hash",
            rssi=-60,
            zone=ZoneEnum.NEAR,
            timestamp=dt,
            device_id="iot_sensor_01",
        )

        data = detection.to_dict()
        assert data["id"] == 1
        assert data["device_hash"] == "abc123hash"
        assert data["zone"] == "near"
        assert data["timestamp"] == dt.isoformat()
        assert data["device_id"] == "iot_sensor_01"

    def test_device_to_dict(self):
        """Valida la serialización del modelo Device."""
        now = _get_spain_now()
        device = Device(
            id=10,
            device_id="dev_unique_01",
            name="Sensor Entrada",
            location="Pasillo A",
            is_active=1,
            created_at=now,
            updated_at=now,
        )

        data = device.to_dict()
        assert data["device_id"] == "dev_unique_01"
        assert data["is_active"] is True
        assert "last_seen" in data
        assert data["last_seen"] is None

    def test_aggregated_stats_to_dict(self):
        """Valida la serialización de AggregatedStats."""
        start = datetime(2026, 4, 27, 10, 0, tzinfo=ZoneInfo("Europe/Madrid"))
        end = datetime(2026, 4, 27, 11, 0, tzinfo=ZoneInfo("Europe/Madrid"))

        stats = AggregatedStats(
            id=5,
            period_type="hour",
            period_start=start,
            period_end=end,
            zone=ZoneEnum.MEDIUM,
            unique_devices=50,
            total_detections=500,
            estimated_people=35,
            avg_rssi=-72.5,
        )

        data = stats.to_dict()
        assert data["period_type"] == "hour"
        assert data["estimated_people"] == 35
        assert data["avg_rssi"] == -72.5
        assert data["zone"] == "medium"

    def test_detection_to_dict_conversion(self):
        """Valida que el enum se convierta a string en el diccionario."""
        det = Detection(
            device_hash="hash" * 16,
            rssi=-65,
            zone=ZoneEnum.NEAR,
            timestamp=datetime.now(),
            device_id="iot_01",
        )
        result = det.to_dict()
        assert result["zone"] == "near"
        assert isinstance(result["timestamp"], str)

    def test_device_to_dict_active_status(self):
        """Valida que is_active (Integer) se convierta a booleano."""
        now = datetime.now()
        # Poner created_at y updated_at manualmente para evitar el error NoneType
        dev = Device(device_id="iot_01", is_active=1, created_at=now, updated_at=now)
        data = dev.to_dict()
        assert data["is_active"] is True
