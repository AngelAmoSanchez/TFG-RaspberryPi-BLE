import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..application.use_cases import ExportDataUseCase, GetStatisticsUseCase
from ..domain.models import Statistics

logger = logging.getLogger(__name__)


# DTOs para las respuestas de la API
class StatisticsResponse(BaseModel):
    """DTO para respuesta de estadísticas"""

    time_period: str
    start_time: datetime
    zone: str
    estimated_people: int
    unique_devices: int
    avg_permanence_minutes: float

    @staticmethod
    def from_domain(stat: Statistics) -> "StatisticsResponse":
        return StatisticsResponse(
            time_period=stat.time_period,
            start_time=stat.start_time,
            zone=stat.zone.value,
            estimated_people=stat.estimated_people,
            unique_devices=stat.unique_devices,
            avg_permanence_minutes=round(stat.avg_permanence_minutes, 2),
        )

    class Config:
        json_schema_extra = {
            "example": {
                "time_period": "hour",
                "start_time": "2024-02-03T10:00:00",
                "zone": "near",
                "estimated_people": 5,
                "unique_devices": 8,
                "avg_permanence_minutes": 3.5,
            }
        }


class ZoneSummaryResponse(BaseModel):
    """DTO para resumen por zona en tiempo real"""

    zone: str
    estimated_people: int
    unique_devices: int
    avg_permanence: float


class HealthResponse(BaseModel):
    """DTO para health check"""

    status: str
    timestamp: datetime
    version: str = "1.0.0"


def create_app(
    get_stats_use_case: GetStatisticsUseCase, export_use_case: ExportDataUseCase
) -> FastAPI:

    app = FastAPI(
        title="Bluetooth People Counter API",
        description="Sistema de conteo de personas mediante detección Bluetooth BLE",
        version="1.0.0",
        docs_url="/docs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especificar dominios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """Health check endpoint

        Verifica que el sistema está funcionando correctamente
        """
        return HealthResponse(status="healthy", timestamp=datetime.now())

    @app.get(
        "/api/statistics/hourly",
        response_model=List[StatisticsResponse],
        tags=["Statistics"],
    )
    async def get_hourly_statistics(date: str = None):
        """Obtiene estadísticas por hora para una fecha específica

        Args:
            date: Fecha en formato YYYY-MM-DD (por defecto hoy)

        Returns:
            Lista de estadísticas por hora y zona
        """
        try:
            target_date = datetime.fromisoformat(date) if date else datetime.now()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
            )

        logger.info(f"GET /api/statistics/hourly?date={target_date.date()}")

        stats = await get_stats_use_case.get_hourly(target_date)
        return [StatisticsResponse.from_domain(s) for s in stats]

    @app.get(
        "/api/statistics/daily",
        response_model=List[StatisticsResponse],
        tags=["Statistics"],
    )
    async def get_daily_statistics(start_date: str = None, end_date: str = None):
        """
        Obtiene estadísticas por día para un rango de fechas (RF-07)

        Args:
            start_date: Fecha inicio (por defecto hace 7 días)
            end_date: Fecha fin (por defecto hoy)
        """
        try:
            end = datetime.fromisoformat(end_date) if end_date else datetime.now()
            start = (
                datetime.fromisoformat(start_date)
                if start_date
                else end - timedelta(days=7)
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        if start > end:
            raise HTTPException(
                status_code=400, detail="start_date must be before end_date"
            )

        logger.info(f"GET /api/statistics/daily?start={start.date()}&end={end.date()}")

        stats = await get_stats_use_case.get_daily(start, end)
        return [StatisticsResponse.from_domain(s) for s in stats]

    @app.get(
        "/api/statistics/current",
        response_model=List[ZoneSummaryResponse],
        tags=["Statistics"],
    )
    async def get_current_summary():
        """
        Obtiene resumen actual (última hora) por zona (RRB-05)

        Útil para dashboard en tiempo real (RC-03)
        """
        logger.info("GET /api/statistics/current")

        now = datetime.now()
        stats = await get_stats_use_case.get_hourly(now)

        # Filtrar solo la última hora
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_stats = [s for s in stats if s.start_time == current_hour]

        return [
            ZoneSummaryResponse(
                zone=s.zone.value,
                estimated_people=s.estimated_people,
                unique_devices=s.unique_devices,
                avg_permanence=round(s.avg_permanence_minutes, 1),
            )
            for s in current_stats
        ]

    @app.get("/api/export/csv", tags=["Export"])
    async def export_csv(start_date: str, end_date: str):
        """
        Exporta datos a CSV para un rango de fechas (RF-09)

        Args:
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)

        Returns:
            Archivo CSV descargable
        """
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        logger.info(f"GET /api/export/csv?start={start.date()}&end={end.date()}")

        csv_path = await export_use_case.execute(start, end)

        return FileResponse(
            path=csv_path,
            media_type="text/csv",
            filename=f"detections_{start_date}_{end_date}.csv",
        )

    return app
