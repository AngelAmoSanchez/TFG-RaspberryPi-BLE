import logging
from datetime import datetime, timedelta
from typing import List

from ..domain.models import Device, Statistics
from ..domain.ports import BluetoothScannerPort, DeviceRepositoryPort
from ..domain.services import (
    AnonymizationService,
    PeopleEstimatorService,
    PermanenceService,
    ZoneClassifierService,
)

logger = logging.getLogger(__name__)


class ProcessDetectionsUseCase:
    """Procesar dispositivos mediante detecciones Bluetooth BLE

    Su flujo es el siguiente:
    1. Escanear dispositivos BLE
    2. Anonimizar direcciones MAC
    3. Clasificar por zona según el RSSI capturado
    4. Verificar tiempo de permanencia
    5. Guardar dispositivos en base de datos
    """

    def __init__(
        self,
        scanner: BluetoothScannerPort,
        repository: DeviceRepositoryPort,
        zone_classifier: ZoneClassifierService,
        anonymizer: AnonymizationService,
        permanence_service: PermanenceService,
    ):
        self.scanner = scanner
        self.repository = repository
        self.zone_classifier = zone_classifier
        self.anonymizer = anonymizer
        self.permanence_service = permanence_service

    async def execute(self) -> List[Device]:
        """Ejecuta el flujo completo del sistema.

        Returns:
            Lista de dispositivos procesados y guardados
        """
        logger.info("=== Iniciando procesamiento de detecciones ===")

        # 1. Escanear dispositivos Bluetooth BLE
        detections = await self.scanner.scan_devices()
        logger.info(f"Escaneados {len(detections)} dispositivos BLE")

        if not detections:
            logger.warning("No se detectaron dispositivos")
            return []

        processed_devices = []
        time_window = datetime.now() - timedelta(minutes=10)

        for detection in detections:
            try:
                # 2. Anonimizar MAC
                device_hash = self.anonymizer.hash_mac(detection.mac_address)

                # 3. Clasificar por zona según RSSI
                zone = self.zone_classifier.classify(detection.rssi)

                # 4. Verificar si ya existe par saber si hay permanencia
                existing = await self.repository.get_by_hash(device_hash, time_window)

                if existing:
                    # Si yase detectó antes se verifica si cumple el tiempo mínimo
                    is_permanent = self.permanence_service.is_permanent(
                        existing.timestamp, detection.timestamp
                    )

                    if not is_permanent:
                        logger.debug(f"Dispositivo {device_hash[:8]}... ignorado (sin permanencia)")
                        continue  # Ignorar si solo está de paso

                    permanence_mins = self.permanence_service.calculate_permanence(
                        existing.timestamp, detection.timestamp
                    )
                    logger.debug(
                        f"Dispositivo {device_hash[:8]}... permanencia: {permanence_mins:.1f} min"
                    )

                # 5. Crear entidad de dominio
                device = Device.from_detection(detection, device_hash, zone)

                # 6. Guardar en base de datos
                saved = await self.repository.save(device)
                processed_devices.append(saved)

                logger.debug(
                    f"OK - Guardado: {device_hash[:8]}... | Zona: {zone.value} | RSSI: {detection.rssi}"
                )

            except Exception as e:
                logger.error(f"ERROR - Error procesando dispositivo: {e}")
                continue

        logger.info(
            f"=== Procesamiento completado: {len(processed_devices)} dispositivos guardados ==="
        )
        return processed_devices


class GetStatisticsUseCase:
    """Obtener estadísticas agregadas"""

    def __init__(self, repository: DeviceRepositoryPort, estimator: PeopleEstimatorService):
        self.repository = repository
        self.estimator = estimator

    async def get_hourly(self, date: datetime) -> List[Statistics]:
        """Obtiene estadísticas por hora con estimación de personas

        Args:
            date: Fecha para obtener estadísticas

        Returns:
            Lista de estadísticas por hora y zona
        """
        logger.info(f"Obteniendo estadísticas por hora para: {date.date()}")

        stats = await self.repository.get_hourly_stats(date)

        # Añadir estimación de personas
        for stat in stats:
            stat.estimated_people = self.estimator.estimate_people(stat.unique_devices)

        logger.info(f"Obtenidas {len(stats)} estadísticas por hora")
        return stats

    async def get_daily(self, start_date: datetime, end_date: datetime) -> List[Statistics]:
        """Obtiene estadísticas por día

        Args:
            start_date: Fecha inicio
            end_date: Fecha fin

        Returns:
            Lista de estadísticas por día y zona
        """
        logger.info(f"Obteniendo estadísticas diarias: {start_date.date()} a {end_date.date()}")

        stats = await self.repository.get_daily_stats(start_date, end_date)

        # Añadir una estimación de personas
        for stat in stats:
            stat.estimated_people = self.estimator.estimate_people(stat.unique_devices)

        logger.info(f"Obtenidas {len(stats)} estadísticas diarias")
        return stats

    async def get_current_summary(self) -> dict:
        """Obtiene resumen de la última hora por zonas para el dashboard en tiempo real

        Returns:
            Dict con resumen por zona
        """
        now = datetime.now()
        stats = await self.get_hourly(now)

        # Filtrar solo por la última hora completa
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_stats = [s for s in stats if s.start_time == current_hour]

        summary = {"timestamp": now.isoformat(), "zones": {}}

        for stat in current_stats:
            summary["zones"][stat.zone.value] = {
                "estimated_people": stat.estimated_people,
                "unique_devices": stat.unique_devices,
                "avg_permanence": round(stat.avg_permanence_minutes, 1),
            }

        return summary


class ExportDataUseCase:
    """Exportar datos a CSV"""

    def __init__(self, repository: DeviceRepositoryPort):
        self.repository = repository

    async def execute(self, start_date: datetime, end_date: datetime) -> str:
        """Exporta los datos en las fechas definidas a un CSV

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Path del archivo CSV generado
        """
        logger.info(f"Exportando datos: {start_date.date()} a {end_date.date()}")

        csv_path = await self.repository.export_to_csv(start_date, end_date)

        logger.info(f"OK - Exportación completada: {csv_path}")
        return csv_path
