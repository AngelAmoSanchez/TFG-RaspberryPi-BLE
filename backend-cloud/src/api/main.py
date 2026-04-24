import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import detections, devices, export, statistics
from src.config import settings
from src.database.connection import close_db, init_db
from src.mqtt.subscriber import start_mqtt_subscriber
from src.utils import timezone_utils
from src.websocket.manager import ws_manager

# Configurar estrructura de logs
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Arranque
    logger.info("=" * 60)
    logger.info(f"{settings.app_name} starting...")
    logger.info(f"Environment: {settings.environment}")
    logger.info("=" * 60)

    # Inicializar base de datos
    await init_db()

    # Iniciar MQTT subscriber si está habilitado
    if settings.mqtt_enabled:
        await start_mqtt_subscriber()

    logger.info("OK - Aplicación iniciada exitosamente")

    yield

    # Apagado
    logger.info("Apagando aplicación...")
    await close_db()
    logger.info("OK - Aplicación apagada")


# Crear FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="Backend cloud para Sistema de Conteo Bluetooth BLE",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(detections.router, prefix=f"/api/{settings.api_version}")
app.include_router(statistics.router, prefix=f"/api/{settings.api_version}")
app.include_router(devices.router, prefix=f"/api/{settings.api_version}")
app.include_router(export.router, prefix=f"/api/{settings.api_version}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.app_name,
        "version": settings.api_version,
        "environment": settings.environment,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": timezone_utils.now().isoformat(),
        "websocket_connections": ws_manager.get_connection_count(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint para actualizaciones en tiempo real"""
    await ws_manager.connect(websocket)

    try:
        while True:
            # Mantener la conexión abierta
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"ERROR - Error en WebSocket: {e}")
        await ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
