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
    """
    Domain Service - Procesa detecciones crudas
    Implementa:
    - Anonimización de MACs (SHA-256)
    - Clasificación de zonas por RSSI
    - Validación de detecciones
    """

    def __init__(self, near_threshold: int = -60, medium_threshold: int = -75):
        """
        Args:
            near_threshold: RSSI para zona cercana
            medium_threshold: RSSI para zona media
        """
        self.near_threshold = near_threshold
        self.medium_threshold = medium_threshold
        logger.info(
            f"Detection Processor initialized "
            f"(NEAR ≥ {near_threshold} dBm, MEDIUM ≥ {medium_threshold} dBm)"
        )

    def anonymize_mac(self, mac_address: str) -> str:
        """
        Anonimiza dirección MAC usando SHA-256
        Cumple GDPR - hash irreversible

        Args:
            mac_address: Dirección MAC del dispositivo

        Devuelve:
            Hash SHA-256 en hexadecimal (64 caracteres)
        """
        # Normalizar MAC (remover separadores y mayúsculas)
        normalized_mac = mac_address.replace(":", "").replace("-", "").upper()

        # Generar hash SHA-256
        hash_object = hashlib.sha256(normalized_mac.encode())
        return hash_object.hexdigest()

    def classify_zone(self, rssi: int) -> Zone:
        """
        Clasifica dispositivo en zona según RSSI

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
        """
        Procesa lista de detecciones crudas

        Args:
            detections: Lista de detecciones del scanner

        Devuelve:
            Lista de detecciones procesadas y anonimizadas
        """
        processed = []

        for detection in detections:
            try:
                # Anonimizar MAC
                device_hash = self.anonymize_mac(detection.mac_address)

                # Clasificar zona
                zone = self.classify_zone(detection.rssi)

                # Crear detección procesada
                processed_detection = Device.from_detection(
                    detection=detection, device_hash=device_hash, zone=zone
                )

                processed.append(processed_detection)

            except Exception as e:
                logger.warning(f"Error processing detection: {e}")
                continue

        logger.debug(f"Processed {len(processed)}/{len(detections)} detections")
        return processed


class IoTAgent:
    """
    Application Service - Agente IoT principal
    Orquesta el flujo: Escaneo → Procesamiento → Envío
    """

    def __init__(self, config: AgentConfig):
        """
        Args:
            config: Configuración del agente
        """
        self.config = config
        self.running = False

        # Inicializar procesador de detecciones (Domain Service)
        self.processor = DetectionProcessor(
            near_threshold=config.scanner.near_threshold,
            medium_threshold=config.scanner.medium_threshold,
        )

        # Inicializar scanner (Infrastructure Adapter)
        self.scanner = self._init_scanner()

        # Inicializar cliente de comunicación (Infrastructure Adapter)
        self.client = self._init_client()

        logger.info(f"IoT Agent initialized\n{config}")

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
            # Modo MQTT
            logger.info("Using MQTT communication mode")

            # Si no hay broker configurado, usar mock
            if not self.config.mqtt.broker or self.config.mqtt.broker == "broker.emqx.io":
                logger.warning("No MQTT broker configured, using MOCK client")
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
            logger.info("Using HTTP communication mode")

            return HTTPClient(
                base_url=self.config.http.base_url,
                device_id=self.config.device_id,
                config=self.config,
                api_key=self.config.http.api_key,
                timeout=self.config.http.timeout,
            )

        else:
            raise ValueError(f"Unknown communication mode: {self.config.communication_mode}")

    async def run(self):
        """
        Ejecuta el agente en loop infinito

        Flujo:
        1. Escanear dispositivos BLE
        2. Procesar y anonimizar detecciones
        3. Enviar al cloud backend
        4. Esperar intervalo
        5. Repetir
        """
        logger.info("=" * 60)
        logger.info("IoT Agent starting...")
        logger.info("=" * 60)

        # Conectar cliente
        if not self.client.connect():
            logger.error("Failed to connect client, running in offline mode")

        self.running = True
        cycle_count = 0

        try:
            while self.running:
                cycle_count += 1
                logger.info(f"\n{'=' * 60}")
                logger.info(
                    f"Scan Cycle #{cycle_count} - {datetime.now(SPAIN_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
                )
                logger.info(f"{'=' * 60}")

                # 1. Escanear dispositivos BLE
                detections = await self.scanner.scan_devices()

                if not detections:
                    logger.warning("No devices detected in this scan")
                else:
                    # 2. Procesar detecciones (anonimizar + clasificar)
                    processed_detections = self.processor.process_detections(detections)

                    # Log resumen por zonas
                    zones_count = {
                        Zone.NEAR: sum(1 for d in processed_detections if d.zone == Zone.NEAR),
                        Zone.MEDIUM: sum(1 for d in processed_detections if d.zone == Zone.MEDIUM),
                        Zone.FAR: sum(1 for d in processed_detections if d.zone == Zone.FAR),
                    }

                    logger.info(
                        f"Zones distribution: "
                        f"NEAR={zones_count[Zone.NEAR]}, "
                        f"MEDIUM={zones_count[Zone.MEDIUM]}, "
                        f"FAR={zones_count[Zone.FAR]}"
                    )

                    # 3. Enviar al cloud
                    if processed_detections:
                        success = self.client.publish_detections(processed_detections)

                        if not success:
                            logger.error("Failed to publish detections")

                        # Mostrar estado del buffer si existe
                        buffer_size = self.client.get_buffer_size()
                        if buffer_size > 0:
                            logger.warning(f"Buffer has {buffer_size} pending messages")

                # Mostrar estado de conexión
                if self.client.is_connected():
                    logger.info("✓ Client connected and operational")
                else:
                    logger.warning("✗ Client offline (messages buffered)")

                # 4. Esperar intervalo
                logger.info(f"Waiting {self.config.scanner.scan_interval}s until next scan...")
                await asyncio.sleep(self.config.scanner.scan_interval)

        except asyncio.CancelledError:
            logger.info("Agent received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in agent: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Apaga el agente de forma limpia"""
        logger.info("Shutting down IoT Agent...")
        self.running = False

        # Desconectar cliente
        self.client.disconnect()

        logger.info("✓ IoT Agent stopped")


def signal_handler(signum, frame):
    """Manejador de señales para shutdown limpio"""
    logger.info(f"\nReceived signal {signum}, shutting down...")
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
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Ejecutar agente
    asyncio.run(main())
