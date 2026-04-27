from unittest.mock import AsyncMock, MagicMock, patch

from src.websocket.manager import ws_manager


class TestMainAPI:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "running"

    def test_health_check(self, client):
        with patch.object(ws_manager, "get_connection_count", return_value=5):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["websocket_connections"] == 5

    def test_websocket_ping_pong(self, client):
        """Prueba la comunicación básica bidireccional del WebSocket."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"

    @patch("src.api.main.init_db", new_callable=AsyncMock)
    @patch("src.api.main.start_mqtt_subscriber", new_callable=AsyncMock)
    @patch("src.config.settings.mqtt_enabled", True)
    async def test_lifespan_startup_mqtt_enabled(self, mock_mqtt, mock_db):
        """Valida que el sistema inicia DB y MQTT si está configurado."""
        from src.api.main import lifespan

        app_mock = MagicMock()

        async with lifespan(app_mock):
            mock_db.assert_called_once()
            mock_mqtt.assert_called_once()
