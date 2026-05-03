from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.utils.timezone_utils import SPAIN_TZ
from src.websocket.manager import WebSocketManager

pytestmark = pytest.mark.unit


class MockWebSocket:
    """Mock de WebSocket para testing."""

    def __init__(self, should_fail=False, client_id=None):
        self.sent_messages = []
        self.should_fail = should_fail
        self.is_closed = False
        self.client_id = client_id or id(self)

    async def send_json(self, data):
        if self.should_fail:
            raise Exception("Connection failed")
        if self.is_closed:
            raise Exception("WebSocket is closed")
        self.sent_messages.append(data)

    async def accept(self):
        pass

    async def close(self):
        self.is_closed = True


class TestWebSocketManagerInit:
    """Tests para inicialización del manager."""

    def test_manager_initialization(self):
        """Valida la inicialización del manager."""
        manager = WebSocketManager()

        assert hasattr(manager, "active_connections")
        assert len(manager.active_connections) == 0
        assert isinstance(manager.active_connections, set)
        assert hasattr(manager, "lock")


class TestConnect:
    """Tests para conectar WebSocket."""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self):
        """Valida que conectar añade WebSocket al set activo."""
        manager = WebSocketManager()
        mock_ws = MockWebSocket()

        await manager.connect(mock_ws)

        assert len(manager.active_connections) == 1
        assert mock_ws in manager.active_connections

    @pytest.mark.asyncio
    async def test_connect_calls_accept(self):
        """Valida que se llama accept al conectar."""
        manager = WebSocketManager()
        mock_ws = MockWebSocket()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        mock_ws.accept.assert_called_once()


class TestDisconnect:
    """Tests para desconectar WebSocket."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """Valida que se elimine el WebSocket del set."""
        manager = WebSocketManager()
        mock_ws = MockWebSocket()

        await manager.connect(mock_ws)
        await manager.disconnect(mock_ws)

        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """Valida que desconectar un WebSocket que no existe no lanza error (que lo ignore)."""
        manager = WebSocketManager()
        mock_ws = MockWebSocket()

        await manager.disconnect(mock_ws)
        assert len(manager.active_connections) == 0


class TestBroadcast:
    """Tests para enviar mensajes a todos."""

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        """Valida que broadcast envíe el mensaje a todas las conexiones activas."""
        manager = WebSocketManager()
        ws1, ws2 = MockWebSocket(), MockWebSocket()

        await manager.connect(ws1)
        await manager.connect(ws2)

        message = {"msg": "hello"}
        await manager.broadcast(message)

        assert ws1.sent_messages == [message]
        assert ws2.sent_messages == [message]

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connection(self):
        """Valida que broadcast remueva automáticamente conexiones fallidas."""
        manager = WebSocketManager()
        ws_good = MockWebSocket()
        ws_bad = MockWebSocket(should_fail=True)

        await manager.connect(ws_good)
        await manager.connect(ws_bad)

        await manager.broadcast({"type": "test"})

        assert ws_bad not in manager.active_connections
        assert len(manager.active_connections) == 1

    @pytest.mark.asyncio
    @patch("src.websocket.manager.timezone_utils.now")
    async def test_broadcast_detection_event(self, mock_now):
        """Valida el helper de detección de eventos."""
        # El mock debe devolver un objeto datetime compatible con .isoformat()
        mock_date = datetime(2026, 4, 27, 10, 0, 0, tzinfo=SPAIN_TZ)
        mock_now.return_value = mock_date
        manager = WebSocketManager()
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        await manager.broadcast_detection_event("dev_01", 5)

        expected = {
            "type": "detection_event",
            "timestamp": mock_date.isoformat(),
            "device_id": "dev_01",
            "count": 5,
        }
        assert mock_ws.sent_messages[0] == expected

    @pytest.mark.asyncio
    @patch("src.websocket.manager.timezone_utils.now")
    async def test_broadcast_stats_update(self, mock_now):
        """Valida el helper de actualización de stats."""
        mock_date = datetime(2026, 4, 27, 10, 0, 0, tzinfo=SPAIN_TZ)
        mock_now.return_value = mock_date
        manager = WebSocketManager()
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        stats = {"cpu": 10, "mem": 50}
        await manager.broadcast_stats_update(stats)

        assert mock_ws.sent_messages[0]["data"] == stats
        assert mock_ws.sent_messages[0]["type"] == "stats_update"

    @pytest.mark.asyncio
    async def test_broadcast_no_connections_early_return(self):
        """Valida que broadcast regrese pronto si no hay conexiones activas."""
        manager = WebSocketManager()
        manager.active_connections = set()

        with patch.object(manager, "lock", AsyncMock()) as mock_lock:
            await manager.broadcast({"msg": "test"})

            assert mock_lock.__aenter__.call_count == 0


class TestSendPersonalMessage:
    """Tests para enviar mensaje a conexión específica."""

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self):
        """Valida que send_personal_message envíe el mensaje al WebSocket dado."""
        manager = WebSocketManager()
        ws = MockWebSocket()
        message = {"secret": "data"}

        await manager.send_personal_message(message, ws)
        assert ws.sent_messages == [message]

    @pytest.mark.asyncio
    async def test_send_personal_message_exception_handled(self):
        """Valida que el try/except interno captura errores sin propagarlos ni lanzar excepciones."""
        manager = WebSocketManager()
        ws = MockWebSocket(should_fail=True)

        await manager.send_personal_message({"test": "fail"}, ws)


class TestGetConnectionCount:
    @pytest.mark.asyncio
    async def test_get_connection_count(self):
        """Valida que get_connection_count devuelva el número correcto de conexiones activas."""
        manager = WebSocketManager()
        assert manager.get_connection_count() == 0

        ws = MockWebSocket()
        await manager.connect(ws)
        assert manager.get_connection_count() == 1


@pytest.mark.asyncio
class TestWebSocketManagerLogic:
    """Tests para lógica interna del WebSocketManager, especialmente ramas y manejo de errores"""

    async def test_broadcast_empty_connections(self):
        """Valida que broadcast maneje correctamente el caso sin conexiones activas"""
        manager = WebSocketManager()
        manager.active_connections = set()

        await manager.broadcast({"data": "test"})
        assert len(manager.active_connections) == 0

    async def test_broadcast_with_disconnected_clients(self):
        """Valida el manejo de desconexiones durante broadcast elminando las conexiones que fallan."""
        manager = WebSocketManager()

        mock_ws_ok = AsyncMock()
        mock_ws_fail = AsyncMock()
        mock_ws_fail.send_json.side_effect = Exception("Connection lost")

        manager.active_connections = {mock_ws_ok, mock_ws_fail}

        await manager.broadcast({"msg": "hello"})

        assert mock_ws_fail not in manager.active_connections
        assert mock_ws_ok in manager.active_connections
