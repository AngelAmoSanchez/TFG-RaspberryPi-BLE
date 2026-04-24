"""
Utilidades para manejo de zonas horarias
Centraliza toda la lógica de timezone en un solo lugar
Usa zoneinfo (incluido en Python 3.9+, no requiere dependencias externas)
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Zona horaria de España (CEST en verano, CET en invierno)
SPAIN_TZ = ZoneInfo("Europe/Madrid")


def now() -> datetime:
    """
    Devuelve la hora actual en zona horaria de España
    
    Returns:
        datetime: Hora actual en Europe/Madrid con tzinfo
    """
    return datetime.now(SPAIN_TZ)


def utc_now() -> datetime:
    """
    Devuelve la hora actual en UTC
    Solo usar si específicamente necesitas UTC
    
    Returns:
        datetime: Hora actual en UTC con tzinfo
    """
    return datetime.now(timezone.utc)


def ensure_spain_tz(dt: datetime) -> datetime:
    """
    Asegura que un datetime tiene timezone de España
    
    Args:
        dt: datetime con o sin timezone
        
    Returns:
        datetime con timezone Europe/Madrid
    """
    if dt.tzinfo is None:
        # Si no tiene timezone, asume que es hora de España
        return dt.replace(tzinfo=SPAIN_TZ)
    else:
        # Si tiene timezone, convierte a España
        return dt.astimezone(SPAIN_TZ)


def to_spain_tz(dt: datetime) -> datetime:
    """
    Convierte un datetime a zona horaria de España
    
    Args:
        dt: datetime con timezone
        
    Returns:
        datetime convertido a Europe/Madrid
    """
    if dt.tzinfo is None:
        # Si no tiene timezone, asume UTC y convierte
        return dt.replace(tzinfo=timezone.utc).astimezone(SPAIN_TZ)
    else:
        return dt.astimezone(SPAIN_TZ)


def parse_datetime(dt_str: str) -> datetime:
    """
    Parsea un string ISO a datetime con timezone de España
    
    Args:
        dt_str: String en formato ISO (ej: "2026-04-24T15:00:00")
        
    Returns:
        datetime con timezone Europe/Madrid
    """
    # Parsear string
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    
    # Asegurar timezone de España
    return ensure_spain_tz(dt)
