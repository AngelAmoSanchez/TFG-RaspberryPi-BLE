from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.connection import Database, close_db, get_db


@pytest.mark.asyncio
class TestDatabaseConnection:
    async def test_database_connect_success(self):
        """Valida que el objeto Database se inicializa y conecta."""
        db = Database()
        with patch("src.database.connection.create_async_engine") as mock_engine:
            await db.connect()
            assert db._initialized is True
            assert db.engine is not None
            mock_engine.assert_called_once()

    async def test_database_connect_exception(self):
        """Caso negativo: Error al conectar con el motor."""
        db = Database()
        with patch(
            "src.database.connection.create_async_engine", side_effect=Exception("Conn Error")
        ):
            with pytest.raises(Exception) as exc:
                await db.connect()
            assert "Conn Error" in str(exc.value)
            assert db._initialized is False

    async def test_get_session_lifecycle(self):
        """Valida commit y cierre en flujo normal."""
        from src.database.connection import Database

        db = Database()
        mock_session = AsyncMock()
        # Configuramos el mock como si fuera contexto
        db.async_session_maker = MagicMock()
        db.async_session_maker.return_value.__aenter__.return_value = mock_session
        db._initialized = True

        async with db.get_session() as session:
            assert session == mock_session

        assert mock_session.commit.called
        assert mock_session.close.called

    async def test_get_session_rollback_on_error(self):
        """Valida rollback ante una excepción."""
        from src.database.connection import Database

        db = Database()
        mock_session = AsyncMock()
        db.async_session_maker = MagicMock()
        db.async_session_maker.return_value.__aenter__.return_value = mock_session
        db._initialized = True

        try:
            async with db.get_session() as session:
                raise ValueError("Error forzado")
        except ValueError:
            pass

        assert mock_session.rollback.called
        assert mock_session.close.called

    @patch("src.database.connection.database.get_session")
    async def test_get_db_dependency(self, mock_get_session):
        """Valida la dependencia de FastAPI get_db."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        async for session in get_db():
            assert session == mock_session

    async def test_database_singleton_connect(self):
        """Valida que connect() inicializa el motor solo una vez."""
        db = Database()
        with patch("src.database.connection.create_async_engine") as mock_create:
            await db.connect()
            await db.connect()
            assert mock_create.call_count == 1
            assert db._initialized is True

    async def test_connect_failure_logging(self, caplog):
        """Caso negativo: Error en la conexión debe loguear y propagar la excepción."""
        db = Database()
        with patch(
            "src.database.connection.create_async_engine", side_effect=Exception("DB Error")
        ):
            with pytest.raises(Exception):
                await db.connect()
            assert "ERROR - Error de conexión" in caplog.text

    async def test_get_session_rollback_on_exception(self):
        """Valida que se ejecute rollback si el bloque yield falla."""
        db = Database()
        mock_session = AsyncMock()

        db.async_session_maker = MagicMock()
        db.async_session_maker.return_value.__aenter__.return_value = mock_session
        db._initialized = True

        with pytest.raises(RuntimeError):
            async with db.get_session() as session:
                raise RuntimeError("Falló la lógica de negocio")

        assert mock_session.rollback.called

    @pytest.mark.asyncio
    async def test_disconnect_engine_logic(self):
        """Valida que disconnect() llame a dispose() y marque como no inicializado."""
        db = Database()
        mock_engine = AsyncMock()
        db.engine = mock_engine
        db._initialized = True

        await db.disconnect()

        mock_engine.dispose.assert_called_once()
        assert db._initialized is False

    @pytest.mark.asyncio
    async def test_create_tables_error_handling(self):
        """Valida que create_tables maneje errores durante la migración."""
        db = Database()
        db._initialized = True
        mock_engine = MagicMock()
        mock_engine.begin.side_effect = Exception("Migration Failed")
        db.engine = mock_engine

        with pytest.raises(Exception, match="Migration Failed"):
            await db.create_tables()

    @pytest.mark.asyncio
    async def test_drop_tables_initialization_and_execution(self):
        """Valida que drop_tables se inicialice si no lo está y ejecute la lógica de borrado."""
        db = Database()
        db._initialized = False

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_engine.begin.return_value = mock_conn

        with patch.object(db, "connect", new_callable=AsyncMock) as mock_connect:
            db.engine = mock_engine
            await db.drop_tables()
            mock_connect.assert_called_once()
            mock_engine.begin.assert_called_once()
            assert mock_conn.__aenter__.return_value.run_sync.called

    @pytest.mark.asyncio
    async def test_get_session_auto_initialization(self):
        """Valida que get_session auto-inicialice la conexión si no está hecha."""
        db = Database()
        db._initialized = False

        mock_session = AsyncMock()

        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__.return_value = mock_session
        db.async_session_maker = mock_maker

        with patch.object(db, "connect", new_callable=AsyncMock) as mock_connect:
            async with db.get_session() as session:
                assert session == mock_session

            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_db_utility(self):
        """Valida que close_db llame a disconnect del Database."""
        with patch(
            "src.database.connection.database.disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            await close_db()
            mock_disconnect.assert_called_once()
