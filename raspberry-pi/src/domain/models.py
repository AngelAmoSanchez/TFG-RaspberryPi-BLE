from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Zone(Enum):
    """ Zonas de proximidad según la señal RSSI """
    NEAR = "near"      # RSSI >= -50 dBm
    MEDIUM = "medium"  # -70 <= RSSI < -50 dBm
    FAR = "far"        # RSSI < -70 dBm

    def get_description(self) -> str:
        """ Devuelve descripción legible de cada zona """
        descriptions = {
            Zone.NEAR: "Zona Cercana (0-2m)",
            Zone.MEDIUM: "Zona Media (2-5m)",
            Zone.FAR: "Zona Lejana (>5m)"
        }
        return descriptions[self]


@dataclass
class Detection:
    """ Representa una detección Bluetooth BLE en bruto directamente desde el escaneo """
    mac_address: str
    rssi: int
    timestamp: datetime
    device_name: Optional[str] = None  # (si es que está disponible)

    def __post_init__(self):
        """ Validaciones del dominio """
        if not self.mac_address:
            raise ValueError("Dirección MAC no puede estar vacía")
        if self.rssi > 0:
            raise ValueError(f"RSSI tiene que ser negativo, se obtuvo {self.rssi}")
        if self.rssi < -100:
            raise ValueError(f"RSSI demasiado bajo (fuera de rango), se obtuvo {self.rssi}")


@dataclass
class Device:
    """ Dispositivo una vez procesado y anonimizado.
    Representa un dispositivo después de ser procesado por el dominio """
    id: Optional[int]
    device_hash: str      # Hash SHA-256 de MAC
    rssi: int
    zone: Zone
    timestamp: datetime

    @staticmethod
    def from_detection(detection: Detection, device_hash: str, zone: Zone) -> 'Device':
        """ Método para crear Device desde Detection
        Implementa la transformación de datos en bruto a entidad de dominio """
        return Device(
            id=None,
            device_hash=device_hash,
            rssi=detection.rssi,
            zone=zone,
            timestamp=detection.timestamp
        )


@dataclass
class Statistics:
    """ Estadísticas de datos detectados y agrupados por periodo temporal y zona """
    time_period: str  # 'hour', 'day', 'week'
    start_time: datetime
    zone: Zone
    estimated_people: int
    unique_devices: int
    avg_permanence_minutes: float
    
    def to_dict(self) -> dict:
        """ Convierte a diccionario para su serialización """
        return {
            'time_period': self.time_period,
            'start_time': self.start_time.isoformat(),
            'zone': self.zone.value,
            'estimated_people': self.estimated_people,
            'unique_devices': self.unique_devices,
            'avg_permanence_minutes': round(self.avg_permanence_minutes, 2)
        }
