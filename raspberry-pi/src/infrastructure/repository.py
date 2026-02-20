import aiosqlite
import csv
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import logging

from ..domain.models import Device, Statistics, Zone
from ..domain.ports import DeviceRepositoryPort

logger = logging.getLogger(__name__)


class SQLiteDeviceRepository(DeviceRepositoryPort):
    """Repository pattern con SQLite"""

    def __init__(self, db_path: str = "data/detections.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Inicializa la base de datos con el esquema"""
        async with aiosqlite.connect(self.db_path) as db:
            schema_path = (
                Path(__file__).parent.parent.parent / "database" / "schema.sql"
            )

            with open(schema_path) as f:
                schema = f.read()

            await db.executescript(schema)
            await db.commit()
            logger.info("Base de datos inicializada")

    async def save(self, device: Device) -> Device:
        """Guarda dispositivo en BD"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO detections (device_hash, rssi, zone, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (device.device_hash, device.rssi, device.zone.value, device.timestamp),
            )
            await db.commit()
            device.id = cursor.lastrowid
            return device

    async def get_by_hash(self, device_hash: str, since: datetime) -> Optional[Device]:
        """Obtiene la última detección de un dispositivo por su hash desde una fecha concreta"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT * FROM detections
                WHERE device_hash = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (device_hash, since),
            )
            row = await cursor.fetchone()

            if row:
                return Device(
                    id=row["id"],
                    device_hash=row["device_hash"],
                    rssi=row["rssi"],
                    zone=Zone(row["zone"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            return None

    async def get_hourly_stats(self, date: datetime) -> List[Statistics]:
        """Obtiene estadísticas por hora"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            cursor = await db.execute(
                """
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour_start,
                    zone,
                    COUNT(DISTINCT device_hash) as unique_devices,
                    0.0 as avg_permanence_minutes
                FROM detections
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY hour_start, zone
                ORDER BY hour_start, zone
                """,
                (start_of_day, end_of_day),
            )

            rows = await cursor.fetchall()

            stats = []
            for row in rows:
                stat = Statistics(
                    time_period="hour",
                    start_time=datetime.fromisoformat(row["hour_start"]),
                    zone=Zone(row["zone"]),
                    estimated_people=0,  # Se calcula en use case
                    unique_devices=row["unique_devices"],
                    avg_permanence_minutes=row["avg_permanence_minutes"],
                )
                stats.append(stat)

            return stats

    async def get_daily_stats(
        self, start_date: datetime, end_date: datetime
    ) -> List[Statistics]:
        """Obtiene estadísticas por día"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT 
                    DATE(timestamp) as date,
                    zone,
                    COUNT(DISTINCT device_hash) as unique_devices,
                    0.0 as avg_permanence_minutes
                FROM detections
                WHERE DATE(timestamp) >= DATE(?) AND DATE(timestamp) <= DATE(?)
                GROUP BY date, zone
                ORDER BY date, zone
                """,
                (start_date, end_date),
            )

            rows = await cursor.fetchall()

            stats = []
            for row in rows:
                stat = Statistics(
                    time_period="day",
                    start_time=datetime.fromisoformat(row["date"]),
                    zone=Zone(row["zone"]),
                    estimated_people=0,
                    unique_devices=row["unique_devices"],
                    avg_permanence_minutes=row["avg_permanence_minutes"],
                )
                stats.append(stat)

            return stats

    async def export_to_csv(self, start_date: datetime, end_date: datetime) -> str:
        """Exporta datos a CSV para un rango de fechas"""
        # Definimos las fechas para incluir todo el día
        start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        csv_path = f"exports/detections_{start_date.date()}_{end_date.date()}.csv"
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT device_hash, rssi, zone, datetime(timestamp) as timestamp
                FROM detections
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
                """,
                (start, end),
            )

            rows = await cursor.fetchall()

            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["device_hash", "rssi", "zone", "timestamp"])

                for row in rows:
                    writer.writerow(
                        [row["device_hash"], row["rssi"], row["zone"], row["timestamp"]]
                    )

        logger.info(f"Exportados {len(rows)} registros a {csv_path}")
        return csv_path

    async def get_all_detections(
        self, start_date: datetime, end_date: datetime, zone: Optional[Zone] = None
    ) -> List[Device]:
        """Obtiene todas las detecciones entre dos fechas, opcionalmente filtrando por zona"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if zone:
                cursor = await db.execute(
                    "SELECT * FROM detections WHERE timestamp >= ? AND timestamp <= ? AND zone = ?",
                    (start_date, end_date, zone.value),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM detections WHERE timestamp >= ? AND timestamp <= ?",
                    (start_date, end_date),
                )

            rows = await cursor.fetchall()

            devices = []
            for row in rows:
                device = Device(
                    id=row["id"],
                    device_hash=row["device_hash"],
                    rssi=row["rssi"],
                    zone=Zone(row["zone"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                devices.append(device)

            return devices
