import asyncio
import logging
import sys
from datetime import datetime

import uvicorn

from .application.use_cases import (
    ExportDataUseCase,
    GetStatisticsUseCase,
    ProcessDetectionsUseCase,
)
from .config import AppConfig
from .domain.services import (
    AnonymizationService,
    PeopleEstimatorService,
    PermanenceService,
    ZoneClassifierService,
)
from .infrastructure.api import create_app
from .infrastructure.bluetooth_scanner import MockBLEScanner
from .infrastructure.repository import SQLiteDeviceRepository

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/system.log"),
    ],
)
logger = logging.getLogger(__name__)


class Application:
    """Aplicación principal que orquesta todos los componentes del sistema"""

    def __init__(self, config: AppConfig, use_mock_bluetooth: bool = False):
        """
        Args:
            config: Configuración de la aplicación
            use_mock_bluetooth: Si True, usa scanner mock (desarrollo)
        """
        self.config = config
        logger.info("=== Inicializando Sistema de Conteo Bluetooth BLE ===")

        # Servicios de dominio
        logger.info("Inicializando servicios de dominio...")
        self.anonymizer = AnonymizationService()
        self.zone_classifier = ZoneClassifierService(
            near_threshold=config.zone.near_threshold,
            medium_threshold=config.zone.medium_threshold,
        )
        self.people_estimator = PeopleEstimatorService()
        self.permanence_service = PermanenceService(
            min_permanence_minutes=config.permanence.min_permanence_minutes
        )

        # Adaptadores de infraestructura
        logger.info("Inicializando adaptadores de infraestructura...")

        # Repositorio en SQLite
        self.repository = SQLiteDeviceRepository(config.database.db_path)

        # Escaner Bluetooth (Mock de respaldo)
        if use_mock_bluetooth:
            self.scanner = MockBLEScanner()
            logger.info("WARN - Usando escáner BLE MOCK")
        else:
            from .infrastructure.bluetooth_scanner import BleakBLEScanner

            self.scanner = BleakBLEScanner(scan_duration=config.bluetooth.scan_duration)
            logger.info("OK - Usando escáner BLE real (Bleak)")

        # Casos de uso
        logger.info("Configurando casos de uso...")
        self.process_detections_uc = ProcessDetectionsUseCase(
            scanner=self.scanner,
            repository=self.repository,
            zone_classifier=self.zone_classifier,
            anonymizer=self.anonymizer,
            permanence_service=self.permanence_service,
        )

        self.get_statistics_uc = GetStatisticsUseCase(
            repository=self.repository, estimator=self.people_estimator
        )

        self.export_data_uc = ExportDataUseCase(repository=self.repository)

        # API REST
        logger.info("Creando API REST...")
        self.api = create_app(
            get_stats_use_case=self.get_statistics_uc,
            export_use_case=self.export_data_uc,
        )

        logger.info("OK - Aplicación inicializada correctamente")

    async def initialize(self):
        """Inicializa la aplicación (BD, etc.)"""
        logger.info("Inicializando base de datos...")

        # Crear directorio de logs
        import os

        os.makedirs("logs", exist_ok=True)

        # Inicializar base de datos
        await self.repository.initialize()
        logger.info("OK - Base de datos lista")

    async def run_detection_loop(self):
        """Loop principal de detección Bluetooth BLE ejecutando escaneos periódicos en segundo plano"""
        logger.info(
            f"Iniciando loop de detección BLE "
            f"(intervalo: {self.config.bluetooth.scan_interval}s)"
        )

        consecutive_errors = 0
        max_consecutive_errors = 5

        while True:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[{timestamp}] Escaneando dispositivos Bluetooth...")

                # Procesar detecciones
                devices = await self.process_detections_uc.execute()

                logger.info(
                    f"[{timestamp}] ===> Ciclo completado: {len(devices)} dispositivos procesados"
                )

                # Resetear contador de errores si todo va bien
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"ERROR - Error en el escaneo ({consecutive_errors}/{max_consecutive_errors}): {e}",
                    exc_info=True,
                )

                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"CRITICAL - Demasiados errores consecutivos ({consecutive_errors}). "
                    )
                    # TODO: Pensado tal vez implementar una lógica de recuperación o notificación
                    break

            # Esperar antes del siguiente escaneo
            await asyncio.sleep(self.config.bluetooth.scan_interval)

    def run_api_server(self):
        """Ejecuta el servidor API REST usando Uvicorn"""
        logger.info(
            f"Iniciando servidor API REST en "
            f"http://{self.config.api.host}:{self.config.api.port}"
        )
        logger.info(f"Documentación disponible en http://localhost:{self.config.api.port}/docs")

        uvicorn.run(
            self.api,
            host=self.config.api.host,
            port=self.config.api.port,
            reload=self.config.api.reload,
            log_level="info",
        )

    async def start(self):
        """Inicia todos los componentes del sistema"""
        await self.initialize()

        logger.info("=== Sistema completamente iniciado ===")
        logger.info("Presiona Ctrl+C para detener el sistema")

        # Ejecutar API y loop de detección
        detection_task = asyncio.create_task(self.run_detection_loop())

        # uvicorn.run es bloqueante, así que lo ejecutamos en thread separado
        import threading

        api_thread = threading.Thread(target=self.run_api_server, daemon=True)
        api_thread.start()

        # Esperar al loop de detección (corre indefinidamente)
        try:
            await detection_task
        except KeyboardInterrupt:
            logger.info("\n=== Sistema detenido por el usuario ===")


async def main():
    """Función principal"""
    print("=== Sistema de Conteo de Personas Bluetooth ===")

    # Cargar configuración
    config = AppConfig.load_default()

    # Crear aplicación
    # use_mock_bluetooth=True para usar datos simulados
    app = Application(config, use_mock_bluetooth=False)

    # Iniciar sistema
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n Sistema detenido por el usuario correctamente")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Error al detener el sistema: {e}", exc_info=True)
        sys.exit(1)
