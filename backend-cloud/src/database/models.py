import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ZoneEnum(str, enum.Enum):
    """ Zonas de proximidad según la señal RSSI """

    NEAR = "near"
    MEDIUM = "medium"
    FAR = "far"


class Detection(Base):
    """Cada detección de un dispositivo BLE por la Raspberry Pi"""

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_hash = Column(String(64), nullable=False, index=True)
    rssi = Column(Integer, nullable=False)
    zone = Column(SQLEnum(ZoneEnum), nullable=False, index=True)
    timestamp = Column(
        DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc)
    )
    device_id = Column(String(50), nullable=False, index=True)

    # Indices para consultas comunes
    __table_args__ = (
        Index("idx_device_hash_timestamp", "device_hash", "timestamp"),
        Index("idx_zone_timestamp", "zone", "timestamp"),
        Index("idx_device_id_timestamp", "device_id", "timestamp"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_hash": self.device_hash,
            "rssi": self.rssi,
            "zone": self.zone.value if isinstance(self.zone, ZoneEnum) else self.zone,
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
        }


class Device(Base):
    """Información de los dispositivos detectados"""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)
    is_active = Column(Integer, default=1)  # 1=activo, 0=inactivo
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "name": self.name,
            "location": self.location,
            "is_active": bool(self.is_active),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AggregatedStats(Base):
    """Estadísticas de datos detectados y agrupados"""

    __tablename__ = "aggregated_stats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    period_type = Column(String(20), nullable=False)  # 'hour', 'day', 'week'
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    zone = Column(SQLEnum(ZoneEnum), nullable=False)
    unique_devices = Column(Integer, nullable=False, default=0)
    total_detections = Column(Integer, nullable=False, default=0)
    estimated_people = Column(Integer, nullable=False, default=0)
    avg_rssi = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_period_zone", "period_type", "period_start", "zone"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "zone": self.zone.value if isinstance(self.zone, ZoneEnum) else self.zone,
            "unique_devices": self.unique_devices,
            "total_detections": self.total_detections,
            "estimated_people": self.estimated_people,
            "avg_rssi": self.avg_rssi,
        }
