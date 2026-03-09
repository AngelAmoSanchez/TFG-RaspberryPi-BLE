from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .models import Detection, Device, Statistics, Zone


class BluetoothScannerPort(ABC):
    """Puerto de salida para escaneo Bluetooth

    Los adaptadores concretos implementan esta interface:
    - BleakBLEScanner (producción)
    - MockBLEScanner (desarrollo/testing)
    """

    @abstractmethod
    async def scan_devices(self) -> List[Detection]:
        """Escanea dispositivos Bluetooth cercanos

        Returns:
            Lista de detecciones con MAC, RSSI y timestamp
        """
        pass


class DeviceRepositoryPort(ABC):
    """Puerto de salida  para persistencia de dispositivos y estadísticas

    Adaptadores:
    - SQLiteDeviceRepository (producción)
    - InMemoryDeviceRepository (testing)
    """

    @abstractmethod
    async def save(self, device: Device) -> Device:
        """Guarda un dispositivo detectado

        Args:
            device: Dispositivo a persistir

        Returns:
            Dispositivo con ID asignado
        """
        pass

    @abstractmethod
    async def get_by_hash(self, device_hash: str, since: datetime) -> Optional[Device]:
        """Obtiene dispositivo por hash en un periodo definido con el fin de detectar permanencia

        Args:
            device_hash: Hash SHA-256 de la MAC
            since: Fecha (timestamp) desde la cual buscar detecciones

        Returns:
            Dispositivo encontrado o None
        """
        pass

    @abstractmethod
    async def get_hourly_stats(self, date: datetime) -> List[Statistics]:
        """Obtiene estadísticas por hora

        Args:
            date: Fecha para obtener estadísticas

        Returns:
            Lista de estadísticas por hora y zona
        """
        pass

    @abstractmethod
    async def get_daily_stats(
        self, start_date: datetime, end_date: datetime
    ) -> List[Statistics]:
        """Obtiene estadísticas por día

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de estadísticas por día y zona
        """
        pass

    @abstractmethod
    async def export_to_csv(self, start_date: datetime, end_date: datetime) -> str:
        """Exporta datos en formato CSV

        Args:
            start_date: Fecha de inicio del rango
            end_date: Fecha de fin del rango

        Returns:
            Ubicación del archivo CSV generado
        """
        pass

    @abstractmethod
    async def get_all_detections(
        self, start_date: datetime, end_date: datetime, zone: Optional[Zone] = None
    ) -> List[Device]:
        """Obtiene todas las detecciones en un rango de tiempo definido

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            zone: Filtrar por zona (opcional)

        Returns:
            Lista de dispositivos detectados
        """
        pass
