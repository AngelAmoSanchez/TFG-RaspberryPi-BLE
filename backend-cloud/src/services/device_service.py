import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Device

logger = logging.getLogger(__name__)


class DeviceService:
    """Servicio de dominio para gestionar dispositivos IoT"""

    async def register_device(
        self, db: AsyncSession, device_id: str, name: str = None, location: str = None
    ) -> Device:
        """Registra un nuevo dispositivo

        Args:
            db: Sesión de base de datos
            device_id: Identificador único del dispositivo
            name: Nombre legible del dispositivo
            location: Ubicación física

        Devuelve:
            Objeto Device creado
        """
        # Verificar si el dispositivo ya existe
        existing = await self.get_device(db, device_id)
        if existing:
            logger.info(f"Dispositivo {device_id} ya registrado")
            return existing

        # Crear nuevo dispositivo
        device = Device(
            device_id=device_id,
            name=name or device_id,
            location=location,
            is_active=1,
            last_seen=datetime.now(timezone.utc),
        )

        db.add(device)
        await db.flush()

        logger.info(f"✓ Dispositivo registrado: {device_id}")
        return device

    async def get_device(self, db: AsyncSession, device_id: str) -> Optional[Device]:
        """
        Obtener dispositivo por ID

        Args:
            db: Sesión de base de datos
            device_id: Identificador del dispositivo

        Devuelve:
            Objeto Device o None
        """
        query = select(Device).where(Device.device_id == device_id)
        result = await db.execute(query)
        device = result.scalar_one_or_none()

        return device

    async def update_last_seen(self, db: AsyncSession, device_id: str) -> Optional[Device]:
        """
        Actualiza la marca de tiempo de última detección de un dispositivo

        Args:
            db: Sesión de base de datos
            device_id: Identificador del dispositivo

        Devuelve:
            Objeto Device actualizado
        """
        device = await self.get_device(db, device_id)

        if device:
            device.last_seen = datetime.now(timezone.utc)
            device.is_active = 1
            await db.flush()
            logger.debug(f"Actualizado last_seen para {device_id}")
        else:
            # Si el dispositivo no existe, se registra automáticamente
            logger.warning(f"Dispositivo {device_id} no registrado, auto-registrando...")
            device = await self.register_device(db, device_id)

        return device

    async def get_all_devices(self, db: AsyncSession, active_only: bool = False) -> List[Device]:
        """Obtener todos los dispositivos

        Args:
            db: Sesión de base de datos
            active_only: Solo devolver dispositivos activos

        Devuelve:
            Lista de objetos Device
        """
        query = select(Device).order_by(Device.created_at.desc())

        if active_only:
            query = query.where(Device.is_active == 1)

        result = await db.execute(query)
        devices = result.scalars().all()

        return list(devices)

    async def get_active_devices(
        self, db: AsyncSession, threshold_minutes: int = 60
    ) -> List[Device]:
        """Obtener dispositivos activos en los últimos X minutos

        Args:
            db: Sesión de base de datos
            threshold_minutes: Considerar activo si se ha visto dentro de este tiempo

        Devuelve:
            Lista de objetos Device activos
        """
        threshold = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        query = (
            select(Device).where(Device.last_seen >= threshold).order_by(Device.last_seen.desc())
        )

        result = await db.execute(query)
        devices = result.scalars().all()

        return list(devices)

    async def deactivate_device(self, db: AsyncSession, device_id: str) -> Optional[Device]:
        """Marca un dispositivo como inactivo

        Args:
            db: Sesión de base de datos
            device_id: Identificador del dispositivo

        Devuelve:
            Objeto Device actualizado
        """
        device = await self.get_device(db, device_id)

        if device:
            device.is_active = 0
            await db.flush()
            logger.info(f"Dispositivo {device_id} desactivado")

        return device

    async def activate_device(self, db: AsyncSession, device_id: str) -> Optional[Device]:
        """Marca un dispositivo como activo

        Args:
            db: Sesión de base de datos
            device_id: Identificador del dispositivo

        Devuelve:
            Objeto Device actualizado
        """
        device = await self.get_device(db, device_id)

        if device:
            device.is_active = 1
            device.updated_at = datetime.now(timezone.utc)
            await db.flush()
            logger.info(f"Dispositivo {device_id} activado")

        return device

    async def update_device_info(
        self, db: AsyncSession, device_id: str, name: str = None, location: str = None
    ) -> Optional[Device]:
        """Actualiza la información de un dispositivo

        Args:
            db: Sesión de base de datos
            device_id: Identificador del dispositivo
            name: Nuevo nombre (opcional)
            location: Nueva ubicación (opcional)

        Devuelve:
            Objeto Device actualizado
        """
        device = await self.get_device(db, device_id)

        if device:
            if name is not None:
                device.name = name
            if location is not None:
                device.location = location

            device.last_seen = datetime.now(timezone.utc)
            await db.flush()

            logger.info(f"Información del dispositivo {device_id} actualizada")

        return device

    async def get_device_stats(self, db: AsyncSession, device_id: str) -> dict:
        """Obtiene estadísticas de detecciones para un dispositivo específico

        Args:
            db: Sesión de base de datos
            device_id: Identificador del dispositivo

        Devuelve:
            Diccionario con estadísticas del dispositivo
        """
        from sqlalchemy import func

        from ..database.models import Detection

        device = await self.get_device(db, device_id)

        if not device:
            return None

        # Contar detecciones totales
        count_query = select(func.count(Detection.id)).where(Detection.device_id == device_id)
        total_result = await db.execute(count_query)
        total_detections = total_result.scalar()

        # Obtener primera y última detección
        first_query = (
            select(Detection.timestamp)
            .where(Detection.device_id == device_id)
            .order_by(Detection.timestamp.asc())
            .limit(1)
        )
        first_result = await db.execute(first_query)
        first_detection = first_result.scalar()

        last_query = (
            select(Detection.timestamp)
            .where(Detection.device_id == device_id)
            .order_by(Detection.timestamp.desc())
            .limit(1)
        )
        last_result = await db.execute(last_query)
        last_detection = last_result.scalar()

        return {
            "device_id": device_id,
            "name": device.name,
            "location": device.location,
            "is_active": bool(device.is_active),
            "registered_at": device.created_at.isoformat(),
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "total_detections": total_detections,
            "first_detection": first_detection.isoformat() if first_detection else None,
            "last_detection": last_detection.isoformat() if last_detection else None,
        }
