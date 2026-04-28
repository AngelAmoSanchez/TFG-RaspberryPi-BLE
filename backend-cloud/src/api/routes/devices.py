from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegister(BaseModel):
    device_id: str
    name: Optional[str] = None
    location: Optional[str] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


@router.post("/register")
async def register_device(device: DeviceRegister, db: AsyncSession = Depends(get_db)):
    """Registrar nuevo dispositivo IoT"""
    service = DeviceService()
    result = await service.register_device(db, device.device_id, device.name, device.location)
    await db.commit()
    return result.to_dict()


@router.get("/")
async def get_all_devices(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    """Obtener todos los dispositivos registrados"""
    service = DeviceService()
    devices = await service.get_all_devices(db, active_only)
    return [d.to_dict() for d in devices]


@router.get("/active")
async def get_active_devices(threshold_minutes: int = 60, db: AsyncSession = Depends(get_db)):
    """Obtener dispositivos activos (vistos recientemente)"""
    service = DeviceService()
    devices = await service.get_active_devices(db, threshold_minutes)
    return [d.to_dict() for d in devices]


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Obtener dispositivo por ID"""
    service = DeviceService()
    device = await service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device no encontrado")
    return device.to_dict()


@router.get("/{device_id}/stats")
async def get_device_stats(device_id: str, db: AsyncSession = Depends(get_db)):
    """Obtener estadísticas del dispositivo"""
    service = DeviceService()
    stats = await service.get_device_stats(db, device_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Device no encontrado")
    return stats


@router.put("/{device_id}")
async def update_device(device_id: str, update: DeviceUpdate, db: AsyncSession = Depends(get_db)):
    """Actualizar información del dispositivo"""
    service = DeviceService()
    device = await service.update_device_info(db, device_id, update.name, update.location)
    if not device:
        raise HTTPException(status_code=404, detail="Device no encontrado")
    await db.commit()
    return device.to_dict()


@router.post("/{device_id}/deactivate")
async def deactivate_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Desactivar dispositivo"""
    service = DeviceService()
    device = await service.deactivate_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device no encontrado")
    await db.commit()
    return device.to_dict()


@router.post("/{device_id}/activate")
async def activate_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Activar dispositivo"""
    service = DeviceService()
    device = await service.activate_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device no encontrado")
    await db.commit()
    return device.to_dict()
