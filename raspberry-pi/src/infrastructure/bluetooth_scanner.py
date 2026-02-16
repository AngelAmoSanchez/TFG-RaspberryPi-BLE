import asyncio
from datetime import datetime
from typing import List
import logging

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
except ImportError:
    BleakScanner = None
    BLEDevice = None
    AdvertisementData = None

from ..domain.models import Detection
from ..domain.ports import BluetoothScannerPort

logger = logging.getLogger(__name__)


class BleakBLEScanner(BluetoothScannerPort):
    """ Adaptador para el escaneo BLE usando Bleak. """

    def __init__(self, scan_duration: int = 20):
        """
        Args:
            scan_duration: Duración del escaneo en segundos
        """
        if BleakScanner is None:
            raise ImportError("ERROR - Bleak no se encuentra instalado.")

        self.scan_duration = scan_duration
        self._devices_cache = {}

    async def scan_devices(self) -> List[Detection]:
        """ Escanea dispositivos BLE cercanos

        Returns:
            Lista de detecciones con MAC, RSSI y timestamp
        """
        logger.info(f"Iniciando escaneo BLE ({self.scan_duration}s)...")

        self._devices_cache.clear()
        detections = []

        try:
            # Callback para recibir dispositivos detectados
            def detection_callback(
                device: BLEDevice, advertisement_data: AdvertisementData
            ):
                """ Callback llamado por cada dispositivo detectado
                Se ejecuta en tiempo real durante el escaneo
                """

                rssi = advertisement_data.rssi
                # Para evitar duplicados en el mismo escaneo
                if device.address in self._devices_cache:
                    # Si ya lo detectamos entonces actualizamos RSSI si es más cercano
                    if rssi > self._devices_cache[device.address].rssi:
                        self._devices_cache[device.address] = Detection(
                            mac_address=device.address,
                            rssi=rssi,
                            timestamp=datetime.now(),
                            device_name=device.name,
                        )
                else:
                    # Si es la primera vez que detectamos el dispositivo
                    self._devices_cache[device.address] = Detection(
                        mac_address=device.address,
                        rssi=rssi,
                        timestamp=datetime.now(),
                        device_name=device.name,
                    )

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
                    f"  - {det.mac_address[:8]}... | RSSI: {det.rssi} dBm | "
                    f"Name: {det.device_name or 'Unknown'}"
                )

        except Exception as e:
            logger.error(f"ERROR - Error durante escaneo BLE: {e}")

        return detections

    async def scan_devices_simple(self) -> List[Detection]:
        """
        Método alternativo simplificado usando discover()
        Más simple pero menos control
        """
        try:
            devices = await BleakScanner.discover(
                timeout=self.scan_duration,
                return_adv=True,  # NECESARIO PARA OBTENER EL RSSI!!
            )

            detections = []
            timestamp = datetime.now()

            for device, advertisement_data in devices.values():
                try:
                    detection = Detection(
                        mac_address=device.address,
                        rssi=advertisement_data.rssi,
                        timestamp=timestamp,
                        device_name=device.name,
                    )
                    detections.append(detection)
                except ValueError as e:
                    # Ignorar dispositivos con RSSI inválido
                    logger.debug(f"Dispositivo ignorado: {e}")
                    continue

            logger.info(f"OK - Detectado en escaneo simple {len(detections)} dispositivos BLE")
            return detections

        except Exception as e:
            logger.error(f"ERROR - Error en escaneo BLE simple: {e}")
            return []


class MockBLEScanner(BluetoothScannerPort):
    """ Mock para probar el sistema sin necesidad del hardware Bluetooth
    Genera detecciones realistas de manera simulada """

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

    async def scan_devices(self) -> List[Detection]:
        """ Simula escaneo BLE con datos realistas
        Útil para desarrollo y demos sin hardware """
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
        timestamp = datetime.now()

        for mac, name, base_rssi in selected_devices:
            # Añadimos diferentes valores de RSSI (en rango de 5 dBm)
            rssi = base_rssi + random.randint(-5, 5)

            detection = Detection(
                mac_address=mac, rssi=rssi, timestamp=timestamp, device_name=name
            )
            detections.append(detection)

        logger.info(f"[MOCK] OK: Generados {len(detections)} dispositivos simulados")

        for det in detections:
            logger.debug(
                f"  [MOCK] - {det.mac_address} | RSSI: {det.rssi} dBm | {det.device_name}"
            )

        return detections
