from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.database.models import ZoneEnum

pytestmark = pytest.mark.asyncio


class TestDetectionsRoutes:
    @patch("src.api.routes.detections.DetectionProcessorService")
    @patch("src.api.routes.detections.DeviceService")
    async def test_create_detection_success(
        self, mock_device_service, mock_processor_service, client
    ):
        mock_proc = mock_processor_service.return_value
        mock_proc.save_detection = AsyncMock()
        mock_detection_obj = MagicMock()
        mock_detection_obj.to_dict.return_value = {"id": 1, "device_hash": "hash123"}
        mock_proc.save_detection.return_value = mock_detection_obj

        mock_dev = mock_device_service.return_value
        mock_dev.update_last_seen = AsyncMock()

        payload = {
            "device_hash": "hash123",
            "rssi": -65,
            "zone": "near",
            "timestamp": "2026-04-27T10:00:00",
        }

        response = client.post("/api/v1/detections/?device_id=iot_01", json=payload)

        assert response.status_code == 200
        assert response.json()["device_hash"] == "hash123"
        mock_proc.save_detection.assert_called_once()
        mock_dev.update_last_seen.assert_called_once()

    @patch("src.api.routes.detections.DetectionProcessorService")
    @patch("src.api.routes.detections.DeviceService")
    async def test_create_bulk_detections_success(
        self, mock_device_service, mock_processor_service, client
    ):
        mock_proc = mock_processor_service.return_value
        mock_proc.save_bulk_detections = AsyncMock(return_value=[MagicMock(), MagicMock()])

        mock_dev = mock_device_service.return_value
        mock_dev.register_device = AsyncMock()
        mock_dev.update_last_seen = AsyncMock()

        payload = {
            "device_id": "iot_01",
            "detections": [{"hash": "h1"}, {"hash": "h2"}],
            "name": "Sensor Principal",
            "location": "Entrada",
        }

        response = client.post("/api/v1/detections/bulk", json=payload)

        assert response.status_code == 200
        assert response.json()["count"] == 2
        mock_dev.register_device.assert_called_with(
            ANY, "iot_01", name="Sensor Principal", location="Entrada"
        )

    @patch("src.api.routes.detections.DetectionProcessorService")
    async def test_get_detection_count_invalid_zone(self, mock_processor_service, client):
        """Caso negativo: Zona inválida lanza 400."""
        response = client.get("/api/v1/detections/count?zone=INVALID_ZONE")

        assert response.status_code == 400
        assert "Zona inválida" in response.json()["detail"]

    @patch("src.api.routes.detections.DetectionProcessorService")
    async def test_get_detection_count_success(self, mock_processor_service, client):
        """Caso positivo: Conteo con zona válida."""
        mock_proc = mock_processor_service.return_value
        mock_proc.get_unique_devices_count = AsyncMock(return_value=10)
        mock_proc.estimate_people.return_value = 8

        response = client.get("/api/v1/detections/count?hours=5&zone=near")

        assert response.status_code == 200
        data = response.json()
        assert data["unique_devices"] == 10
        assert data["estimated_people"] == 8

    @pytest.mark.asyncio
    async def test_get_recent_detections_endpoint(self, client):
        """Prueba el endpoint GET /recent con y sin filtros de zona."""
        from unittest.mock import MagicMock, patch

        mock_det = MagicMock()
        mock_det.to_dict.return_value = {"id": 1, "device_hash": "abc"}

        with patch(
            "src.api.routes.detections.DetectionProcessorService.get_recent_detections",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = [mock_det]

            response = client.get("/api/v1/detections/recent?limit=10")
            assert response.status_code == 200
            assert len(response.json()) == 1

            response_zone = client.get("/api/v1/detections/recent?limit=5&zone=near")
            assert response_zone.status_code == 200

            mock_service.assert_called_with(ANY, 5, ZoneEnum.NEAR)

    @pytest.mark.asyncio
    async def test_get_recent_detections_route(self, client):
        """Test para el endpoint /recent con transformación to_dict"""
        from src.database.models import ZoneEnum

        mock_det = MagicMock()
        mock_det.to_dict.return_value = {"id": "test", "rssi": -50}

        with patch(
            "src.api.routes.detections.DetectionProcessorService.get_recent_detections",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = [mock_det]

            response = client.get("/api/v1/detections/recent?limit=5&zone=near")
            assert response.status_code == 200
            assert response.json()[0]["id"] == "test"
            mock_get.assert_called_with(ANY, 5, ZoneEnum.NEAR)
