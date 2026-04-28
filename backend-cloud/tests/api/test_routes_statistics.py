from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

SPAIN_TZ = ZoneInfo("Europe/Madrid")


class TestStatisticsRoutes:
    @patch("src.api.routes.statistics.StatisticsService")
    async def test_get_range_stats_success(self, mock_stats_service, client):
        """Valida la obtención exitosa de estadísticas por rango de fechas."""
        mock_stats = mock_stats_service.return_value
        mock_stats.get_range_stats = AsyncMock(return_value={"total": 100})

        start = "2026-04-20T10:00:00"
        end = "2026-04-20T12:00:00"
        response = client.get(f"/api/v1/statistics/range?start_time={start}&end_time={end}")

        assert response.status_code == 200
        assert response.json() == {"total": 100}

    async def test_get_range_stats_invalid_order(self, client):
        """Caso negativo: Fecha inicio > Fecha fin."""
        start = "2026-04-20T15:00:00"
        end = "2026-04-20T10:00:00"
        response = client.get(f"/api/v1/statistics/range?start_time={start}&end_time={end}")

        assert response.status_code == 400
        assert "anterior" in response.json()["detail"]

    async def test_get_range_stats_invalid_format(self, client):
        """Caso negativo: Formato de fecha mal formado."""
        response = client.get("/api/v1/statistics/range?start_time=hoy&end_time=manana")
        assert response.status_code == 400

    @patch("src.api.routes.statistics.StatisticsService")
    async def test_get_daily_stats_defaults(self, mock_stats_service, client):
        """Valida que usa valores por defecto (últimos 7 días) si no hay params."""
        mock_stats = mock_stats_service.return_value
        mock_stats.get_daily_stats = AsyncMock(return_value=[])

        response = client.get("/api/v1/statistics/daily")

        assert response.status_code == 200
        mock_stats.get_daily_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_range_stats_invalid_date_format(self, client):
        """Valida la captura del ValueError ante un formato de fecha ISO incorrecto."""
        response = client.get(
            "/api/v1/statistics/range",
            params={"start_time": "fecha-incorrecta", "end_time": "2026-04-23T12:00:00"},
        )

        assert response.status_code == 400
        assert "Formato de fecha inválido" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_range_stats_start_after_end(self, client):
        """Valida el error cuando la fecha de inicio es posterior o igual a la de fin."""
        response = client.get(
            "/api/v1/statistics/range",
            params={"start_time": "2026-04-23T15:00:00", "end_time": "2026-04-23T10:00:00"},
        )

        assert response.status_code == 400
        assert "fecha de inicio debe ser anterior" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_hourly_stats_default_today(self, client):
        """Valida la rama donde no se proporciona fecha y se usa la actual del servidor."""
        with patch(
            "src.api.routes.statistics.StatisticsService.get_hourly_stats", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = []

            response = client.get("/api/v1/statistics/hourly")

            assert response.status_code == 200
            today_str = datetime.now(SPAIN_TZ).date().isoformat()
            assert response.json()["date"] == today_str
            mock_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_daily_stats_default_range_calculation(self, client):
        """Valida el cálculo del rango por defecto basado en el parámetro 'days'."""
        with patch(
            "src.api.routes.statistics.StatisticsService.get_daily_stats", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = []

            response = client.get("/api/v1/statistics/daily?days=10")

            assert response.status_code == 200
            data = response.json()

            start_dt = datetime.fromisoformat(data["start_date"])
            end_dt = datetime.fromisoformat(data["end_date"])

            diff = end_dt - start_dt
            assert diff.days == 10
            mock_service.assert_called_once()
