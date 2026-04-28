from datetime import datetime, timezone

from src.utils import timezone_utils


class TestTimezoneUtils:
    def test_ensure_spain_tz_with_naive_datetime(self):
        """Valida el IF: Si no tiene timezone, asume que es de España."""
        naive_dt = datetime(2026, 4, 27, 10, 0, 0)
        result = timezone_utils.ensure_spain_tz(naive_dt)
        assert result.tzinfo == timezone_utils.SPAIN_TZ
        assert result.hour == 10

    def test_ensure_spain_tz_with_utc(self):
        """Valida el ELSE: Si tiene timezone (UTC), convierte a España."""
        utc_dt = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        result = timezone_utils.ensure_spain_tz(utc_dt)
        # En abril (CEST), España es UTC+2
        assert result.tzinfo == timezone_utils.SPAIN_TZ
        assert result.hour == 12

    def test_parse_datetime_handles_z_format(self):
        """Valida el reemplazo de 'Z' por el offset de UTC para compatibilidad."""
        iso_str = "2026-04-24T15:00:00Z"
        result = timezone_utils.parse_datetime(iso_str)
        assert result.tzinfo == timezone_utils.SPAIN_TZ
        assert result.day == 24

    def test_to_spain_tz_from_naive_assumes_utc(self):
        """Valida que al convertir a zona de España, si el datetime es naive, se asume que es UTC."""
        naive_dt = datetime(2026, 4, 27, 10, 0, 0)
        result = timezone_utils.to_spain_tz(naive_dt)
        assert result.hour == 12  # 10 UTC -> 12 Madrid

    def test_utc_now_logic(self):
        """Valida que utc_now devuelva un datetime con tzinfo de UTC."""
        result = timezone_utils.utc_now()
        assert result.tzinfo == timezone.utc

    def test_to_spain_tz_with_existing_tz(self):
        """Valida que to_spain_tz convierta correctamente desde una zona horaria existente."""
        dt = datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc)
        result = timezone_utils.to_spain_tz(dt)
        assert result.tzinfo == timezone_utils.SPAIN_TZ
