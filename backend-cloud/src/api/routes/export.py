"""
Export routes - CSV download endpoints
"""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...database.models import Detection, ZoneEnum

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/detections/csv")
async def export_detections_csv(
    # Filtros de tiempo
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    last_minutes: Optional[int] = Query(None, description="Últimos N minutos"),
    last_hours: Optional[int] = Query(None, description="Últimas N horas"),
    last_days: Optional[int] = Query(None, description="Últimos N días"),
    # Filtros adicionales
    zone: Optional[str] = Query(None, description="Filtrar por zona (near/medium/far)"),
    device_id: Optional[str] = Query(None, description="Filtrar por dispositivo IoT"),
    # Database
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta detecciones a CSV con filtros flexibles.
    
    Prioridad de filtros de tiempo:
    1. start_date + end_date (rango específico)
    2. last_minutes (últimos N minutos)
    3. last_hours (últimas N horas)  
    4. last_days (últimos N días)
    5. Por defecto: últimas 24 horas
    """
    
    # Determinar rango de tiempo
    end_time = datetime.now(timezone.utc)
    
    if start_date and end_date:
        # Rango específico de fechas
        start_time = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        # Asegurar que end_time incluye todo el día
        end_time = end_time.replace(hour=23, minute=59, second=59)
    elif last_minutes:
        start_time = end_time - timedelta(minutes=last_minutes)
    elif last_hours:
        start_time = end_time - timedelta(hours=last_hours)
    elif last_days:
        start_time = end_time - timedelta(days=last_days)
    else:
        # Por defecto: últimas 24 horas
        start_time = end_time - timedelta(hours=24)
    
    # Construir query
    query = select(Detection).where(
        and_(
            Detection.timestamp >= start_time,
            Detection.timestamp <= end_time
        )
    )
    
    # Aplicar filtros adicionales
    if zone:
        try:
            zone_enum = ZoneEnum(zone.lower())
            query = query.where(Detection.zone == zone_enum.value)
        except ValueError:
            pass  # Ignorar zona inválida
    
    if device_id:
        query = query.where(Detection.device_id == device_id)
    
    # Ordenar por timestamp descendente
    query = query.order_by(Detection.timestamp.desc())
    
    # Ejecutar query
    result = await db.execute(query)
    detections = result.scalars().all()
    
    # Crear CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escribir encabezados
    writer.writerow([
        'ID',
        'Device Hash',
        'RSSI (dBm)',
        'Zone',
        'Timestamp',
        'Device ID (IoT)',
        'Date',
        'Time'
    ])
    
    # Escribir datos
    for detection in detections:
        timestamp = detection.timestamp
        writer.writerow([
            detection.id,
            detection.device_hash,
            detection.rssi,
            detection.zone,
            timestamp.isoformat(),
            detection.device_id,
            timestamp.strftime('%Y-%m-%d'),
            timestamp.strftime('%H:%M:%S')
        ])
    
    # Preparar respuesta
    output.seek(0)
    
    # Nombre del archivo basado en filtros
    filename_parts = ['detections']
    if start_date and end_date:
        filename_parts.append(f"{start_date}_to_{end_date}")
    elif last_minutes:
        filename_parts.append(f"last_{last_minutes}min")
    elif last_hours:
        filename_parts.append(f"last_{last_hours}h")
    elif last_days:
        filename_parts.append(f"last_{last_days}d")
    else:
        filename_parts.append("last_24h")
    
    if zone:
        filename_parts.append(f"zone_{zone}")
    
    filename = "_".join(filename_parts) + ".csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )
