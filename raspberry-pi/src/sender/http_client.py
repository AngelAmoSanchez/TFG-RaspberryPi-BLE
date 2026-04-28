import logging
from typing import List

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

from scanner.detection import Device

logger = logging.getLogger(__name__)


class HTTPClient:
    """Cliente HTTP REST para publicar detecciones al backend"""

    def __init__(
        self, base_url: str, device_id: str, config=None, api_key: str = None, timeout: int = 10
    ):
        """
        Args:
            base_url: URL base del API (ej: "https://api.example.com")
            device_id: ID único de este dispositivo
            config: Objeto de configuración
            api_key: API key para autenticación (opcional)
            timeout: Timeout de requests en segundos
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("La librería Requests no está instalada.")

        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.config = config
        self.api_key = api_key
        self.timeout = timeout

        self.detections_endpoint = f"{self.base_url}/api/v1/detections/bulk"

        logger.info(
            f"Cliente HTTP inicializado (endpoint: {self.detections_endpoint}, "
            f"dispositivo: {device_id})"
        )

    def connect(self) -> bool:
        """Verifica conectividad con el backend

        Devuelve:
            True si el backend está alcanzable
        """
        try:
            logger.info("Probando conectividad HTTP...")

            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=self.timeout)

            if response.status_code == 200:
                logger.info("OK - HTTP backend alcanzable")
                return True
            else:
                logger.warning(f"Backend respondió con estado {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            logger.error("ERROR - No se puede alcanzar el backend (error de conexión)")
            return False
        except requests.exceptions.Timeout:
            logger.error("ERROR - Backend timeout")
            return False
        except Exception as e:
            logger.error(f"ERROR - Error de conectividad HTTP: {e}")
            return False

    def disconnect(self):
        """HTTP no requiere desconexión explícita"""
        logger.info("Cliente HTTP desconectado")

    def publish_detections(self, detections: List[Device]) -> bool:
        """Publica lista de detecciones por HTTP POST

        Args:
            detections: Lista de detecciones procesadas

        Devuelve:
            True si se publicó exitosamente
        """
        if not detections:
            logger.debug("Ninguna detección para publicar")
            return True

        try:
            # Crear payload en formato bulk
            payload = {
                "device_id": self.device_id,
                "detections": [
                    {
                        "device_hash": det.device_hash,
                        "rssi": det.rssi,
                        "zone": det.zone.value,  # Convertir enum a string
                        "timestamp": det.timestamp.isoformat(),
                    }
                    for det in detections
                ],
            }

            if self.config:
                if self.config.device_name:
                    payload["name"] = self.config.device_name
                if self.config.device_location:
                    payload["location"] = self.config.device_location

            # Headers
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            # Enviar POST
            logger.info(f"Enviando {len(detections)} detecciones por HTTP...")
            response = requests.post(
                self.detections_endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code in [200, 201]:
                logger.info(
                    f"OK - Publicadas {len(detections)} detecciones por HTTP "
                    f"(estado: {response.status_code})"
                )
                return True
            else:
                logger.error(
                    f"ERROR - Publicación HTTP fallida (estado: {response.status_code}, "
                    f"body: {response.text[:200]})"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error("ERROR - Timeout en solicitud HTTP")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("ERROR - Error de conexión HTTP")
            return False
        except Exception as e:
            logger.error(f"ERROR - Error de publicación HTTP: {e}")
            return False

    def is_connected(self) -> bool:
        """Verifica si el backend está alcanzable

        Devuelve:
            True si está conectado
        """
        return self.connect()

    def get_buffer_size(self) -> int:
        """HTTP no tiene buffer (es síncrono)"""
        return 0
