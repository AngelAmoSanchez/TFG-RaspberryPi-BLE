from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.database.models import Device

pytestmark = pytest.mark.asyncio


class TestDevicesRoutes:
    @patch("src.api.routes.devices.DeviceService")
    async def test_get_all_devices(self, mock_service, client):
        """Valida la respuesta de obtener todos los dispositivos, filtrando solo activos."""
        mock_dev = MagicMock()
        mock_dev.to_dict.return_value = {"device_id": "iot_1", "is_active": True}
        mock_service.return_value.get_all_devices = AsyncMock(return_value=[mock_dev])

        response = client.get("/api/v1/devices/?active_only=true")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["device_id"] == "iot_1"

    @patch("src.api.routes.devices.DeviceService")
    async def test_get_device_not_found(self, mock_service, client):
        """Caso negativo: Dispositivo inexistente lanza 404."""
        mock_service.return_value.get_device = AsyncMock(return_value=None)

        response = client.get("/api/v1/devices/non_existent")

        assert response.status_code == 404
        assert response.json()["detail"] == "Device no encontrado"

    @patch("src.api.routes.devices.DeviceService")
    async def test_get_device_success(self, mock_service, client):
        """Valida la respuesta de obtener un dispositivo específico por ID correctamente."""
        mock_dev = MagicMock()
        mock_dev.to_dict.return_value = {"device_id": "iot_1"}
        mock_service.return_value.get_device = AsyncMock(return_value=mock_dev)

        response = client.get("/api/v1/devices/iot_1")
        assert response.status_code == 200
        assert response.json()["device_id"] == "iot_1"

    @patch("src.api.routes.devices.DeviceService")
    async def test_update_device_info(self, mock_service, client):
        """Valida la actualización de información de un dispositivo existente."""
        mock_dev = MagicMock()
        mock_dev.to_dict.return_value = {"device_id": "iot_1", "name": "New Name"}
        mock_service.return_value.update_device_info = AsyncMock(return_value=mock_dev)

        payload = {"name": "New Name", "location": "Lab"}
        response = client.put("/api/v1/devices/iot_1", json=payload)

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    @patch("src.api.routes.devices.DeviceService")
    async def test_deactivate_device_success(self, mock_service, client):
        """Valida la desactivación de un dispositivo existente."""
        mock_dev = MagicMock()
        mock_dev.to_dict.return_value = {"is_active": False}
        mock_service.return_value.deactivate_device = AsyncMock(return_value=mock_dev)

        response = client.post("/api/v1/devices/iot_1/deactivate")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_register_device_route(self, client):
        """Valida el registro de nuevo dispositivo."""
        payload = {"device_id": "iot_sensor_99", "name": "Sensor Jardín", "location": "Exterior"}

        mock_device = MagicMock(spec=Device)
        mock_device.to_dict.return_value = {
            "device_id": "iot_sensor_99",
            "name": "Sensor Jardín",
            "location": "Exterior",
        }

        with patch(
            "src.api.routes.devices.DeviceService.register_device", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = mock_device

            response = client.post("/api/v1/devices/register", json=payload)

            assert response.status_code == 200
            assert response.json()["device_id"] == "iot_sensor_99"
            mock_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_devices_route(self, client):
        """Valida la respuesta de obtener todos los dispositivos activos."""
        mock_device = MagicMock(spec=Device)
        mock_device.to_dict.return_value = {"device_id": "active_01"}

        with patch(
            "src.api.routes.devices.DeviceService.get_active_devices", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = [mock_device]

            response = client.get("/api/v1/devices/active?threshold_minutes=30")

            assert response.status_code == 200
            assert len(response.json()) == 1
            mock_service.assert_called_with(ANY, 30)

    @pytest.mark.asyncio
    async def test_get_device_not_found_raises_404(self, client):
        """Valida que se lance un error 404 al intentar obtener un dispositivo inexistente."""
        with patch(
            "src.api.routes.devices.DeviceService.get_device", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = None

            response = client.get("/api/v1/devices/non_existent")

            assert response.status_code == 404
            assert response.json()["detail"] == "Device no encontrado"

    @pytest.mark.asyncio
    async def test_get_device_stats_not_found_raises_404(self, client):
        """Valida que se lance un error 404 al intentar obtener estadísticas de un dispositivo inexistente."""
        with patch(
            "src.api.routes.devices.DeviceService.get_device_stats", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = None

            response = client.get("/api/v1/devices/unknown_id/stats")

            assert response.status_code == 404
            assert response.json()["detail"] == "Device no encontrado"

    @pytest.mark.asyncio
    async def test_update_device_not_found_raises_404(self, client):
        """Valida que se lance un error 404 al intentar actualizar un dispositivo inexistente."""
        with patch(
            "src.api.routes.devices.DeviceService.update_device_info", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = None

            response = client.put("/api/v1/devices/missing_id", json={"name": "New Name"})

            assert response.status_code == 404
            assert response.json()["detail"] == "Device no encontrado"

    @pytest.mark.asyncio
    async def test_activate_device_route_success(self, client):
        """Valida la activación exitosa de un dispositivo."""
        mock_device = MagicMock(spec=Device)
        mock_device.to_dict.return_value = {"device_id": "iot_01", "is_active": True}

        with patch(
            "src.api.routes.devices.DeviceService.activate_device", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = mock_device

            response = client.post("/api/v1/devices/iot_01/activate")

            assert response.status_code == 200
            assert response.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_activate_device_not_found_raises_404(self, client):
        """Valida que se lance un error 404 al intentar activar un dispositivo inexistente."""
        with patch(
            "src.api.routes.devices.DeviceService.activate_device", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = None

            response = client.post("/api/v1/devices/invalid_id/activate")

            assert response.status_code == 404
            assert response.json()["detail"] == "Device no encontrado"
