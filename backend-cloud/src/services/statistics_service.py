import logging
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database.models import AggregatedStats, Detection, ZoneEnum
from ..utils import timezone_utils

logger = logging.getLogger(__name__)


class StatisticsService:
    """Servicio de dominio para generar estadísticas a partir de las detecciones"""

    def __init__(self, devices_per_person: float = None):
        """
        Args:
            devices_per_person: Ratio estimado de dispositivos por persona
        """
        self.devices_per_person = devices_per_person or settings.devices_per_person

    def estimate_people(self, unique_devices: int) -> int:
        """Estima el número de personas a partir del número de dispositivos únicos detectados"""
        if unique_devices == 0:
            return 0
        estimated = unique_devices / self.devices_per_person
        return max(1, int(round(estimated)))

    async def get_hourly_stats(self, db: AsyncSession, date: datetime) -> List[Dict]:
        """Obtiene estadísticas agregadas por hora para un día específico

        Args:
            db: Sesión de base de datos
            date: Fecha para la que se quieren estadísticas

        Devuelve:
            Lista de diccionarios con estadísticas por hora y zona
        """

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Consulta para agrupar por hora y zona
        query = (
            select(
                func.date_trunc("hour", Detection.timestamp).label("hour_start"),
                Detection.zone,
                func.count(func.distinct(Detection.device_hash)).label("unique_devices"),
                func.count(Detection.id).label("total_detections"),
                func.avg(Detection.rssi).label("avg_rssi"),
            )
            .where(and_(Detection.timestamp >= start_of_day, Detection.timestamp < end_of_day))
            .group_by("hour_start", Detection.zone)
            .order_by("hour_start", Detection.zone)
        )

        result = await db.execute(query)
        rows = result.all()

        # Procesar resultados
        stats = []
        for row in rows:
            unique_devices = row.unique_devices
            estimated_people = self.estimate_people(unique_devices)

            stats.append(
                {
                    "period_type": "hour",
                    "period_start": row.hour_start.isoformat(),
                    "zone": row.zone.value if isinstance(row.zone, ZoneEnum) else row.zone,
                    "unique_devices": unique_devices,
                    "total_detections": row.total_detections,
                    "estimated_people": estimated_people,
                    "avg_rssi": round(row.avg_rssi, 2) if row.avg_rssi else None,
                }
            )

        logger.info(f"Generadas {len(stats)} estadísticas por hora para {date.date()}")
        return stats

    async def get_daily_stats(
        self, db: AsyncSession, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Obtiene estadísticas agregadas por días

        Args:
            db: Sesión de base de datos
            start_date: Fecha de inicio
            end_date: Fecha de fin (inclusive)

        Devuelve:
            Lista de diccionarios con estadísticas por día y zona
        """

        start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Consulta para agrupar por día y zona
        query = (
            select(
                func.date_trunc("day", Detection.timestamp).label("day_start"),
                Detection.zone,
                func.count(func.distinct(Detection.device_hash)).label("unique_devices"),
                func.count(Detection.id).label("total_detections"),
                func.avg(Detection.rssi).label("avg_rssi"),
            )
            .where(and_(Detection.timestamp >= start, Detection.timestamp <= end))
            .group_by("day_start", Detection.zone)
            .order_by("day_start", Detection.zone)
        )

        result = await db.execute(query)
        rows = result.all()

        # Procesar resultados
        stats = []
        for row in rows:
            unique_devices = row.unique_devices
            estimated_people = self.estimate_people(unique_devices)

            stats.append(
                {
                    "period_type": "day",
                    "period_start": row.day_start.isoformat(),
                    "zone": row.zone.value if isinstance(row.zone, ZoneEnum) else row.zone,
                    "unique_devices": unique_devices,
                    "total_detections": row.total_detections,
                    "estimated_people": estimated_people,
                    "avg_rssi": round(row.avg_rssi, 2) if row.avg_rssi else None,
                }
            )

        logger.info(
            f"Generadas {len(stats)} estadísticas diarias desde {start_date.date()} hasta {end_date.date()}"
        )
        return stats

    async def get_real_time_stats(self, db: AsyncSession, minutes: int = 5) -> Dict:
        """Obtiene estadísticas en tiempo real para los últimos N minutos

        Args:
            db: Sesión de base de datos
            minutes: úmero de minutos para retroceder

        Devuelve:
            Diccionario con estadísticas por zona y totales
        """
        now = timezone_utils.now()
        start_time = now - timedelta(minutes=minutes)
        end_time = now + timedelta(seconds=1)

        # Consulta para agrupar por zona
        query = (
            select(
                Detection.zone,
                func.count(func.distinct(Detection.device_hash)).label("unique_devices"),
                func.count(Detection.id).label("total_detections"),
                func.avg(Detection.rssi).label("avg_rssi"),
            )
            .where(and_(Detection.timestamp >= start_time, Detection.timestamp < end_time))
            .group_by(Detection.zone)
        )

        result = await db.execute(query)
        rows = result.all()

        # Procesar por zona
        stats_by_zone = {}
        total_unique = 0
        total_detections = 0

        for row in rows:
            zone = row.zone.value if isinstance(row.zone, ZoneEnum) else row.zone
            unique_devices = row.unique_devices

            stats_by_zone[zone] = {
                "unique_devices": unique_devices,
                "total_detections": row.total_detections,
                "estimated_people": self.estimate_people(unique_devices),
                "avg_rssi": round(row.avg_rssi, 2) if row.avg_rssi else None,
            }

            total_unique += unique_devices
            total_detections += row.total_detections

        logger.info(
            f"Estadísticas en tiempo real: {total_unique} dispositivos únicos de {start_time.strftime('%H:%M:%S')} a {now.strftime('%H:%M:%S')} (ventana de {minutes} minutos)"
        )

        return {
            "timestamp": now.isoformat(),
            "time_window_minutes": minutes,
            "by_zone": stats_by_zone,
            "total": {
                "unique_devices": total_unique,
                "total_detections": total_detections,
                "estimated_people": self.estimate_people(total_unique),
            },
        }

    async def save_aggregated_stats(
        self, db: AsyncSession, period_type: str, period_start: datetime, period_end: datetime
    ) -> List[AggregatedStats]:
        """Guarda estadísticas agregadas en la base de datos en un período específico

        Args:
            db: Sesión de base de datos
            period_type: 'hour', 'day', or 'week'
            period_start: Inicio del período
            period_end: Fin del período

        Devuelve:
            Lista de objetos AggregatedStats creados
        """
        # Consulta para agrupar por zona
        query = (
            select(
                Detection.zone,
                func.count(func.distinct(Detection.device_hash)).label("unique_devices"),
                func.count(Detection.id).label("total_detections"),
                func.avg(Detection.rssi).label("avg_rssi"),
            )
            .where(and_(Detection.timestamp >= period_start, Detection.timestamp < period_end))
            .group_by(Detection.zone)
        )

        result = await db.execute(query)
        rows = result.all()

        # Crear estadísticas agregadas para cada zona
        aggregated = []
        for row in rows:
            unique_devices = row.unique_devices

            stat = AggregatedStats(
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                zone=row.zone,
                unique_devices=unique_devices,
                total_detections=row.total_detections,
                estimated_people=self.estimate_people(unique_devices),
                avg_rssi=row.avg_rssi,
            )

            aggregated.append(stat)

        if aggregated:
            db.add_all(aggregated)
            await db.flush()
            logger.info(f"Guardadas {len(aggregated)} estadísticas agregadas para {period_type}")

        return aggregated

    async def get_zone_distribution(
        self, db: AsyncSession, start_time: datetime, end_time: datetime
    ) -> Dict:
        """Obtiene la distribución de detecciones por zona en un rango de tiempo

        Args:
            db: Sesión de base de datos
            start_time: Tiempo de inicio
            end_time: Tiempo de fin

        Devuelve:
            Diccionario con la distribución por zona
        """
        query = (
            select(Detection.zone, func.count(Detection.id).label("count"))
            .where(and_(Detection.timestamp >= start_time, Detection.timestamp < end_time))
            .group_by(Detection.zone)
        )

        result = await db.execute(query)
        rows = result.all()

        total = sum(row.count for row in rows)

        distribution = {}
        for row in rows:
            zone = row.zone.value if isinstance(row.zone, ZoneEnum) else row.zone
            count = row.count
            percentage = (count / total * 100) if total > 0 else 0

            distribution[zone] = {"count": count, "percentage": round(percentage, 2)}

        return {"total": total, "distribution": distribution}