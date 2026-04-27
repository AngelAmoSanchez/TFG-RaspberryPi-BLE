import json
import logging
import time
from datetime import datetime
from typing import List, Optional

try:
    import paho.mqtt.client as mqtt

    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

from zoneinfo import ZoneInfo

from scanner.detection import Device

SPAIN_TZ = ZoneInfo("Europe/Madrid")

logger = logging.getLogger(__name__)


class MQTTClient:
    """Cliente MQTT para publicar detecciones al cloud backend con buffer local, reconexión automática y QoS 1"""

    def __init__(
        self,
        broker: str,
        port: int,
        topic: str,
        device_id: str,
        config=None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_buffer_size: int = 100,
    ):
        """
        Args:
            broker: Dirección del broker MQTT
            port: Puerto MQTT
            topic: Topic donde publicar
            device_id: ID de la Raspberry Pi
            config: Objeto de configuración (opcional)
            username: Usuario MQTT (opcional)
            password: Contraseña MQTT (opcional)
            max_buffer_size: Tamaño máximo del buffer offline
        """
        if not MQTT_AVAILABLE:
            raise ImportError("ERROR - Dependencia paho-mqtt no instalada")

        self.broker = broker
        self.port = port
        self.topic = topic
        self.device_id = device_id
        self.config = config
        self.username = username
        self.password = password
        self.max_buffer_size = max_buffer_size

        # Buffer para mensajes cuando el sistema esté offline
        self._buffer: List[dict] = []

        # Estado de conexión
        self._connected = False
        self._client = None

        logger.info(
            f"Cliente MQTT inicializado (broker: {broker}:{port}, "
            f"topic: {topic}, dispositivo: {device_id})"
        )

    def connect(self) -> bool:
        """Conecta al broker MQTT

        Devuelve:
            True si se conecta exitosamente, False si no pudo conectarse
        """
        try:
            # Crear cliente MQTT
            self._client = mqtt.Client(
                client_id=f"rpi-agent-{self.device_id}",
                protocol=mqtt.MQTTv311,
                clean_session=True,
            )

            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)

            # Callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_publish = self._on_publish

            # Conectar
            logger.info(f"Conectando al broker MQTT {self.broker}:{self.port}...")
            self._client.connect(self.broker, self.port, keepalive=60)

            # Iniciar loop
            self._client.loop_start()

            timeout = 10
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self._connected:
                logger.info("OK - MQTT conectado existosamente")
                self._flush_buffer()
                return True
            else:
                logger.error("ERROR - Error timeout de conexión MQTT")
                return False

        except Exception as e:
            logger.error(f"ERROR -Error de conexión MQTT: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Desconecta del broker MQTT"""
        if self._client:
            logger.info("Desconectando del broker MQTT...")
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("OK - MQTT desconectado")

    def publish_detections(self, detections: List[Device]) -> bool:
        """Publica lista de detecciones al broker MQTT

        Args:
            detections: Lista de detecciones ya procesadas

        Devuelve:
            True si se publicó exitosamente (o se guardó en buffer)
        """
        if not detections:
            logger.debug("Sin detecciones para publicar")
            return True

        # Crear mensaje MQTT
        message = {
            "device_id": self.device_id,
            "timestamp": datetime.now(SPAIN_TZ).isoformat(),
            "detections": [det.to_dict() for det in detections],
        }

        if self.config:
            if self.config.device_name:
                message["name"] = self.config.device_name
            if self.config.device_location:
                message["location"] = self.config.device_location


        # Intento de publicar
        if self._connected and self._client:
            return self._publish_message(message)
        else:
            # Si no está conectado, guarda en el buffer
            logger.warning(
                f"WARN - MQTT no está conectado, guardando mensaje en buffer ({len(self._buffer)}/{self.max_buffer_size})"
            )
            return self._buffer_message(message)

    def _publish_message(self, message: dict) -> bool:
        """Publica mensaje al broker

        Args:
            message: Diccionario con datos a publicar

        Devuelve:
            True si se publicó exitosamente
        """
        try:
            payload = json.dumps(message)

            result = self._client.publish(topic=self.topic, payload=payload, qos=1, retain=False)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(
                    f"OK - Publicadas {len(message['detections'])} detecciones" f"to {self.topic}"
                )
                return True
            else:
                logger.error(f"ERROR - Publicación fallida con código {result.rc}")
                # Guardar en buffer para reintentar después
                self._buffer_message(message)
                return False

        except Exception as e:
            logger.error(f"ERROR - Error publicando el mensaje: {e}")
            self._buffer_message(message)
            return False

    def _buffer_message(self, message: dict) -> bool:
        """Guarda el mensaje en buffer local

        Args:
            message: Mensaje a guardar

        Devuelve:
            True si se guardó exitosamente
        """
        if len(self._buffer) >= self.max_buffer_size:
            logger.warning(
                f"Buffer lleno ({self.max_buffer_size}), " f"descartando el mensaje más antiguo"
            )
            self._buffer.pop(0)

        self._buffer.append(message)
        logger.debug(f"Mensaje guardado en el buffer (total: {len(self._buffer)})")
        return True

    def _flush_buffer(self):
        """Envía todos los mensajes del buffer al reconectar con el backend"""
        if not self._buffer:
            return

        logger.info(f"Publicando mensajes del buffer ({len(self._buffer)})...")

        messages_to_send = self._buffer.copy()
        self._buffer.clear()

        for message in messages_to_send:
            if not self._publish_message(message):
                # Si falla, volver a guardar
                logger.warning(
                    "ERROR - Error al publicar mensaje del buffer, reintentando más tarde"
                )
                break

        if not self._buffer:
            logger.info("OK - Mensajes del buffer publicados exitosamente")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker"""
        if rc == 0:
            self._connected = True
            logger.info(f"OK - MQTT conectado (rc={rc})")
        else:
            self._connected = False
            logger.error(f"ERROR - Error de conexión con MQTT (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        """Callback cuando se desconecta del broker"""
        self._connected = False
        if rc == 0:
            logger.info("OK - MQTT desconectado")
        else:
            logger.warning(f"WARNING - MQTT desconectado repentinamente (rc={rc})")

    def _on_publish(self, client, userdata, mid):
        """Callback cuando se completa una publicación"""
        logger.debug(f"Mensaje {mid} publicado exitosamente")

    def is_connected(self) -> bool:
        """Devuelve True si está conectado al broker"""
        return self._connected

    def get_buffer_size(self) -> int:
        """Devuelve el tamaño actual del buffer"""
        return len(self._buffer)


class MockMQTTClient:
    """Mock MQTT client para simular la publicación exitosa y logueo de mensajes"""

    def __init__(self, device_id: str, **kwargs):
        """
        Args:
            device_id: ID del dispositivo
            **kwargs: Ignorados (compatibilidad con MQTTClient real)
        """
        self.device_id = device_id
        self._connected = True
        logger.info(f"[MOCK] Cliente MQTT inicializado (device: {device_id})")

    def connect(self) -> bool:
        """Simula conexión exitosa"""
        logger.info("OK - [MOCK] MQTT conectado (simulado)")
        self._connected = True
        return True

    def disconnect(self):
        """Simula desconexión"""
        logger.info("OK - [MOCK] MQTT desconectado (simulado)")
        self._connected = False

    def publish_detections(self, detections: List[Device]) -> bool:
        """Simula publicación de detecciones

        Args:
            detections: Lista de detecciones

        Devuelve:
            True siempre (simula éxito)
        """
        if not detections:
            return True

        logger.info(
            f"OK - [MOCK] Publicará {len(detections)} detecciones " f"(device: {self.device_id})"
        )

        for det in detections[:3]:
            logger.debug(
                f"  [MOCK] Hash: {det.device_hash[:16]}... | "
                f"RSSI: {det.rssi:3d} dBm | "
                f"Zona: {det.zone.value}"
            )

        if len(detections) > 3:
            logger.debug(f"  [MOCK] ... y {len(detections) - 3} más")

        return True

    def is_connected(self) -> bool:
        """Devuelve True siempre (simula conexión)"""
        return self._connected

    def get_buffer_size(self) -> int:
        """Devuelve 0 siempre (no hay buffer en mock)"""
        return 0
