from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestExportRoutes:
    @pytest.mark.asyncio
    async def test_export_detections_csv_success(self, client, mock_db_session):
        mock_detection = MagicMock()
        mock_detection.id = 1
        mock_detection.device_hash = "abc"
        mock_detection.rssi = -50
        mock_detection.zone = "near"
        mock_detection.timestamp = MagicMock()
        mock_detection.timestamp.isoformat.return_value = "2026-04-27T10:00:00"
        mock_detection.timestamp.strftime.side_effect = ["2026-04-27", "10:00:00"]
        mock_detection.device_id = "iot_01"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_detection]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/v1/export/detections/csv?last_hours=1")

        assert response.status_code == 200
        content = response.text

        assert "abc" in content
        assert "-50" in content
        assert "near" in content
        assert "iot_01" in content

    async def test_export_invalid_zone_ignored(self, client):
        """Valida que una zona inválida no rompe la exportación."""
        response = client.get("/api/v1/export/detections/csv?zone=NON_EXISTENT")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_csv_with_date_range_priority(self, client):
        """Valida el filtrado por rango específico de fechas."""
        with patch("src.api.routes.export.timezone_utils.parse_datetime") as mock_parse:
            mock_parse.side_effect = [datetime(2026, 1, 1), datetime(2026, 1, 2)]

            with patch("src.api.routes.export.get_db"):
                response = client.get(
                    "/api/v1/export/detections/csv?start_date=2026-01-01&end_date=2026-01-02"
                )

                assert response.status_code == 200
                assert (
                    "filename=detections_2026-01-01_to_2026-01-02.csv"
                    in response.headers["content-disposition"]
                )

    @pytest.mark.asyncio
    async def test_export_csv_last_minutes_filter(self, client):
        """Valida la rama de filtrado por los últimos N minutos."""
        response = client.get("/api/v1/export/detections/csv?last_minutes=15")

        assert response.status_code == 200
        assert "filename=detections_last_15min.csv" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_csv_last_days_filter(self, client):
        """Valida la rama de filtrado por los últimos N días."""
        response = client.get("/api/v1/export/detections/csv?last_days=7")

        assert response.status_code == 200
        assert "filename=detections_last_7d.csv" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_csv_invalid_zone_ignores_filter(self, client):
        """Valida que un valor de zona inválido no rompa la ejecución."""
        response = client.get("/api/v1/export/detections/csv?zone=invalid_zone")

        assert response.status_code == 200
        assert "zone_invalid_zone" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_csv_device_id_filter(self, client):
        """Valida la aplicación del filtro por ID de dispositivo IoT."""
        response = client.get("/api/v1/export/detections/csv?device_id=rpi_agent_01")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_csv_filename_with_last_hours(self, client):
        """Valida la generación del nombre de archivo para el filtro de horas."""
        response = client.get("/api/v1/export/detections/csv?last_hours=5")

        assert response.status_code == 200
        assert "filename=detections_last_5h.csv" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_csv_filename_with_zone_append(self, client):
        """Valida que la zona se concatene correctamente al nombre del archivo final."""
        response = client.get("/api/v1/export/detections/csv?zone=near")

        assert response.status_code == 200
        assert "zone_near.csv" in response.headers["content-disposition"]
