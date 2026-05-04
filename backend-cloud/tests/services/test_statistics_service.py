from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.database.models import AggregatedStats, ZoneEnum
from src.services.statistics_service import StatisticsService
from src.utils import timezone_utils

pytestmark = pytest.mark.unit


class TestStatisticsService:
    @pytest.fixture
    def service(self):
        return StatisticsService(devices_per_person=1.5)

    @pytest.mark.parametrize(
        "devices,expected",
        [
            (0, 0),  # Caso base: 0 dispositivos
            (1, 1),  # 1 / 1.5 = 0.66 -> 1
            (2, 1),  # 2 / 1.5 = 1.33 -> 1
            (3, 2),  # 3 / 1.5 = 2.0 -> 2
            (5, 3),  # 5 / 1.5 = 3.33 -> 3
        ],
    )
    def test_estimate_people_logic(self, service, devices, expected):
        """Valida el cálculo y el max(1, int) para casos positivos."""
        assert service.estimate_people(devices) == expected

    @pytest.mark.asyncio
    async def test_get_real_time_stats_success(self, service, db_session):
        """Valida el cálculo de estadísticas en tiempo real."""
        mock_row_near = MagicMock(
            zone=ZoneEnum.NEAR, unique_devices=10, total_detections=100, avg_rssi=-55.555
        )
        mock_row_far = MagicMock(
            zone=ZoneEnum.FAR, unique_devices=5, total_detections=50, avg_rssi=-80.0
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row_near, mock_row_far]
        db_session.execute = AsyncMock(return_value=mock_result)

        stats = await service.get_real_time_stats(db_session, minutes=5)

        assert stats["total"]["unique_devices"] == 15
        assert stats["by_zone"]["near"]["unique_devices"] == 10
        assert stats["by_zone"]["near"]["avg_rssi"] == pytest.approx(-55.56, 0.01)
        assert stats["by_zone"]["far"]["estimated_people"] == 3  # 5 / 1.5 = 3.33 -> 3

    @pytest.mark.asyncio
    async def test_get_zone_distribution_empty(self, service, db_session):
        """Caso negativo: Sin detecciones debe devolver porcentajes 0 y no romper por división por cero."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_zone_distribution(db_session, datetime.now(), datetime.now())

        assert result["total"] == 0
        assert result["distribution"] == {}

    @pytest.mark.asyncio
    async def test_get_zone_distribution_success(self, service, db_session):
        """Valida el cálculo de porcentajes de distribución."""
        mock_row = MagicMock(zone=ZoneEnum.NEAR, count=75)
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_zone_distribution(db_session, datetime.now(), datetime.now())

        assert result["total"] == 75
        assert result["distribution"]["near"]["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_get_hourly_stats_formatting_branches(db_session):
        """Valida los diferentes formateos de avg_rssi."""
        service = StatisticsService()
        # avg_rssi es un valor
        row_with_val = MagicMock(
            hour_start=datetime.now(),
            zone=ZoneEnum.NEAR,
            unique_devices=1,
            total_detections=1,
            avg_rssi=-50.0,
        )
        # avg_rssi es None (evita error)
        row_with_none = MagicMock(
            hour_start=datetime.now(),
            zone=ZoneEnum.FAR,
            unique_devices=0,
            total_detections=0,
            avg_rssi=None,
        )

        mock_res = MagicMock()
        mock_res.all.return_value = [row_with_val, row_with_none]
        db_session.execute = AsyncMock(return_value=mock_res)

        stats = await service.get_hourly_stats(db_session, datetime.now())
        assert stats[0]["avg_rssi"] == -50.0
        assert stats[1]["avg_rssi"] is None

    @pytest.mark.asyncio
    async def test_get_hourly_stats_no_data(self, service, db_session):
        """Valida el comportamiento cuando no hay datos disponibles."""
        mock_result = MagicMock()
        mock_result.all.return_value = []  # Simulamos 0 filas
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_hourly_stats(db_session, datetime.now())
        assert result == []  # Valida que no rompe y devuelve lista vacía

    @pytest.mark.asyncio
    async def test_get_hourly_stats_with_date_param(self, client):
        """Valida el comportamiento del endpoint hourly con parámetro de fecha."""
        with patch(
            "src.api.routes.statistics.StatisticsService.get_hourly_stats", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = []

            response = client.get("/api/v1/statistics/hourly?date=2026-04-27")

            assert response.status_code == 200
            assert response.json()["date"] == "2026-04-27"
            mock_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_daily_stats_custom_range(self, client):
        """Valida el parseo de start_date y end_date en daily stats."""
        with patch(
            "src.api.routes.statistics.StatisticsService.get_daily_stats", new_callable=AsyncMock
        ) as mock_service:
            mock_service.return_value = []

            response = client.get(
                "/api/v1/statistics/daily?start_date=2026-04-01&end_date=2026-04-07"
            )

            assert response.status_code == 200
            assert response.json()["start_date"] == "2026-04-01"
            mock_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_hourly_stats_data_transformation(db_session):
        """Valida la transformación de datos y cálculo de estimated_people en hourly stats."""
        service = StatisticsService(devices_per_person=2.0)
        mock_row = MagicMock(
            hour_start=datetime(2026, 4, 27, 10),
            zone=ZoneEnum.NEAR,
            unique_devices=4,
            total_detections=20,
            avg_rssi=-50.1234,
        )
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db_session.execute = AsyncMock(return_value=mock_result)

        stats = await service.get_hourly_stats(db_session, datetime(2026, 4, 27))

        assert len(stats) == 1
        assert stats[0]["estimated_people"] == 2
        assert stats[0]["avg_rssi"] == -50.12
        assert stats[0]["zone"] == "near"

    @pytest.mark.asyncio
    async def test_get_daily_stats_query_and_formatting(self, db_session):
        """Valida la consulta y el formateo de resultados en daily stats."""
        service = StatisticsService(devices_per_person=1.0)
        mock_row = MagicMock(
            day_start=datetime(2026, 4, 27),
            zone=ZoneEnum.FAR,
            unique_devices=10,
            total_detections=100,
            avg_rssi=None,
        )
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db_session.execute = AsyncMock(return_value=mock_result)

        stats = await service.get_daily_stats(
            db_session, datetime(2026, 4, 27), datetime(2026, 4, 28)
        )

        assert len(stats) == 1
        assert stats[0]["unique_devices"] == 10
        assert stats[0]["estimated_people"] == 10
        assert stats[0]["avg_rssi"] is None

    @pytest.mark.asyncio
    async def test_get_range_stats_with_device_id_filter_applied(self, db_session):
        """Valida que el filtro por device_id se incluya correctamente en la consulta de range stats."""
        service = StatisticsService()
        db_session.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        await service.get_range_stats(
            db_session, datetime.now(), datetime.now(), device_id="iot_01"
        )

        args, _ = db_session.execute.call_args
        sql_query = str(args[0])
        assert "detections.device_id = :device_id_1" in sql_query

    @pytest.mark.asyncio
    async def test_get_real_time_stats_full_calculation_and_totals(self, db_session):
        """Valida el cálculo completo de estadísticas en tiempo real, incluyendo totales y estimación de personas."""
        service = StatisticsService(devices_per_person=1.5)
        mock_row_1 = MagicMock(zone="near", unique_devices=3, total_detections=15, avg_rssi=-40.0)
        mock_row_2 = MagicMock(
            zone="medium", unique_devices=3, total_detections=10, avg_rssi=-65.5555
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row_1, mock_row_2]
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_real_time_stats(db_session, minutes=15)

        assert result["total"]["unique_devices"] == 6
        assert result["total"]["total_detections"] == 25
        assert result["total"]["estimated_people"] == 4
        assert result["by_zone"]["medium"]["avg_rssi"] == -65.56
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_range_stats_with_multiple_zones_and_totals(self, db_session):
        """Valida el cálculo de estadísticas por rango con múltiples zonas y totales correctos."""
        service = StatisticsService(devices_per_person=1.0)
        start = datetime(2026, 4, 27, 10, 0)
        end = datetime(2026, 4, 27, 11, 0)

        mock_row_near = MagicMock(
            zone=ZoneEnum.NEAR, unique_devices=5, total_detections=50, avg_rssi=-55.5
        )
        mock_row_far = MagicMock(
            zone=ZoneEnum.FAR, unique_devices=10, total_detections=100, avg_rssi=-80.0
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row_near, mock_row_far]
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_range_stats(db_session, start, end)

        assert result["total"]["unique_devices"] == 15
        assert result["total"]["total_detections"] == 150
        assert result["total"]["estimated_people"] == 15
        assert "near" in result["by_zone"]
        assert "far" in result["by_zone"]
        assert result["by_zone"]["near"]["unique_devices"] == 5

    @pytest.mark.asyncio
    async def test_save_aggregated_stats_database_insertion(self, db_session):
        """Valida la creación y guardado de objetos AggregatedStats en la base de datos."""
        service = StatisticsService()
        p_start = datetime(2026, 4, 27, 12, 0)
        p_end = datetime(2026, 4, 27, 13, 0)

        mock_row = MagicMock(
            zone=ZoneEnum.MEDIUM, unique_devices=8, total_detections=40, avg_rssi=-70.0
        )
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.save_aggregated_stats(db_session, "hour", p_start, p_end)

        assert len(result) == 1
        assert isinstance(result[0], AggregatedStats)
        assert result[0].zone == ZoneEnum.MEDIUM
        assert result[0].period_type == "hour"
        db_session.add_all.assert_called_once()
        db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_zone_distribution_calculation_logic(self, db_session):
        """Valida el cálculo de distribución por zona, incluyendo casos diferentes"""
        service = StatisticsService()
        start = datetime(2026, 4, 27, 14, 0)
        end = datetime(2026, 4, 27, 15, 0)

        mock_row_near = MagicMock(zone=ZoneEnum.NEAR, count=30)
        mock_row_medium = MagicMock(zone=ZoneEnum.MEDIUM, count=70)

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row_near, mock_row_medium]
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_zone_distribution(db_session, start, end)

        assert result["total"] == 100
        assert result["distribution"]["near"]["count"] == 30
        assert result["distribution"]["near"]["percentage"] == 30.0
        assert result["distribution"]["medium"]["count"] == 70
        assert result["distribution"]["medium"]["percentage"] == 70.0

    @pytest.mark.asyncio
    async def test_get_zone_distribution_empty_results(self, db_session):
        """Valida el comportamiento de get_zone_distribution cuando la consulta no devuelve resultados."""
        service = StatisticsService()

        mock_result = MagicMock()
        mock_result.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_zone_distribution(db_session, datetime.now(), datetime.now())

        assert result["total"] == 0
        assert result["distribution"] == {}

    @pytest.mark.asyncio
    async def test_get_realtime_stats_endpoint(self, client):
        """Valida que el endpoint realtime llama correctamente al servicio con los parámetros de consulta."""
        with patch(
            "src.api.routes.statistics.StatisticsService.get_real_time_stats",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = {"total": {"unique_devices": 5}, "by_zone": {}}

            response = client.get("/api/v1/statistics/realtime?minutes=10&device_id=iot_01")

            assert response.status_code == 200
            assert response.json()["total"]["unique_devices"] == 5
            mock_service.assert_called_once()
            args, _ = mock_service.call_args
            assert args[1] == 10  # minutos
            assert args[2] == "iot_01"  # device_id

    @pytest.mark.asyncio
    async def test_get_zone_distribution_endpoint(self, client):
        """Valida que el endpoint distribution calcula correctamente los rangos de tiempo y devuelve los datos."""
        with patch(
            "src.api.routes.statistics.StatisticsService.get_zone_distribution",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = {
                "total": 100,
                "distribution": {"near": {"count": 100, "percentage": 100.0}},
            }

            response = client.get("/api/v1/statistics/distribution?hours=12")

            # Verificaciones
            assert response.status_code == 200
            data = response.json()
            assert "start_time" in data
            assert "end_time" in data
            assert data["total"] == 100

            mock_service.assert_called_once()
            args, _ = mock_service.call_args
            start_dt = args[1]
            end_dt = args[2]
            diff = end_dt - start_dt
            assert diff.total_seconds() / 3600 == pytest.approx(12, 0.01)

    @patch("src.services.statistics_service.timezone_utils.now")
    def test_compute_histogram_window_logic(self, mock_now, service):
        """Valida el cálculo de ventanas y bloques de tiempo para histogramas."""
        # Fijamos la hora: Lunes 2026-04-27 10:45:00
        fixed_now = datetime(2026, 4, 27, 10, 45, 0, tzinfo=ZoneInfo("Europe/Madrid"))
        mock_now.return_value = fixed_now

        # Caso 1: Hour (6 bloques de 10 min de la hora actual)
        start, end, buckets = service._compute_histogram_window("hour")
        assert start.hour == 10 and start.minute == 0
        assert end.hour == 11 and end.minute == 0
        assert len(buckets) == 6
        assert buckets[0][0].minute == 0
        assert buckets[-1][1].minute == 0  # 11:00

        # Caso 2: Today (8 bloques de 3h de hoy)
        start, end, buckets = service._compute_histogram_window("today")
        assert start.hour == 0 and start.day == 27
        assert end.hour == 0 and end.day == 28
        assert len(buckets) == 8
        assert (buckets[1][0] - buckets[0][0]).total_seconds() / 3600 == 3.0

        # Caso 3: Week (7 bloques de 1 día terminando hoy)
        start, end, buckets = service._compute_histogram_window("week")
        assert start.day == 21  # 27 - 6 días
        assert end.day == 28
        assert len(buckets) == 7

        with pytest.raises(ValueError, match="Rango range_key desconocido"):
            service._compute_histogram_window("month")

    @pytest.mark.asyncio
    @patch("src.services.statistics_service.timezone_utils.now")
    async def test_get_histogram_stats_full_mapping(self, mock_now, service, db_session):
        """Valida que el histograma mapee datos de DB y rellene con ceros los bloques vacíos."""
        fixed_now = datetime(2026, 4, 27, 10, 45, 0, tzinfo=ZoneInfo("Europe/Madrid"))
        mock_now.return_value = fixed_now

        mock_row = MagicMock(zone=ZoneEnum.NEAR, unique_devices=5, total_detections=50)

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]

        res_empty = MagicMock()
        res_empty.all.return_value = []

        db_session.execute.side_effect = [
            mock_result,
            res_empty,
            res_empty,
            res_empty,
            res_empty,
            res_empty,
        ]

        result = await service.get_histogram_stats(db_session, "hour")

        assert result["range"] == "hour"
        assert len(result["buckets"]) == 6

        first_bucket = result["buckets"][0]
        assert first_bucket["by_zone"]["near"] == 5
        assert first_bucket["total"] == 5

        second_bucket = result["buckets"][1]
        assert second_bucket["total"] == 0
        assert second_bucket["by_zone"]["near"] == 0

    @pytest.mark.asyncio
    @patch("src.services.statistics_service.timezone_utils.now")
    async def test_get_histogram_stats_week_success(self, mock_now, service, db_session):
        """Valida la casuística de range_key='week'"""
        fixed_now = datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone_utils.SPAIN_TZ)
        mock_now.return_value = fixed_now

        today_start = fixed_now.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = today_start - timedelta(days=6)

        mock_row = MagicMock(zone=ZoneEnum.NEAR, unique_devices=15, total_detections=150)

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]

        res_empty = MagicMock()
        res_empty.all.return_value = []

        db_session.execute.side_effect = [mock_result] + [res_empty] * 6

        result = await service.get_histogram_stats(db_session, range_key="week")

        assert result["range"] == "week"
        assert result["bin_interval"] == "1 day"
        assert len(result["buckets"]) == 7

        first_bucket = result["buckets"][0]
        assert first_bucket["period_start"] == expected_start.isoformat()
        assert first_bucket["by_zone"]["near"] == 15

        last_bucket = result["buckets"][-1]
        assert last_bucket["period_start"] == today_start.isoformat()
        assert last_bucket["total"] == 0

        assert db_session.execute.call_count == 7

    @pytest.mark.asyncio
    async def test_get_histogram_stats_device_filter_sql(self, service, db_session):
        """Valida que el filtro por device_id se aplique a la consulta del histograma."""
        db_session.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        await service.get_histogram_stats(db_session, "today", device_id="raspberry_01")

        args, _ = db_session.execute.call_args
        sql_query = str(args[0])
        assert "detections.device_id = :device_id_1" in sql_query

    @pytest.mark.asyncio
    async def test_get_histogram_stats_invalid_key_error(self, service, db_session):
        """Valida que se lance ValueError ante un range_key inválido en el servicio."""
        with pytest.raises(ValueError):
            await service.get_histogram_stats(db_session, "invalid_range")
