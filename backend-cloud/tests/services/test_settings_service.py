from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.settings_service import SettingsService


class TestSettingsService:
    @pytest.mark.asyncio
    async def test_get_thresholds_from_db(self, db_session):
        """Valida que se obtengan los umbrales desde la BD si existen."""
        service = SettingsService()

        near_setting = MagicMock()
        near_setting.value = "-60"
        medium_setting = MagicMock()
        medium_setting.value = "-75"

        mock_result_near = MagicMock()
        mock_result_near.scalar_one_or_none.return_value = near_setting

        mock_result_medium = MagicMock()
        mock_result_medium.scalar_one_or_none.return_value = medium_setting

        db_session.execute.side_effect = [mock_result_near, mock_result_medium]

        thresholds = await service.get_thresholds(db_session)
        assert thresholds["near_threshold"] == -60

    @pytest.mark.asyncio
    async def test_get_thresholds_defaults_and_save(self, db_session):
        """Valida que si no hay umbrales en la BD, se creen con los valores por defecto."""
        service = SettingsService()

        # Configuramos el mock para que devuelva un resultado que al llamar a scalar_one_or_none sea None
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_res  # este ya es un AsyncMock

        with patch("src.services.settings_service.settings") as mock_settings:
            mock_settings.near_threshold = -50
            mock_settings.medium_threshold = -70
            thresholds = await service.get_thresholds(db_session)

            assert thresholds["near_threshold"] == -50
            assert db_session.add.called
            assert db_session.commit.called

    @pytest.mark.asyncio
    async def test_get_thresholds_creation_logic(self, db_session):
        """Valida que si no hay umbrales en la BD, se creen con los valores por defecto."""
        service = SettingsService()

        # Simulamos que no hay nada en la BD
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_res)

        await service.get_thresholds(db_session)

        assert db_session.add.called
        assert db_session.commit.called

    @pytest.mark.asyncio
    async def test_update_thresholds_recalculation(self, db_session):
        """Valida que al actualizar los umbrales, se recalcule el conteo de detecciones."""
        service = SettingsService()

        mock_counts = MagicMock(near_count=10, medium_count=20, far_count=30, total=60)
        mock_res = MagicMock()
        mock_res.first.return_value = mock_counts
        db_session.execute.return_value = mock_res

        result = await service.update_thresholds(db_session, -55, -70)
        assert result["recalculated_count"] == 60
