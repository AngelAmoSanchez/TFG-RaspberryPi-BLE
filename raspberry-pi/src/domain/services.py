import hashlib
from datetime import datetime

from .models import Zone


class AnonymizationService:
    """Servicio de anonimización de datos
    Implementa hash irreversible de direcciones MAC"""

    @staticmethod
    def hash_mac(mac_address: str) -> str:
        """Genera un hash SHA-256 de una dirección MAC

        Args:
            mac_address: Dirección MAC del dispositivo

        Returns:
            Hash SHA-256 en formato hexadecimal (64 caracteres)
        """
        # Normalizar las MACs
        normalized_mac = mac_address.replace(":", "").replace("-", "").upper()

        # Generar hash SHA-256
        hash_object = hashlib.sha256(normalized_mac.encode())
        return hash_object.hexdigest()


class ZoneClassifierService:
    """Servicio de clasificación en zonas de proximidad
    Clasifica dispositivos según su señal RSSI
    """

    def __init__(self, near_threshold: int = -50, medium_threshold: int = -70):
        """
        Args:
            near_threshold: Umbral RSSI para zona cercana (por defecto -50 dBm)
            medium_threshold: Umbral RSSI para zona media (por defecto -70 dBm)
        """
        self.near_threshold = near_threshold
        self.medium_threshold = medium_threshold

    def classify(self, rssi: int) -> Zone:
        """Clasifica dispositivo en zona según su RSSI

        Rangos típicos BLE:
        - Muy cerca (< 1m): -40 a -50 dBm
        - Cerca (1-3m): -50 a -65 dBm
        - Media distancia (3-7m): -65 a -80 dBm
        - Lejos (> 7m): < -80 dBm

        Args:
            rssi: Señal recibida en dBm (negativo)

        Returns:
            Zone correspondiente
        """
        if rssi >= self.near_threshold:
            return Zone.NEAR
        elif rssi >= self.medium_threshold:
            return Zone.MEDIUM
        else:
            return Zone.FAR


class PeopleEstimatorService:
    """Servicio de estimación de personas
    según la cantidad de dispositivos detectados
    """

    def __init__(self, devices_per_person: float = 1.5):
        """
        Args:
            devices_per_person: Ratio dispositivos/persona (por defecto 1.5)
        """
        self.devices_per_person = devices_per_person

    @staticmethod
    def estimate_people(unique_devices: int, devices_per_person: float = 1.5) -> int:
        """Estima número de personas basándose en dispositivos únicos
        Asumiendo que el ratio típico es de 1.5 dispositivos por persona,
        se puede estimar el número de personas detectadas.

        Args:
            unique_devices: Número de dispositivos únicos detectados
            devices_per_person: Ratio dispositivos por persona

        Returns:
            Número estimado de personas (mínimo 1)
        """
        if unique_devices == 0:
            return 0

        estimated = unique_devices / devices_per_person
        return max(1, int(round(estimated)))


class PermanenceService:
    """Servicio de detección de permanencia en la zona
    Determina si un dispositivo cumple tiempo mínimo de permanencia"""

    def __init__(self, min_permanence_minutes: int = 2):
        """
        Args:
            min_permanence_minutes: Tiempo mínimo para considerar permanencia
        """
        self.min_permanence_minutes = min_permanence_minutes

    def calculate_permanence(self, first_seen: datetime, last_seen: datetime) -> float:
        """Calcula tiempo de permanencia en minutos

        Args:
            first_seen: Primera detección del dispositivo
            last_seen: Última detección del dispositivo

        Returns:
            Minutos de permanencia
        """
        delta = last_seen - first_seen
        return delta.total_seconds() / 60

    def is_permanent(self, first_seen: datetime, last_seen: datetime) -> bool:
        """Verifica si cumple tiempo mínimo de permanencia

        Args:
            first_seen: Primera detección
            last_seen: Última detección

        Returns:
            True si cumple tiempo mínimo
        """
        permanence = self.calculate_permanence(first_seen, last_seen)
        return permanence >= self.min_permanence_minutes
