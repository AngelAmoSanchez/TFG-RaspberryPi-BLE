import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mqtt.subscriber import MQTTSubscriber, start_mqtt_subscriber


@pytest.mark.asyncio
class TestMQTTSubscriber:
    @pytest.fixture
    def subscriber(self):
        return MQTTSubscriber(broker="localhost", port=1883, topic="test/topic")

    def test_on_connect_success(self, subscriber, caplog):
        """Valida el rc == 0 (Éxito)."""
        mock_client = MagicMock()
        subscriber.on_connect(mock_client, None, {}, 0)
        assert subscriber.connected is True
        mock_client.subscribe.assert_called_with("test/topic", qos=1)

    def test_on_connect_fail(self, subscriber):
        """Valida el rc != 0 (Fallo)."""
        subscriber.on_connect(MagicMock(), None, {}, 1)
        assert subscriber.connected is False

    @patch("src.mqtt.subscriber.asyncio.create_task")
    def test_on_message_valid_payload(self, mock_create_task, subscriber):
        """Caso positivo: JSON correcto dispara tarea de procesamiento."""
        msg = MagicMock()
        payload = {"device_id": "rasp_01", "detections": [{"hash": "h1", "rssi": -50}]}
        msg.payload = json.dumps(payload).encode()

        subscriber.on_message(None, None, msg)
        mock_create_task.assert_not_called()

    def test_on_message_missing_device_id(self, subscriber, caplog):
        """Caso negativo: JSON sin device_id muestra advertencia (IF not device_id)."""
        msg = MagicMock()
        msg.payload = b'{"detections": []}'
        subscriber.on_message(None, None, msg)
        assert "WARN - Falta el mensaje device_id" in caplog.text

    def test_on_message_invalid_json(self, subscriber, caplog):
        """Caso negativo: Captura JSONDecodeError."""
        msg = MagicMock()
        msg.payload = b"not-a-json"
        subscriber.on_message(None, None, msg)
        assert "ERROR - JSON inválido" in caplog.text

    async def test_process_message_logic(self, subscriber):
        """Valida la lógica de persistencia dentro de la tarea asíncrona."""
        mock_db = AsyncMock()
        # Mockeamos el contexto asíncrono de la base de datos
        with patch("src.mqtt.subscriber.database.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db

            subscriber.device_service.update_last_seen = AsyncMock()
            subscriber.detection_service.save_bulk_detections = AsyncMock()

            await subscriber.process_message("rasp_01", [{"hash": "h1"}])

            subscriber.device_service.update_last_seen.assert_called_once()
            subscriber.detection_service.save_bulk_detections.assert_called_once()
            mock_db.commit.assert_called_once()


@pytest.mark.asyncio
class TestMQTTSubscriberDetailed:
    def test_import_error_handling(self):
        """Valida el manejo de error cuando paho-mqtt no está instalado"""
        with patch("src.mqtt.subscriber.MQTT_AVAILABLE", False):
            with pytest.raises(ImportError, match="Dependencia paho-mqtt no está instalada"):
                MQTTSubscriber("localhost", 1883, "test")

    def test_on_disconnect_unexpected(self, caplog):
        """Valida el log de error ante desconexiones inesperadas (rc != 0)."""
        sub = MQTTSubscriber("localhost", 1883, "test")
        sub.on_disconnect(MagicMock(), None, 1)  # rc != 0
        assert "ERROR - MQTT desconectado inesperadamente" in caplog.text

    def test_on_message_invalid_json_error(self, caplog):
        """Valida la captura de JSONDecodeError."""
        sub = MQTTSubscriber("localhost", 1883, "test")
        msg = MagicMock()
        msg.payload = b"invalid{json"
        sub.on_message(MagicMock(), None, msg)
        assert "ERROR - JSON inválido" in caplog.text

    async def test_process_message_exception(self, caplog):
        """Valida el manejo de excepciones al procesar mensaje (Exception general)"""
        sub = MQTTSubscriber("localhost", 1883, "test")
        caplog.set_level("ERROR")

        with patch("src.mqtt.subscriber.database.get_session", side_effect=Exception("DB Down")):
            # Mockeamos sleep para que el test no espere los reintentos reales
            with patch("asyncio.sleep", return_value=None):
                await sub.process_message("dev1", [])

                # Buscamos el mensaje final de la función tras agotar los 2 intentos
                assert "ERROR - No se pudo procesar mensaje tras 2 intentos" in caplog.text

    async def test_run_loop_and_reconnect(self):
        """Valida que el bucle de run intente reconectar"""
        sub = MQTTSubscriber("localhost", 1883, "test")
        sub.connect = MagicMock(return_value=True)

        # Simulamos que corre una vez y se detiene para no entrar en bucle infinito
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            sub.connected = False
            try:
                await sub.run()
            except asyncio.CancelledError:
                pass
            assert sub.connect.call_count >= 2  # Inicial + reconexión

    def test_init_without_mqtt_dependency(self):
        """Valida que se lance ImportError si paho-mqtt no está disponible."""
        with patch("src.mqtt.subscriber.MQTT_AVAILABLE", False):
            with pytest.raises(ImportError, match="Dependencia paho-mqtt no está instalada"):
                MQTTSubscriber("localhost", 1883, "test/topic")

    def test_on_disconnect_unexpected_logging(self, caplog):
        """Valida el log de advertencia ante desconexiones con código de retorno != 0."""
        sub = MQTTSubscriber("localhost", 1883, "test/topic")
        with caplog.at_level("WARNING"):
            sub.on_disconnect(MagicMock(), None, 1)  # rc=1 (inesperado)
            assert "ERROR - MQTT desconectado inesperadamente" in caplog.text

    def test_on_message_malformed_json_logging(self, caplog):
        """Valida captura de JSONDecodeError."""
        sub = MQTTSubscriber("localhost", 1883, "test/topic")
        msg = MagicMock()
        msg.payload = b"not a json {["

        with caplog.at_level("ERROR"):
            sub.on_message(MagicMock(), None, msg)
            assert "ERROR - JSON inválido" in caplog.text

    @patch("src.mqtt.subscriber.mqtt.Client")
    def test_connect_with_credentials(self, mock_client_class):
        """Valida la creación del cliente con usuario/contraseña y callbacks."""
        mock_client_inst = mock_client_class.return_value
        sub = MQTTSubscriber("localhost", 1883, "test", username="user", password="pass")

        result = sub.connect()

        assert result is True
        mock_client_inst.username_pw_set.assert_called_with("user", "pass")
        assert mock_client_inst.on_connect == sub.on_connect
        mock_client_inst.connect.assert_called_with("localhost", 1883, keepalive=60)

    def test_connect_exception_handling(self, caplog):
        """Valida que connect devuelva False ante excepciones."""
        sub = MQTTSubscriber("invalid_host", 1883, "test")
        with patch(
            "src.mqtt.subscriber.mqtt.Client", side_effect=Exception("Connection test error")
        ):
            result = sub.connect()
            assert result is False
            assert "ERROR - Error de conexión con MQTT" in caplog.text

    def test_disconnect_full_lifecycle(self):
        """Valida que se detenga el loop y se desconecte el cliente."""
        sub = MQTTSubscriber("localhost", 1883, "test")
        mock_client = MagicMock()
        sub.client = mock_client
        sub.connected = True

        sub.disconnect()

        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert sub.connected is False

    @pytest.mark.asyncio
    async def test_run_loop_reconnection(self, caplog):
        """Valida que el bucle intente reconectar si connected es False."""

        sub = MQTTSubscriber("localhost", 1883, "test")

        # Mockear connect para simular reconexión exitosa
        with patch.object(sub, "connect", return_value=True) as mock_conn:
            sub.running = True
            sub.connected = False  # Simular pérdida de conexión para activar la rama if

            with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
                with caplog.at_level("WARNING"):
                    await sub.run()

            # Se debió llamar a connect al menos una vez dentro del bucle de reconexión
            assert mock_conn.called
            # Se debió generar el log de advertencia de reconexión
            assert "WARN - Conexión con MQTT perdida, reconectando..." in caplog.text

    @pytest.mark.asyncio
    async def test_start_mqtt_subscriber_disabled(self, caplog):
        """Valida comportamiento cuando MQTT está deshabilitado en settings."""
        with patch("src.mqtt.subscriber.settings") as mock_settings:
            mock_settings.mqtt_enabled = False
            result = await start_mqtt_subscriber()
            assert result is None
            assert "MQTT subscriber deshabilitado" in caplog.text

    @pytest.mark.asyncio
    async def test_start_mqtt_subscriber_no_broker(self, caplog):
        """Valida comportamiento cuando no hay broker configurado."""
        with patch("src.mqtt.subscriber.settings") as mock_settings:
            mock_settings.mqtt_enabled = True
            mock_settings.mqtt_broker = None
            result = await start_mqtt_subscriber()
            assert result is None
            assert "MQTT broker no configurado" in caplog.text

    @pytest.mark.asyncio
    async def test_start_mqtt_subscriber_success(self):
        """Valida la creación de la tarea de ejecución y retorno del objeto."""
        with patch("src.mqtt.subscriber.settings") as mock_settings:
            mock_settings.mqtt_enabled = True
            mock_settings.mqtt_broker = "localhost"
            mock_settings.mqtt_port = 1883
            mock_settings.mqtt_topic = "topic"
            mock_settings.mqtt_username = None
            mock_settings.mqtt_password = None

            with patch("src.mqtt.subscriber.asyncio.create_task") as mock_task:
                result = await start_mqtt_subscriber()
                assert isinstance(result, MQTTSubscriber)
                mock_task.assert_called_once()
