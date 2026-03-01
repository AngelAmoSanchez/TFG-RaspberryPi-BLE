from dataclasses import dataclass


@dataclass
class BluetoothConfig:
    """Configuración del escáner Bluetooth"""

    scan_duration: int = 10
    scan_interval: int = 25


@dataclass
class ZoneConfig:
    """Configuración de umbrales de división de zonas según RSSI"""

    near_threshold: int = -50  # Zona cercana
    medium_threshold: int = -70  # Zona media


@dataclass
class PermanenceConfig:
    """Configuración de la permanencia"""

    min_permanence_minutes: int = 2


@dataclass
class DatabaseConfig:
    """Configuración de la base de datos"""

    db_path: str = "data/detections.db"


@dataclass
class APIConfig:
    """Configuración del API"""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False  # True solo en desarrollo


@dataclass
class AppConfig:
    """Configuración general del sistema"""

    bluetooth: BluetoothConfig
    zone: ZoneConfig
    permanence: PermanenceConfig
    database: DatabaseConfig
    api: APIConfig

    @staticmethod
    def load_default() -> "AppConfig":
        """Carga por defecto de la configuración"""
        return AppConfig(
            bluetooth=BluetoothConfig(),
            zone=ZoneConfig(),
            permanence=PermanenceConfig(),
            database=DatabaseConfig(),
            api=APIConfig(),
        )
