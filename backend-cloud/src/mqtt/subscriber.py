import asyncio
import json
import logging
import ssl
from typing import Optional

try:
    import paho.mqtt.client as mqtt

    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

from ..config import settings
from ..database.connection import database
from ..services.detection_processor import DetectionProcessorService
from ..services.device_service import DeviceService

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """MQTT subscriber para recibir las detecciones de la Raspberry Pi"""

    def __init__(
        self,
        broker: str,
        port: int,
        topic: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Args:
            broker: dirección del broker MQTT
            port: puerto del broker MQTT
            topic: Topic al que está suscrito
            username: usuario MQTT (optional)
            password: contraseña MQTT (optional)
        """
        if not MQTT_AVAILABLE:
            raise ImportError("Dependencia paho-mqtt no está instalada")

        self.broker = broker
        self.port = port
        self.topic = topic
        self.username = username
        self.password = password

        self.client = None
        self.connected = False
        self.running = False
        self.loop = None  # Se asignará al iniciar run()

        # Servicios
        self.detection_service = DetectionProcessorService()
        self.device_service = DeviceService()

        logger.info(f"MQTT Subscriber inicializado (broker: {broker}:{port}, topic: {topic})")

    def on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker"""
        if rc == 0:
            self.connected = True
            logger.info("OK - Conectado al broker MQTT")

            client.subscribe(self.topic, qos=1)
            logger.info(f"OK - Subscripto al topic: {self.topic}")
        else:
            logger.error(f"ERROR - Error en la conexión MQTT (rc={rc})")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        """Callback cuando se desconecta del broker"""
        self.connected = False
        if rc == 0:
            logger.info("MQTT desconectado")
        else:
            logger.warning(f"ERROR - MQTT desconectado inesperadamente (rc={rc})")

    def on_message(self, client, userdata, msg):
        """Callback cuando se recibe un mensaje"""
        try:
            payload = json.loads(msg.payload.decode())

            device_id = payload.get("device_id")
            detections = payload.get("detections", [])

            if not device_id:
                logger.warning("WARN - Falta el mensaje device_id")
                return

            logger.info(f"Recibidas {len(detections)} detecciones desde {device_id}")

            # Programar el procesamiento en el bucle asyncio principal
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.process_message(device_id, detections), self.loop
                )
            else:
                logger.error("ERROR - No hay bucle asyncio disponible para procesar el mensaje")

        except json.JSONDecodeError as e:
            logger.error(f"ERROR - JSON inválido en el mensaje: {e}")
        except Exception as e:
            logger.error(f"ERROR - Error procesando mensaje: {e}", exc_info=True)

    async def process_message(self, device_id: str, detections: list):
        """Procesa el mensaje recibido y lo guarda en la base de datos

        Args:
            device_id: IoT agent identifier
            detections: List of detection dicts
        """
        try:
            async with database.get_session() as db:
                # Actualiza el timestamp de last_seen del dispositivo
                await self.device_service.update_last_seen(db, device_id)

                # Guarda las detecciones
                if detections:
                    await self.detection_service.save_bulk_detections(db, detections, device_id)
                    logger.info(f"OK - Guardadas {len(detections)} detecciones")

                await db.commit()

        except Exception as e:
            logger.error(f"ERROR - Error procesando mensajes: {e}", exc_info=True)

    def connect(self):
        """Conecta al broker MQTT"""
        try:
            # Crea el cliente
            self.client = mqtt.Client(
                client_id="backend-subscriber", protocol=mqtt.MQTTv311, clean_session=True
            )

            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Configurar TLS para el puerto 8883 y broker EMQX Cloud (certificado de Let's Encrypt)
            self.client.tls_set(
                ca_certs=None,
                certfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS
            )

            # Callbacks
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message

            logger.info(f"Conectando con el MQTT broker {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)

            self.client.loop_start()

            return True

        except Exception as e:
            logger.error(f"ERROR - Error de conexión con MQTT: {e}")
            return False

    def disconnect(self):
        """Desconecta del broker MQTT"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT desconectado")

    async def run(self):
        """Ejecuta el subscriber (mantiene la conexión activa)"""
        self.running = True
        # Guarda referencia al bucle asyncio en ejecución
        self.loop = asyncio.get_running_loop()

        if not self.connect():
            logger.error("ERROR - No se pudo conectar al MQTT broker")
            return

        try:
            while self.running:
                await asyncio.sleep(1)

                if not self.connected:
                    logger.warning("WARN - Conexión con MQTT perdida, reconectando...")
                    self.connect()

        except asyncio.CancelledError:
            logger.info("MQTT subscriber detenido")
        finally:
            self.disconnect()

    def stop(self):
        """Detiene el subscriber"""
        self.running = False


async def start_mqtt_subscriber():
    """Ejecuta MQTT subscriber si está habilitado"""
    if not settings.mqtt_enabled:
        logger.info("MQTT subscriber deshabilitado")
        return None

    if not settings.mqtt_broker:
        logger.warning("MQTT broker no configurado")
        return None

    subscriber = MQTTSubscriber(
        broker=settings.mqtt_broker,
        port=settings.mqtt_port,
        topic=settings.mqtt_topic,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
    )

    asyncio.create_task(subscriber.run())

    return subscriber
