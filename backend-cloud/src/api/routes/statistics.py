from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...services.statistics_service import StatisticsService

SPAIN_TZ = ZoneInfo("Europe/Madrid")

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/realtime")
async def get_realtime_stats(
    minutes: int = Query(5, ge=1, le=10080),
    db: AsyncSession = Depends(get_db),  # Hasta 7 días (máximo del seleccionador predeterminado)
):
    """Devuelve estadísticas en tiempo real para los últimos N minutos"""
    service = StatisticsService()
    stats = await service.get_real_time_stats(db, minutes)
    return stats


@router.get("/range")
async def get_range_stats(
    start_time: str = Query(
        ..., description="Fecha y hora de inicio en formato ISO (ej: 2026-04-23T10:00:00)"
    ),
    end_time: str = Query(
        ..., description="Fecha y hora de fin en formato ISO (ej: 2026-04-23T12:00:00)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve estadísticas para un rango específico de fechas y horas"""

    try:
        # Parsear las fechas
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de fecha inválido. Use formato ISO: YYYY-MM-DDTHH:MM:SS. Error: {str(e)}",
        )

    # Validar que start_time < end_time
    if start_dt >= end_dt:
        raise HTTPException(
            status_code=400, detail="La fecha de inicio debe ser anterior a la fecha de fin"
        )

    service = StatisticsService()
    stats = await service.get_range_stats(db, start_dt, end_dt)
    return stats


@router.get("/hourly")
async def get_hourly_stats(date: str = Query(None), db: AsyncSession = Depends(get_db)):
    """Devuelve estadísticas por hora para una fecha"""
    service = StatisticsService()

    if date:
        target_date = datetime.fromisoformat(date).replace(tzinfo=SPAIN_TZ)
    else:
        target_date = datetime.now(SPAIN_TZ)

    stats = await service.get_hourly_stats(db, target_date)

    return {"date": target_date.date().isoformat(), "statistics": stats}


@router.get("/daily")
async def get_daily_stats(
    start_date: str = Query(None),
    end_date: str = Query(None),
    days: int = Query(7),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve estadísticas diarias"""
    service = StatisticsService()

    if end_date:
        end = datetime.fromisoformat(end_date)
    else:
        end = datetime.now(SPAIN_TZ)

    if start_date:
        start = datetime.fromisoformat(start_date)
    else:
        start = end - timedelta(days=days)

    stats = await service.get_daily_stats(db, start, end)

    return {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "statistics": stats,
    }


@router.get("/distribution")
async def get_zone_distribution(hours: int = Query(24), db: AsyncSession = Depends(get_db)):
    """Devuelve la distribución de zonas para un rango de tiempo"""
    service = StatisticsService()

    end_time = datetime.now(SPAIN_TZ)
    start_time = end_time - timedelta(hours=hours)

    distribution = await service.get_zone_distribution(db, start_time, end_time)

    return {"start_time": start_time.isoformat(), "end_time": end_time.isoformat(), **distribution}
