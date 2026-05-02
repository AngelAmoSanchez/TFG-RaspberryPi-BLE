import asyncio
import logging
from typing import Set

from fastapi import WebSocket

from ..utils import timezone_utils

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Administra las conexiones WebSocket y la comunicación con los clientes"""

    def __init__(self):
        """Inicializa administrador de WebSocket"""
        self.active_connections: Set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Acepta una nueva conexión WebSocket

        Args:
            websocket: conexión WebSocket
        """
        await websocket.accept()
        async with self.lock:
            self.active_connections.add(websocket)
        logger.info(f"OK - Cliente WebSocket conectado (total: {len(self.active_connections)})")

    async def disconnect(self, websocket: WebSocket):
        """Elimina una conexión WebSocket

        Args:
            websocket: conexión WebSocket
        """
        async with self.lock:
            self.active_connections.discard(websocket)
        logger.info(f"OK - Cliente WebSocket desconectado (total: {len(self.active_connections)})")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Envia un mensaje a un cliente WebSocket específico

        Args:
            message: Mensaje dict a enviar
            websocket: conexión WebSocket del cliente
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"ERROR - Error enviando mensaje personal: {e}")

    async def broadcast(self, message: dict):
        """Envia un mensaje a todos los clientes WebSocket conectados

        Args:
            message: Mesnaje dict a enviar
        """
        if not self.active_connections:
            return

        disconnected = set()

        async with self.lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"ERROR - Error enviando mensaje a cliente: {e}")
                    disconnected.add(connection)

        # Eliminar conexiones desconectadas
        if disconnected:
            async with self.lock:
                self.active_connections -= disconnected

    async def broadcast_detection_event(self, device_id: str, detections_count: int):
        """Evento de nueva detección para un dispositivo específico

        Args:
            device_id: Identificador del dispositivo IoT
            detections_count: Número de nuevas detecciones
        """
        message = {
            "type": "detection_event",
            "timestamp": timezone_utils.now().isoformat(),
            "device_id": device_id,
            "count": detections_count,
        }

        await self.broadcast(message)

    async def broadcast_stats_update(self, stats: dict):
        """Evento de actualización de estadísticas

        Args:
            stats: Diccionario con las estadísticas actualizadas
        """
        message = {
            "type": "stats_update",
            "timestamp": timezone_utils.now().isoformat(),
            "data": stats,
        }

        await self.broadcast(message)

    def get_connection_count(self) -> int:
        """Devuelve el número de conexiones WebSocket activas"""
        return len(self.active_connections)


# Instancia global del WebSocketManager
ws_manager = WebSocketManager()
