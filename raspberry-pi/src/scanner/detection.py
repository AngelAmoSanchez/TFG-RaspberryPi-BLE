from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Zone(Enum):
    """Zonas de proximidad según la señal RSSI"""

    NEAR = "near"  # RSSI >= -60 dBm
    MEDIUM = "medium"  # -75 <= RSSI < -60 dBm
    FAR = "far"  # RSSI < -75 dBm

    def get_description(self) -> str:
        """Devuelve descripción legible de cada zona"""
        descriptions = {
            Zone.NEAR: "Zona Cercana (0-2m)",
            Zone.MEDIUM: "Zona Media (2-5m)",
            Zone.FAR: "Zona Lejana (>5m)",
        }
        return descriptions[self]


@dataclass(frozen=True)
class Detection:
    """Representa una detección Bluetooth BLE en bruto directamente desde el escaneo"""

    mac_address: str
    rssi: int
    timestamp: datetime
    device_name: Optional[str] = None  # (si es que está disponible)

    def __post_init__(self):
        """Validaciones del dominio"""
        if not self.mac_address:
            raise ValueError("Dirección MAC no puede estar vacía")
        if self.rssi > 0:
            raise ValueError(f"RSSI tiene que ser negativo, se obtuvo {self.rssi}")
        if self.rssi < -100:
            raise ValueError(
                f"RSSI demasiado bajo (fuera de rango), se obtuvo {self.rssi}"
            )

    def to_dict(self) -> dict:
        """Serializa la detección a diccionario"""
        return {
            "mac_address": self.mac_address,
            "rssi": self.rssi,
            "timestamp": self.timestamp.isoformat(),
            "device_name": self.device_name,
        }


@dataclass(frozen=True)
class Device:
    """Dispositivo una vez procesado y anonimizado.
    Representa un dispositivo después de ser procesado por el dominio"""

    device_hash: str  # Hash SHA-256 de MAC
    rssi: int
    zone: Zone
    timestamp: datetime

    def __post_init__(self):
        """Validaciones"""
        if len(self.device_hash) != 64:
            raise ValueError(
                f"El hash tiene que tener 64 carácteres (SHA-256), se obtuvieron {len(self.device_hash)}"
            )
        if self.rssi > 0 or self.rssi < -120:
            raise ValueError(f"Invalid RSSI: {self.rssi}")

    def to_dict(self) -> dict:
        """Serializa la detección procesada para MQTT"""
        return {
            "device_hash": self.device_hash,
            "rssi": self.rssi,
            "zone": self.zone.value,
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_detection(detection: Detection, device_hash: str, zone: Zone) -> "Device":
        """Método para crear Device desde Detection
        Implementa la transformación de datos en bruto a entidad de dominio"""
        return Device(
            device_hash=device_hash,
            rssi=detection.rssi,
            zone=zone,
            timestamp=detection.timestamp,
        )
