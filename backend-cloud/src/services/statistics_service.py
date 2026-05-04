import logging
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_, func, literal_column, select
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

    async def get_range_stats(
        self, db: AsyncSession, start_time: datetime, end_time: datetime, device_id: str = None
    ) -> Dict:
        """Obtiene estadísticas para un rango de fechas específico

        Args:
            db: Sesión de base de datos
            start_time: Fecha y hora de inicio
            end_time: Fecha y hora de fin
            device_id: Opcional, filtrar por ID de dispositivo

        Devuelve:
            Diccionario con estadísticas por zona y totales
        """
        # Asegurar que las fechas tienen timezone de España
        start_time = timezone_utils.ensure_spain_tz(start_time)
        end_time = timezone_utils.ensure_spain_tz(end_time)

        # Construir condiciones
        conditions = [Detection.timestamp >= start_time, Detection.timestamp <= end_time]

        # Filtrar por device_id si se proporciona
        if device_id:
            conditions.append(Detection.device_id == device_id)

        # Consulta para obtener estadísticas por zona
        query = (
            select(
                Detection.zone,
                func.count(func.distinct(Detection.device_hash)).label("unique_devices"),
                func.count(Detection.id).label("total_detections"),
                func.avg(Detection.rssi).label("avg_rssi"),
            )
            .where(and_(*conditions))
            .group_by(Detection.zone)
        )

        result = await db.execute(query)
        rows = result.all()

        # Procesar por zona
        by_zone = {}
        total_unique_devices = 0
        total_detections = 0

        for row in rows:
            zone_name = row.zone.value if isinstance(row.zone, ZoneEnum) else row.zone
            unique_devices = row.unique_devices

            by_zone[zone_name] = {
                "unique_devices": unique_devices,
                "total_detections": row.total_detections,
                "estimated_people": self.estimate_people(unique_devices),
                "avg_rssi": round(row.avg_rssi, 2) if row.avg_rssi else None,
            }

            total_unique_devices += unique_devices
            total_detections += row.total_detections

        # Calcular totales
        stats = {
            "timestamp": timezone_utils.now().isoformat(),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total": {
                "unique_devices": total_unique_devices,
                "total_detections": total_detections,
                "estimated_people": self.estimate_people(total_unique_devices),
                "avg_rssi": None,
            },
            "by_zone": by_zone,
        }

        logger.info(
            f"Estadísticas de rango generadas: {total_unique_devices} dispositivos únicos entre {start_time} y {end_time}"
        )
        return stats

    async def get_real_time_stats(
        self, db: AsyncSession, minutes: int = 5, device_id: str = None
    ) -> Dict:
        """Obtiene estadísticas en tiempo real para los últimos N minutos

        Args:
            db: Sesión de base de datos
            minutes: úmero de minutos para retroceder
            device_id: Opcional, filtrar por ID de dispositivo

        Devuelve:
            Diccionario con estadísticas por zona y totales
        """
        now = timezone_utils.now()
        start_time = now - timedelta(minutes=minutes)
        end_time = now + timedelta(seconds=1)

        # Construir condiciones
        conditions = [Detection.timestamp >= start_time, Detection.timestamp < end_time]

        # Filtrar por device_id si se proporciona
        if device_id:
            conditions.append(Detection.device_id == device_id)

        # Consulta para agrupar por zona
        query = (
            select(
                Detection.zone,
                func.count(func.distinct(Detection.device_hash)).label("unique_devices"),
                func.count(Detection.id).label("total_detections"),
                func.avg(Detection.rssi).label("avg_rssi"),
            )
            .where(and_(*conditions))
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

    def _compute_histogram_window(self, range_key: str):
        """Calcula la lista completa de bloques de tiempo (vacíos incluidos) para un rango de tiempo.

        Devuelve:
            (start, end, buckets) donde buckets (bloques de tiempo) es una lista de tuplas
            (period_start, period_end) ordenadas cronológicamente.
        """
        now = timezone_utils.now()
        buckets = []

        if range_key == "hour":
            # Hora actual de reloj: 6 bloques de 10 min
            start = now.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            for i in range(6):
                bs = start + timedelta(minutes=10 * i)
                be = bs + timedelta(minutes=10)
                buckets.append((bs, be))
 
        elif range_key == "today":
            # Desde 00:00 hasta 24:00 de hoy: 8 bloques de 3h
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            for i in range(8):
                bs = start + timedelta(hours=3 * i)
                be = bs + timedelta(hours=3)
                buckets.append((bs, be))

        elif range_key == "week":
            # Últimos 7 días terminando hoy: 1 bloque = 1 día
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = today_start - timedelta(days=6)
            end = today_start + timedelta(days=1)
            for i in range(7):
                bs = start + timedelta(days=i)
                be = bs + timedelta(days=1)
                buckets.append((bs, be))

        else:
            raise ValueError(f"ERROR - Rango range_key desconocido: {range_key}")

        return start, end, buckets

    async def get_histogram_stats(
        self, db: AsyncSession, range_key: str, device_id: str = None
    ) -> Dict:
        """Obtiene un histograma de dispositivos únicos agrupados por bloques de tiempo y subdivididos por zona.

        Args:
            range_key: 'hour' | 'today' | 'week'
            device_id: Opcional filtrar por dispositivo"""
        start, end, bucket_slate = self._compute_histogram_window(range_key)

        # Tamaño del bucket en función del rango
        if range_key == "hour":
            bin_interval = "10 minutes"
        elif range_key == "today":
            bin_interval = "3 hours"
        elif range_key == "week":
            bin_interval = "1 day"
        else:
            raise ValueError(f"range_key desconocido: {range_key}")
 
        # Cada sub-select cuenta dispositivos y detecciones para un bucket
        params = {}
        parts = []
        for i, (bs, be) in enumerate(bucket_slate):
            p_start = f"bs_{i}"
            p_end = f"be_{i}"
            p_label = f"bl_{i}"
            params[p_start] = bs
            params[p_end] = be
            params[p_label] = bs.isoformat()
 
            device_filter = ""
            if device_id:
                p_dev = f"dev_{i}"
                params[p_dev] = device_id
                device_filter = f" AND device_id = :{p_dev}"
 
            parts.append(
                f"SELECT :{p_label} AS bucket_label, zone, "
                f"COUNT(DISTINCT device_hash) AS unique_devices, "
                f"COUNT(id) AS total_detections "
                f"FROM detections "
                f"WHERE timestamp >= :{p_start} AND timestamp < :{p_end}"
                f"{device_filter} "
                f"GROUP BY zone"
            )
 
        union_sql = " UNION ALL ".join(parts)
        result = await db.execute(text(union_sql), params)
        rows = result.all()
 
        if rows:
            logger.info(
                f"Histograma {range_key}: SQL devolvió {len(rows)} filas. "
                f"Primer bucket raw: {rows[0].bucket!r} (type={type(rows[0].bucket).__name__}), "
                f"zone={rows[0].zone!r}"
            )
        else:
            logger.info(
                f"Histograma {range_key}: SQL devolvió 0 filas. "
                f"WHERE: start={start.isoformat()}, end={end.isoformat()}"
            )

        slate_keys_sample = [bs.isoformat() for bs, _ in bucket_slate[:2]]
        logger.info(f"Histograma {range_key}: slate keys sample={slate_keys_sample}")

        # Indexamos los resultados por (bucket_iso, zona)
        data_map = {}
        for row in rows:
            bucket_label = row.bucket_label
            zone_raw = row.zone
            zone = zone_raw.lower() if isinstance(zone_raw, str) else zone_raw.value.lower()
            key = (bucket_label, zone)
            data_map[key] = {
                "unique_devices": row.unique_devices,
                "total_detections": row.total_detections,
            }
 
        if data_map:
            sample_keys = list(data_map.keys())[:3]
            logger.info(f"Histograma {range_key}: data_map keys sample={sample_keys}")

        # Construimos la respuesta rellenando vacíos con ceros
        buckets_out = []
        for bs, be in bucket_slate:
            by_zone = {}
            for zone_name in ("near", "medium", "far"):
                key = (bs.isoformat(), zone_name)
                entry = data_map.get(key)
                if entry:
                    by_zone[zone_name] = entry["unique_devices"]
                else:
                    by_zone[zone_name] = 0
            total = sum(by_zone.values())
            buckets_out.append(
                {
                    "period_start": bs.isoformat(),
                    "period_end": be.isoformat(),
                    "by_zone": by_zone,
                    "total": total,
                }
            )

        logger.info(
            f"Histograma {range_key}: {len(buckets_out)} buckets, "
            f"{sum(b['total'] for b in buckets_out)} dispositivos totales"
        )

        return {
            "timestamp": timezone_utils.now().isoformat(),
            "range": range_key,
            "bin_interval": bin_interval,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "buckets": buckets_out,
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
