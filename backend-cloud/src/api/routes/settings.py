from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


class ThresholdUpdate(BaseModel):
    """Modelo para actualizar umbrales"""

    near_threshold: int = Field(..., ge=-127, le=-1, description="RSSI para zona NEAR (ej: -60)")
    medium_threshold: int = Field(
        ..., ge=-127, le=-1, description="RSSI para zona MEDIUM (ej: -75)"
    )

    class Config:
        json_schema_extra = {"example": {"near_threshold": -60, "medium_threshold": -75}}


@router.get("/thresholds")
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    """Obtiene los umbrales actuales de RSSI para clasificación de zonas

    Returns:
        dict: Umbrales near y medium
    """
    service = SettingsService()
    thresholds = await service.get_thresholds(db)

    return {
        "near_threshold": thresholds["near_threshold"],
        "medium_threshold": thresholds["medium_threshold"],
        "description": {
            "near": f"RSSI ≥ {thresholds['near_threshold']} dBm",
            "medium": f"{thresholds['medium_threshold']} dBm ≤ RSSI < {thresholds['near_threshold']} dBm",
            "far": f"RSSI < {thresholds['medium_threshold']} dBm",
        },
    }


@router.put("/thresholds")
async def update_thresholds(thresholds: ThresholdUpdate, db: AsyncSession = Depends(get_db)):
    """Actualiza los umbrales de RSSI y recalcula todas las zonas

    Args:
        thresholds: Nuevos valores de umbrales

    Returns:
        dict: Confirmación y estadísticas de recalculo
    """
    # Validar que near_threshold > medium_threshold
    if thresholds.near_threshold <= thresholds.medium_threshold:
        raise HTTPException(
            status_code=400, detail="near_threshold debe ser mayor que medium_threshold"
        )

    service = SettingsService()
    result = await service.update_thresholds(
        db, thresholds.near_threshold, thresholds.medium_threshold
    )

    return {
        "message": "Umbrales actualizados correctamente",
        "thresholds": {
            "near_threshold": thresholds.near_threshold,
            "medium_threshold": thresholds.medium_threshold,
        },
        "recalculated": {
            "total_detections": result["recalculated_count"],
            "updated_to_near": result["updated_to_near"],
            "updated_to_medium": result["updated_to_medium"],
            "updated_to_far": result["updated_to_far"],
        },
    }


@router.post("/thresholds/reset")
async def reset_thresholds(db: AsyncSession = Depends(get_db)):
    """Resetea los umbrales a valores por defecto (-60, -75)

    Returns:
        dict: Confirmación
    """
    service = SettingsService()
    await service.update_thresholds(db, -60, -75)

    return {
        "message": "Umbrales reseteados a valores por defecto",
        "thresholds": {"near_threshold": -60, "medium_threshold": -75},
    }
