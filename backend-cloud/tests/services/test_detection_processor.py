from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.models import Detection, ZoneEnum
from src.services.detection_processor import DetectionProcessorService


class TestDetectionProcessorService:
    @pytest.mark.parametrize(
        "hash_str,expected",
        [
            ("a" * 64, True),  # Válido
            ("G" * 64, False),  # No hexadecimal
            ("abc", False),  # Muy corto
            ("1234567890abcdef" * 4, True),  # 64 carácteres exactos
        ],
    )
    def test_verify_hash(self, hash_str, expected):
        """Valida la función de verificación de hash con casos válidos e inválidos."""
        assert DetectionProcessorService.verify_hash(hash_str) == expected

    @pytest.mark.asyncio
    async def test_save_detection_invalid_hash_raises_error(self, db_session):
        """Valida que se lance error ante hashes no hexadecimales o de longitud incorrecta."""
        service = DetectionProcessorService()
        with pytest.raises(ValueError, match="Hash inválido"):
            await service.save_detection(db_session, "invalid_hash", -60, "iot_1")

    @pytest.mark.asyncio
    async def test_save_detection_invalid_rssi_raises_error(self, db_session):
        """Valida que se lance error ante valores RSSI imposibles."""
        service = DetectionProcessorService()
        h = "a" * 64
        with pytest.raises(ValueError, match="RSSI inválido"):
            await service.save_detection(db_session, h, 10, "iot_1")  # RSSI > 0 es inválido

    @pytest.mark.asyncio
    async def test_save_bulk_detections_partial_failure(self, db_session):
        """Valida que en envíos masivos, las entradas malformadas no impidan guardar las correctas."""
        service = DetectionProcessorService()
        data = [
            {"device_hash": "a" * 64, "rssi": -50},
            {"device_hash": "mal"},  # Falta rssi -> Saltará al 'except'
            {"device_hash": "b" * 64, "rssi": -80},
        ]

        with patch("src.services.settings_service.SettingsService.get_thresholds") as mock_t:
            mock_t.return_value = {"near_threshold": -60, "medium_threshold": -75}
            results = await service.save_bulk_detections(db_session, data, "iot_1")

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_save_bulk_detections_with_malformed_data(self, db_session):
        """Valida que en envíos masivos, las entradas malformadas no impidan guardar las correctas."""
        service = DetectionProcessorService()
        # El primer elemento fallará (no tiene rssi), el segundo es correcto
        data = [{"device_hash": "a" * 64}, {"device_hash": "b" * 64, "rssi": -50}]

        with patch("src.services.settings_service.SettingsService.get_thresholds") as m:
            m.return_value = {"near_threshold": -60, "medium_threshold": -75}
            results = await service.save_bulk_detections(db_session, data, "iot_1")

            assert len(results) == 1
            assert db_session.add_all.called


@pytest.mark.asyncio
class TestDetectionProcessorServiceExtended:
    """Tests para cubrir la lógica de clasificación, estimación y filtrado por zona."""

    async def test_classify_zone_boundaries(self, db_session):
        """Valida la clasificación basada en umbrales (NEAR, MEDIUM, FAR)."""

        mock_thresholds = {"near_threshold": -60, "medium_threshold": -75}

        with patch(
            "src.services.settings_service.SettingsService.get_thresholds",
            new_callable=AsyncMock,
            return_value=mock_thresholds,
        ):
            assert await DetectionProcessorService.classify_zone(db_session, -60) == ZoneEnum.NEAR
            assert await DetectionProcessorService.classify_zone(db_session, -75) == ZoneEnum.MEDIUM
            assert await DetectionProcessorService.classify_zone(db_session, -76) == ZoneEnum.FAR

    def test_estimate_people_rounding_and_minimum(self):
        """Valida el redondeo y el valor mínimo de 1 persona si hay dispositivos."""
        # Con ratio de 1.5:
        # 1 dispositivo / 1.5 = 0.66 -> redondea a 1
        # 2 dispositivos / 1.5 = 1.33 -> redondea a 1
        service = DetectionProcessorService(devices_per_person=1.5)

        assert service.estimate_people(1) == 1
        assert service.estimate_people(2) == 1
        assert service.estimate_people(3) == 2  # 3 / 1.5 = 2.0
        assert service.estimate_people(0) == 0

    async def test_save_detection_rssi_validation(self, db_session):
        """Valida que se lance error ante valores RSSI imposibles."""
        service = DetectionProcessorService()
        valid_hash = "a" * 64

        # RSSI positivo
        with pytest.raises(ValueError, match="RSSI inválido"):
            await service.save_detection(db_session, valid_hash, 10, "dev_01")

        # RSSI por debajo del límite técnico BLE
        with pytest.raises(ValueError, match="RSSI inválido"):
            await service.save_detection(db_session, valid_hash, -128, "dev_01")

    async def test_save_detection_creation_logic(self, db_session):
        """Valida la creación correcta del objeto Detection con umbrales dinámicos."""
        service = DetectionProcessorService()
        valid_hash = "a" * 64
        mock_thresholds = {"near_threshold": -60, "medium_threshold": -75}

        with patch(
            "src.services.settings_service.SettingsService.get_thresholds",
            new_callable=AsyncMock,
            return_value=mock_thresholds,
        ):
            result = await service.save_detection(db_session, valid_hash, -70, "dev_01")

            assert isinstance(result, Detection)
            assert result.zone == ZoneEnum.MEDIUM
            assert db_session.add.called
            assert db_session.flush.called

    async def test_save_bulk_detections_with_custom_timestamps(self, db_session):
        """Valida el parseo de marcas de tiempo en envíos masivos."""
        service = DetectionProcessorService()
        custom_ts = "2026-04-27T10:00:00Z"
        data = [{"device_hash": "a" * 64, "rssi": -50, "timestamp": custom_ts}]

        mock_thresholds = {"near_threshold": -60, "medium_threshold": -75}
        with patch(
            "src.services.settings_service.SettingsService.get_thresholds",
            new_callable=AsyncMock,
            return_value=mock_thresholds,
        ):
            results = await service.save_bulk_detections(db_session, data, "dev_01")

            assert len(results) == 1
            assert results[0].timestamp.hour == 12  # UTC 10:00 -> CEST 12:00

    async def test_get_recent_detections_with_zone_filter(self, db_session):
        """Valida que se aplique el filtro WHERE cuando se solicita una zona."""
        service = DetectionProcessorService()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)

        await service.get_recent_detections(db_session, limit=10, zone=ZoneEnum.NEAR)

        query_sent = db_session.execute.call_args[0][0]
        assert "detections.zone = :zone_1" in str(query_sent)

    async def test_get_unique_devices_count_with_zone_filter(self, db_session):
        """Valida el conteo de dispositivos únicos filtrado por zona y rango."""
        service = DetectionProcessorService()
        start = datetime.now()
        end = datetime.now()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        db_session.execute = AsyncMock(return_value=mock_result)

        count = await service.get_unique_devices_count(db_session, start, end, zone=ZoneEnum.FAR)

        assert count == 5
        query_sent = str(db_session.execute.call_args[0][0]).lower()

        assert "count" in query_sent
        assert "distinct" in query_sent
        assert "device_hash" in query_sent
        assert "zone" in query_sent

    async def test_get_unique_devices_count_null_fallback(self, db_session):
        """Valida que el conteo devuelva 0 si la base de datos devuelve None."""
        service = DetectionProcessorService()

        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # Simular resultado vacío
        db_session.execute = AsyncMock(return_value=mock_result)

        count = await service.get_unique_devices_count(db_session, datetime.now(), datetime.now())
        assert count == 0
