from unittest.mock import AsyncMock, patch

import pytest

from src.database.connection import database, init_db


@pytest.mark.asyncio
class TestDatabaseSchema:
    async def test_create_tables_logic(self):
        """Valida que create_tables intente ejecutar run_sync con Base.metadata."""
        with patch.object(database, "connect", new_callable=AsyncMock) as mock_conn:
            with patch.object(database, "engine") as mock_engine:
                # Mock del contexto de engine.begin()
                mock_conn_context = AsyncMock()
                mock_engine.begin.return_value = mock_conn_context

                await database.create_tables()

                mock_conn.assert_called_once()
                mock_engine.begin.assert_called_once()
                # Valida que se llamó a run_sync (encargado de create_all)
                mock_conn_context.__aenter__.return_value.run_sync.assert_called()

    @patch("src.database.connection.database.connect", new_callable=AsyncMock)
    @patch("src.database.connection.database.create_tables", new_callable=AsyncMock)
    async def test_init_db_development_mode(self, mock_create, mock_connect):
        """Valida que init_db llama a conectar y crear tablas en dev."""
        with patch("src.database.connection.settings") as mock_settings:
            mock_settings.environment = "development"
            await init_db()
            mock_connect.assert_called_once()
            mock_create.assert_called_once()
