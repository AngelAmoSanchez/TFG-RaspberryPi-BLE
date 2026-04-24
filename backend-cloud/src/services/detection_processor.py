import logging
from datetime import datetime
from typing import Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Detection, ZoneEnum
from ..utils import timezone_utils

logger = logging.getLogger(__name__)


class DetectionProcessorService:
    """Servicio de dominio para procesar detecciones BLE"""

    def __init__(self, devices_per_person: float = 1.5):
        """
        Args:
            devices_per_person: Ratio estimado de dispositivos por persona
        """
        self.devices_per_person = devices_per_person

    @staticmethod
    def verify_hash(device_hash: str) -> bool:
        """Verifica que el hash es un SHA-256 válido

        Args:
            device_hash: Hash de dispositivo a verificar

        Devuelve:
            True si el hash es válido, False en caso contrario
        """
        return len(device_hash) == 64 and all(c in "0123456789abcdef" for c in device_hash.lower())

    @staticmethod
    def classify_zone(
        rssi: int, near_threshold: int = -60, medium_threshold: int = -75
    ) -> ZoneEnum:
        """Clasifica la zona de proximidad según el RSSI

        Args:
            rssi: Señal RSSI del dispositivo detectado
            near_threshold: umbral de RSSI para zona NEAR
            medium_threshold: umbral de RSSI para zona MEDIUM

        Devuelve:
            Classificación de zona (NEAR, MEDIUM, FAR)
        """
        if rssi >= near_threshold:
            return ZoneEnum.NEAR
        elif rssi >= medium_threshold:
            return ZoneEnum.MEDIUM
        else:
            return ZoneEnum.FAR

    def estimate_people(self, unique_devices: int) -> int:
        """Estima el número de personas a partir del número de dispositivos únicos detectados

        Args:
            unique_devices: Número de dispositivos únicos detectados

        Devuelve:
            Estimación del número de personas
        """
        if unique_devices == 0:
            return 0

        estimated = unique_devices / self.devices_per_person
        return max(1, int(round(estimated)))

    async def save_detection(
        self,
        db: AsyncSession,
        device_hash: str,
        rssi: int,
        zone: str,
        device_id: str,
        timestamp: datetime = None,
    ) -> Detection:
        """
        Guarda una detección en la base de datos

        Args:
            db: Sesión de base de datos
            device_hash: Hash del dispositivo detectado (SHA-256)
            rssi: Señal RSSI
            zone: Classificación de zona (NEAR, MEDIUM, FAR)
            device_id: Identificador del agente IoT
            timestamp: Momento de la detección (por defecto: hora actual)

        Devuelve:
            Creado objeto Detection
        """
        if not self.verify_hash(device_hash):
            raise ValueError(f"ERROR - Hash inválido: {device_hash}")

        if rssi > 0 or rssi < -120:
            raise ValueError(f"ERROR - RSSI inválido: {rssi}")

        try:
            zone_enum = ZoneEnum(zone)
        except ValueError:
            raise ValueError(f"ERROR - Zona inválida: {zone}")

        # Crear detección
        detection = Detection(
            device_hash=device_hash,
            rssi=rssi,
            zone=zone_enum,
            device_id=device_id,
            timestamp=timestamp or timezone_utils.now(),
        )

        db.add(detection)
        await db.flush()

        logger.debug(f"Detección guardada: {device_hash[:16]}... | {rssi} dBm | {zone}")

        return detection

    async def save_bulk_detections(
        self, db: AsyncSession, detections_data: List[Dict], device_id: str
    ) -> List[Detection]:
        """Guarda múltiples detecciones en la base de datos de forma eficiente

        Args:
            db: Sesión de base de datos
            detections_data: Lista de diccionarios de detecciones
            device_id: Identificador del agente IoT

        Devuelve:
            Lista de objetos Detection creados
        """
        detections = []

        for data in detections_data:
            try:
                # Parsear marcas de tiempo
                timestamp_str = data.get("timestamp")
                if timestamp_str:
                    timestamp = timezone_utils.parse_datetime(timestamp_str)
                else:
                    timestamp = timezone_utils.now()

                # Crear detección
                detection = Detection(
                    device_hash=data["device_hash"],
                    rssi=data["rssi"],
                    zone=data["zone"].lower(),
                    device_id=device_id,
                    timestamp=timestamp,
                )

                detections.append(detection)

            except Exception as e:
                logger.warning(f"WARN - Saltada detección inválida: {e}")
                continue

        # Insertar detecciones válidas en bloque
        if detections:
            db.add_all(detections)
            await db.flush()
            logger.info(f"Bloque de {len(detections)} detecciones guardadas desde {device_id}")

        return detections

    async def get_recent_detections(
        self, db: AsyncSession, limit: int = 100, zone: ZoneEnum = None
    ) -> List[Detection]:
        """Obtiene detecciones recientes

        Args:
            db: Sesión de base de datos
            limit: Número máximo de detecciones
            zone: Filtrar por zona (opcional)

        Devuelve:
            Lista de objetos Detection
        """
        query = select(Detection).order_by(Detection.timestamp.desc()).limit(limit)

        if zone:
            query = query.where(Detection.zone == zone)

        result = await db.execute(query)
        detections = result.scalars().all()

        return list(detections)

    async def get_unique_devices_count(
        self, db: AsyncSession, start_time: datetime, end_time: datetime, zone: ZoneEnum = None
    ) -> int:
        """Cuenta el número de dispositivos únicos detectados en un rango de tiempo

        Args:
            db: Sesión de base de datos
            start_time: Inicio del rango de tiempo
            end_time: Fin del rango de tiempo
            zone: Filtrar por zona (opcional)

        Devuelve:
            Conteo de hashes de dispositivos únicos
        """
        query = select(func.count(func.distinct(Detection.device_hash)))
        query = query.where(and_(Detection.timestamp >= start_time, Detection.timestamp < end_time))

        if zone:
            query = query.where(Detection.zone == zone)

        result = await db.execute(query)
        count = result.scalar()

        return count or 0
