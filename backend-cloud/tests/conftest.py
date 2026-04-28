from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.main import app
from src.database.connection import get_db


@pytest.fixture(autouse=True)
def mock_db_init():
    """Evita que FastAPI intente conectar a la base de datos real en el arranque."""
    with patch("src.api.main.init_db", new_callable=AsyncMock), patch(
        "src.api.main.close_db", new_callable=AsyncMock
    ):
        yield


@pytest.fixture
def mock_db_session():
    """Mock de la sesión de SQLAlchemy para inyectar en las rutas."""
    session = AsyncMock()
    # Mock para que las consultas no rompan aunque no se configuren explícitamente en cada test
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    return session


@pytest.fixture
def client(mock_db_session):
    """Cliente de pruebas con la dependencia de DB sobrescrita."""
    from fastapi.testclient import TestClient

    # Sobrescribimos la dependencia get_db
    app.dependency_overrides[get_db] = lambda: mock_db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(mock_db_session):
    """Alias para que los tests de servicios encuentren la fixture db_session."""
    return mock_db_session
