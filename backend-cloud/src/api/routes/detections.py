from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...database.models import ZoneEnum
from ...services.detection_processor import DetectionProcessorService
from ...services.device_service import DeviceService

router = APIRouter(prefix="/detections", tags=["detections"])


class DetectionCreate(BaseModel):
    device_hash: str
    rssi: int
    zone: str
    timestamp: Optional[str] = None


class BulkDetectionsCreate(BaseModel):
    device_id: str
    detections: List[dict]


@router.post("/")
async def create_detection(
    detection: DetectionCreate, device_id: str = Query(...), db: AsyncSession = Depends(get_db)
):
    """Crear una única detección"""
    service = DetectionProcessorService()
    device_service = DeviceService()

    timestamp = datetime.fromisoformat(detection.timestamp) if detection.timestamp else None

    result = await service.save_detection(
        db, detection.device_hash, detection.rssi, detection.zone, device_id, timestamp
    )

    await device_service.update_last_seen(db, device_id)
    await db.commit()

    return result.to_dict()


@router.post("/bulk")
async def create_bulk_detections(data: BulkDetectionsCreate, db: AsyncSession = Depends(get_db)):
    """Crea múltiples detecciones a la vez"""
    service = DetectionProcessorService()
    device_service = DeviceService()

    results = await service.save_bulk_detections(db, data.detections, data.device_id)

    await device_service.update_last_seen(db, data.device_id)
    await db.commit()

    return {
        "message": f"Guardadas {len(results)} detecciones",
        "device_id": data.device_id,
        "count": len(results),
    }


@router.get("/recent")
async def get_recent_detections(
    limit: int = Query(100, le=1000), zone: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    """Devuelve las detecciones más recientes por zona"""
    service = DetectionProcessorService()

    zone_enum = ZoneEnum(zone) if zone else None
    detections = await service.get_recent_detections(db, limit, zone_enum)

    return [d.to_dict() for d in detections]


@router.get("/count")
async def get_detection_count(
    hours: int = Query(24), zone: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    """Devuelve el número de dispositivos únicos detectados en un rango de tiempo y zona"""
    service = DetectionProcessorService()

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    try:
        zone_enum = ZoneEnum(zone) if zone else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Zona inválida: {zone}")

    count = await service.get_unique_devices_count(db, start_time, end_time, zone_enum)

    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "zone": zone,
        "unique_devices": count,
        "estimated_people": service.estimate_people(count),
    }
