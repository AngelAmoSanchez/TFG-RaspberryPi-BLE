from unittest.mock import ANY, AsyncMock, patch

import pytest


class TestSettingsRoutes:
    @patch("src.api.routes.settings.SettingsService")
    async def test_update_thresholds_logic_error(self, mock_service, client):
        """Caso negativo: near_threshold <= medium_threshold."""
        payload = {
            "near_threshold": -80,
            "medium_threshold": -70,
        }
        response = client.put("/api/v1/settings/thresholds", json=payload)

        assert response.status_code == 400
        assert "mayor" in response.json()["detail"]

    @patch("src.api.routes.settings.SettingsService")
    async def test_update_thresholds_success(self, mock_service, client):
        """Valida la actualización exitosa de umbrales y la respuesta del endpoint."""
        mock_inst = mock_service.return_value
        mock_inst.update_thresholds = AsyncMock(
            return_value={
                "recalculated_count": 10,
                "updated_to_near": 2,
                "updated_to_medium": 3,
                "updated_to_far": 5,
            }
        )

        payload = {"near_threshold": -50, "medium_threshold": -70}
        response = client.put("/api/v1/settings/thresholds", json=payload)

        assert response.status_code == 200
        assert response.json()["recalculated"]["total_detections"] == 10

    @pytest.mark.asyncio
    async def test_get_thresholds_endpoint_response_structure(self, client):
        """Valida que el endpoint de obtención de umbrales devuelva la estructura esperada."""
        mock_thresholds = {"near_threshold": -65, "medium_threshold": -80}

        with patch(
            "src.api.routes.settings.SettingsService.get_thresholds", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = mock_thresholds

            response = client.get("/api/v1/settings/thresholds")

            assert response.status_code == 200
            data = response.json()
            assert data["near_threshold"] == -65
            assert "RSSI ≥ -65 dBm" in data["description"]["near"]

    @pytest.mark.asyncio
    async def test_reset_thresholds_endpoint_execution(self, client):
        """Valida la ejecución exitosa del endpoint de reseteo de umbrales."""
        mock_result = {
            "recalculated_count": 0,
            "updated_to_near": 0,
            "updated_to_medium": 0,
            "updated_to_far": 0,
        }

        with patch(
            "src.api.routes.settings.SettingsService.update_thresholds", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = mock_result

            response = client.post("/api/v1/settings/thresholds/reset")

            assert response.status_code == 200
            assert response.json()["message"] == "Umbrales reseteados a valores por defecto"
            mock_update.assert_called_once_with(ANY, -60, -75)
