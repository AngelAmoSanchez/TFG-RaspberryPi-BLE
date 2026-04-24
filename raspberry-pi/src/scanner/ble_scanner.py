import asyncio
import logging
from datetime import datetime
from typing import List

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData

    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    BleakScanner = None
    BLEDevice = None
    AdvertisementData = None

from zoneinfo import ZoneInfo

from .detection import Detection

SPAIN_TZ = ZoneInfo("Europe/Madrid")

logger = logging.getLogger(__name__)


class BLEScanner:
    """Escáner BLE usando Bleak (escaneo pasivo)"""

    def __init__(self, scan_duration: int = 10):
        """
        Args:
            scan_duration: Duración del escaneo en segundos
        """
        if not BLEAK_AVAILABLE:
            raise ImportError("ERROR - Bleak no se encuentra instalado.")

        self.scan_duration = scan_duration
        self._devices_cache = {}
        logger.info(f"Escaneo BLE inicializado ({scan_duration}s)")

    async def scan_devices(self) -> List[Detection]:
        """Escanea dispositivos BLE cercanos

        Returns:
            Lista de detecciones con MAC, RSSI y timestamp
        """
        logger.info(f"Iniciando escaneo BLE ({self.scan_duration}s)...")

        self._devices_cache.clear()

        try:
            # Callback para recibir dispositivos en tiempo real
            def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
                """Callback llamado por cada dispositivo detectado"""
                rssi = advertisement_data.rssi

                # Si ya detectamos la MAC, actualizar solo si RSSI es más cercano
                if device.address in self._devices_cache:
                    if rssi > self._devices_cache[device.address].rssi:
                        self._devices_cache[device.address] = Detection(
                            mac_address=device.address,
                            rssi=rssi,
                            timestamp=datetime.now(SPAIN_TZ),
                            device_name=device.name,
                        )
                else:
                    # Si es la primera vez que detectamos el dispositivo
                    try:
                        self._devices_cache[device.address] = Detection(
                            mac_address=device.address,
                            rssi=rssi,
                            timestamp=datetime.now(SPAIN_TZ),
                            device_name=device.name,
                        )
                    except ValueError as e:
                        logger.debug(f"Detección invalida: {e}")

            # Ejecutar escaneo
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(self.scan_duration)
            await scanner.stop()

            # Crear una lista para el cache de detecciones únicas
            detections = list(self._devices_cache.values())

            logger.info(f"OK - Escaneo completado: {len(detections)} dispositivos detectados")

            # Log de dispositivos detectados
            for det in detections:
                logger.debug(
                    f"  Dispositivo: {det.mac_address[:8]}... | "
                    f"RSSI: {det.rssi:3d} dBm | "
                    f"Nombre: {det.device_name or 'Desconocido'}"
                )

            if len(detections) > 5:
                logger.debug(f"  ... y {len(detections) - 5} dispositivos más")

            return detections

        except Exception as e:
            logger.error(f"ERROR - Error en escaneo BLE simple: {e}", exc_info=True)
            return []

    def is_available(self) -> bool:
        """Verifica si el adaptador BLE está disponible"""
        return BLEAK_AVAILABLE


class MockBLEScanner:
    """Mock para probar el sistema sin necesidad del hardware Bluetooth
    Genera detecciones realistas de manera simulada"""

    def __init__(self, num_devices: int = 5):
        """
        Args:
            num_devices: Número de dispositivos simulados a generar
        """
        self.num_devices = num_devices

        # MACs simuladas de diferentes tipos de dispositivos
        self._mock_devices = [
            ("A1:B2:C3:D4:E5:F1", "iPhone 13", -55),
            ("A1:B2:C3:D4:E5:F2", "Samsung Galaxy S3", -62),
            ("A1:B2:C3:D4:E5:F3", "Apple Watch", -48),
            ("A1:B2:C3:D4:E5:F4", "Xiaomi Band", -75),
            ("A1:B2:C3:D4:E5:F5", "Airpods Pro", -58),
            ("A1:B2:C3:D4:E5:F6", "Unknown Device", -80),
            ("A1:B2:C3:D4:E5:F7", "Smartwatch", -65),
            ("A1:B2:C3:D4:E5:F8", "Fitness Smartwatch", -72),
        ]
        logger.info(f"[MOCK] Escáner inicializado (simula {num_devices} dispositivos)")

    async def scan_devices(self) -> List[Detection]:
        """Simula escaneo BLE con datos realistas sin hardware"""
        import random

        logger.info("[MOCK] Simulando escaneo BLE...")

        # Simular la latencia del escaneo
        await asyncio.sleep(1)

        # Seleccionar dispositivos aleatorios
        num_to_detect = random.randint(
            max(1, self.num_devices - 2),
            min(len(self._mock_devices), self.num_devices + 2),
        )

        selected_devices = random.sample(self._mock_devices, num_to_detect)

        detections = []
        timestamp = datetime.now(SPAIN_TZ)

        for mac, name, base_rssi in selected_devices:
            # Añadimos diferentes valores de RSSI (en rango de 5 dBm)
            rssi = base_rssi + random.randint(-5, 5)

            detection = Detection(mac_address=mac, rssi=rssi, timestamp=timestamp, device_name=name)
            detections.append(detection)

        logger.info(f"[MOCK] OK - Generados {len(detections)} dispositivos simulados")

        for det in detections:
            logger.debug(
                f"  [MOCK] - {det.mac_address} | RSSI: {det.rssi:3d} dBm | {det.device_name}"
            )

        return detections

    def is_available(self) -> bool:
        """Mock siempre está disponible"""
        return True
