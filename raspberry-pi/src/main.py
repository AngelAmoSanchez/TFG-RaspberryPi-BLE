import asyncio
import hashlib
import logging
import os
import signal
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import List
from zoneinfo import ZoneInfo

from config import AgentConfig, load_config_from_file
from scanner.ble_scanner import BLEScanner, MockBLEScanner
from scanner.detection import Detection, Device, Zone
from sender.http_client import HTTPClient
from sender.mqtt_client import MockMQTTClient, MQTTClient

SPAIN_TZ = ZoneInfo("Europe/Madrid")

# Configurar logging
log_dir = "./logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Mantiene hasta 3 archivos de 5MB cada uno.
rotating_handler = RotatingFileHandler(
    os.path.join(log_dir, "iot-agent.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), rotating_handler],
)
logger = logging.getLogger(__name__)


class DetectionProcessor:
    """Domain Service - Procesa detecciones crudas"""

    def __init__(self, near_threshold: int = -60, medium_threshold: int = -75):
        """
        Args:
            near_threshold: RSSI para zona cercana
            medium_threshold: RSSI para zona media
        """
        self.near_threshold = near_threshold
        self.medium_threshold = medium_threshold
        logger.info(
            f"Procesador de detecciones inicializado"
            f"(NEAR ≥ {near_threshold} dBm, MEDIUM ≥ {medium_threshold} dBm)"
        )

    def anonymize_mac(self, mac_address: str) -> str:
        """Anonimiza dirección MAC usando SHA-256

        Args:
            mac_address: Dirección MAC del dispositivo

        Devuelve:
            Hash SHA-256 en hexadecimal (64 caracteres)
        """
        normalized_mac = mac_address.replace(":", "").replace("-", "").upper()

        hash_object = hashlib.sha256(normalized_mac.encode())
        return hash_object.hexdigest()

    def classify_zone(self, rssi: int) -> Zone:
        """Clasifica dispositivo en zona según RSSI

        Args:
            rssi: Señal recibida en dBm (negativo)

        Devuelve:
            Zone correspondiente
        """
        if rssi >= self.near_threshold:
            return Zone.NEAR
        elif rssi >= self.medium_threshold:
            return Zone.MEDIUM
        else:
            return Zone.FAR

    def process_detections(self, detections: List[Detection]) -> List[Device]:
        """Procesa lista de detecciones crudas

        Args:
            detections: Lista de detecciones del scanner

        Devuelve:
            Lista de detecciones procesadas y anonimizadas
        """
        processed = []

        for detection in detections:
            try:
                device_hash = self.anonymize_mac(detection.mac_address)

                zone = self.classify_zone(detection.rssi)

                processed_detection = Device.from_detection(
                    detection=detection, device_hash=device_hash, zone=zone
                )

                processed.append(processed_detection)

            except Exception as e:
                logger.warning(f"Error procesando detección: {e}")
                continue

        logger.debug(f"Procesadas {len(processed)}/{len(detections)} detecciones")
        return processed


class IoTAgent:
    """Agente IoT principal"""

    def __init__(self, config: AgentConfig):
        """
        Args:
            config: Configuración del agente
        """
        self.config = config
        self.running = False

        self.processor = DetectionProcessor(
            near_threshold=config.scanner.near_threshold,
            medium_threshold=config.scanner.medium_threshold,
        )

        self.scanner = self._init_scanner()

        self.client = self._init_client()

        logger.info(f"Agente IoT inicializado\n{config}")

    def _init_scanner(self):
        """Inicializa el scanner BLE según configuración"""
        if self.config.scanner.use_mock:
            logger.info("OK - Usando escáner MOCK (simulado)")
            return MockBLEScanner(num_devices=5)
        else:
            logger.info("OK - Usando escáner BLE real (Bleak)")
            return BLEScanner(scan_duration=self.config.scanner.scan_duration)

    def _init_client(self):
        """Inicializa el cliente de comunicación según modo"""
        if self.config.communication_mode == "mqtt":
            logger.info("Usando modo de comunicación MQTT")

            if not self.config.mqtt.broker or self.config.mqtt.broker == "broker.emqx.io":
                logger.warning("Sin broker MQTT configurado, se usará MockMQTTClient (simulado)")
                return MockMQTTClient(device_id=self.config.device_id)

            return MQTTClient(
                broker=self.config.mqtt.broker,
                port=self.config.mqtt.port,
                topic=self.config.mqtt.topic,
                device_id=self.config.device_id,
                config=self.config,
                username=self.config.mqtt.username,
                password=self.config.mqtt.password,
                max_buffer_size=self.config.mqtt.max_buffer_size,
            )

        elif self.config.communication_mode == "http":
            # Modo HTTP
            logger.info("Usando modo de comunicación HTTP")

            return HTTPClient(
                base_url=self.config.http.base_url,
                device_id=self.config.device_id,
                config=self.config,
                api_key=self.config.http.api_key,
                timeout=self.config.http.timeout,
            )

        else:
            raise ValueError(f"Modo de comunicación no válido: {self.config.communication_mode}")

    async def run(self):
        """Ejecuta el agente en loop infinito

        Flujo:
        1. Escanear dispositivos BLE
        2. Procesar y anonimizar detecciones
        3. Enviar al cloud backend
        4. Esperar intervalo
        5. Repetir
        """
        logger.info("=" * 60)
        logger.info("Agente IoT iniciado...")
        logger.info("=" * 60)

        if not self.client.connect():
            logger.error("No se pudo conectar al backend, entrando en modo offline")

        self.running = True
        cycle_count = 0

        try:
            while self.running:
                cycle_count += 1
                logger.info(f"\n{'=' * 60}")
                logger.info(
                    f"Ciclo de Escaneo #{cycle_count} - {datetime.now(SPAIN_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
                )
                logger.info(f"{'=' * 60}")

                # 1. Escanear dispositivos BLE
                detections = await self.scanner.scan_devices()

                if not detections:
                    logger.warning("No devices detected in this scan")
                else:
                    # 2. Procesar y anonimizardetecciones
                    processed_detections = self.processor.process_detections(detections)

                    zones_count = {
                        Zone.NEAR: sum(1 for d in processed_detections if d.zone == Zone.NEAR),
                        Zone.MEDIUM: sum(1 for d in processed_detections if d.zone == Zone.MEDIUM),
                        Zone.FAR: sum(1 for d in processed_detections if d.zone == Zone.FAR),
                    }

                    logger.info(
                        f" Distribución de zonas: "
                        f"NEAR={zones_count[Zone.NEAR]}, "
                        f"MEDIUM={zones_count[Zone.MEDIUM]}, "
                        f"FAR={zones_count[Zone.FAR]}"
                    )

                    # 3. Enviar al cloud
                    if processed_detections:
                        success = self.client.publish_detections(processed_detections)

                        if not success:
                            logger.error("Publicación de detecciones fallida")

                        # Mostrar estado del buffer si existe
                        buffer_size = self.client.get_buffer_size()
                        if buffer_size > 0:
                            logger.warning(f"El buffer tiene {buffer_size} mensajes pendientes")

                if self.client.is_connected():
                    logger.info("OK - Cliente conectado y operativo")
                else:
                    logger.warning("ERROR - Cliente offline (mensajes en buffer)")

                # 4. Esperar intervalo
                logger.info(
                    f"Esperando {self.config.scanner.scan_interval}s hasta el próximo escaneo..."
                )
                await asyncio.sleep(self.config.scanner.scan_interval)

        except asyncio.CancelledError:
            logger.info("Agente recibió señal de apagado")
        except Exception as e:
            logger.error(f"Error fatal en el agente: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Apaga el agente de forma limpia"""
        logger.info("Apagando el agente...")
        self.running = False

        self.client.disconnect()

        logger.info("OK - Agente apagado correctamente")


def signal_handler(signum, frame):
    """Handler de señales para shutdown limpio"""
    logger.info(f"\nRecibida señal {signum}, apagando...")
    sys.exit(0)


async def main():
    """Entry point principal"""
    try:
        # Cargar configuración
        config = load_config_from_file(".env")

        # Configurar nivel de logging
        logging.getLogger().setLevel(config.log_level)

        # Crear y ejecutar agente
        agent = IoTAgent(config)

        # Manejar señales para shutdown limpio
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Ejecutar agente
        await agent.run()

    except ValueError as e:
        logger.error(f"Error de configuración: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ejecutar agente
    asyncio.run(main())
