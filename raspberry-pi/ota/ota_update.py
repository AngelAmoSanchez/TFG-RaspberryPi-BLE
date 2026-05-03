import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SPAIN_TZ = ZoneInfo("Europe/Madrid")

logger = logging.getLogger(__name__)


class OTAUpdater:
    """Sistema de actualizaciones OTA (Over-The-Air)
    Utiliza Git para descargar actualizaciones desde el repositorio
    """

    def __init__(
        self,
        repo_path: str = "/home/pi/TFG-RaspberryPi-BLE/raspberry-pi",
        version_file: str = "ota/version.json",
        check_interval: int = 3600,
        auto_restart: bool = True,
    ):
        """
        Args:
            repo_path: Ruta al repositorio git
            version_file: Archivo donde se guarda información de versión
            check_interval: Intervalo de chequeo en segundos (por defecto 1 hora)
            auto_restart: Auto-reiniciar servicio tras actualizar
        """
        self.repo_path = Path(repo_path)
        self.version_file = self.repo_path / version_file
        self.check_interval = check_interval
        self.auto_restart = auto_restart
        self.running = False

        logger.info(
            f"Sistema OTA inicializado (comprueba cada {check_interval}s, "
            f"reinicio automático: {auto_restart})"
        )

    def get_current_version(self) -> dict:
        """Obtiene información de versión actual desde archivo JSON

        Devuelve:
            Dict con commit_hash y last_update
        """
        try:
            if self.version_file.exists():
                with open(self.version_file, "r") as f:
                    return json.load(f)
            else:
                # Si no existe, inicializar
                return {"commit_hash": "initial", "last_update": datetime.now(SPAIN_TZ).isoformat()}
        except Exception as e:
            logger.error(f"ERROR - Error al leer archivo de versión: {e}")
            return {"commit_hash": "unknown", "last_update": "unknown"}

    def save_version(self, version_data: dict):
        """Guarda información de versión

        Args:
            version_data: Dict con commit_hash y last_update
        """
        try:
            self.version_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.version_file, "w") as f:
                json.dump(version_data, f, indent=2)

            logger.info(
                f"Información de versión guardada: commit {version_data['commit_hash'][:8]}"
            )

        except Exception as e:
            logger.error(f"ERROR - Error al guardar archivo de versión: {e}")

    def get_remote_commit_hash(self) -> str:
        """Obtiene hash del último commit en remoto

        Devuelve:
            Commit hash del origin/main
        """
        try:
            # Hacer fetch para actualizar referencias remotas
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                timeout=30,
            )

            # Obtener hash del commit remoto
            result = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            remote_hash = result.stdout.strip()
            logger.debug(f"Commit remoto: {remote_hash[:8]}")
            return remote_hash

        except subprocess.TimeoutExpired:
            logger.error("ERROR - Timeout al consultar repositorio remoto")
            return ""
        except subprocess.CalledProcessError as e:
            logger.error(f"ERROR - Error al ejecutar git fetch: {e}")
            return ""
        except Exception as e:
            logger.error(f"ERROR - Error al obtener commit remoto: {e}")
            return ""

    def get_local_commit_hash(self) -> str:
        """Obtiene hash del commit local actual

        Devuelve:
            Commit hash del HEAD local
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            local_hash = result.stdout.strip()
            logger.debug(f"Commit local: {local_hash[:8]}")
            return local_hash

        except Exception as e:
            logger.error(f"ERROR - Error al obtener commit local: {e}")
            return ""

    def check_for_updates(self) -> bool:
        """Verifica si hay actualizaciones disponibles

        Devuelve:
            True si hay actualizaciones disponibles
        """
        logger.info("Verificando actualizaciones disponibles...")

        remote_hash = self.get_remote_commit_hash()
        local_hash = self.get_local_commit_hash()

        if not remote_hash or not local_hash:
            logger.warning("No se puede verificar actualizaciones (error de git)")
            return False

        if remote_hash != local_hash:
            logger.info(f"Actualización disponible: {local_hash[:8]} -> {remote_hash[:8]}")
            return True
        else:
            logger.info("Sistema actualizado (no hay cambios)")
            return False

    def apply_update(self) -> bool:
        """Aplica actualización mediante git pull

        Devuelve:
            True si se aplicó exitosamente
        """
        try:
            logger.info("Aplicando actualización (git pull)...")

            # Hacer stash por si hay cambios locales
            subprocess.run(["git", "stash"], cwd=self.repo_path, capture_output=True, timeout=10)

            # Pull de cambios
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )

            logger.info("Actualización aplicada correctamente")
            logger.debug(f"Salida de git: {result.stdout}")

            # Actualizar archivo de versión
            new_hash = self.get_local_commit_hash()
            version_data = {
                "commit_hash": new_hash,
                "last_update": datetime.now(SPAIN_TZ).isoformat(),
            }
            self.save_version(version_data)

            return True

        except subprocess.TimeoutExpired:
            logger.error("ERROR - Timeout al ejecutar git pull")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"ERROR - Error al ejecutar git pull: {e}")
            logger.error(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"ERROR - Error al aplicar actualización: {e}")
            return False

    def restart_service(self):
        """Reinicia el servicio systemd"""
        try:
            logger.info("Reiniciando servicio...")

            subprocess.run(["sudo", "systemctl", "restart", "iot-agent"], check=True, timeout=10)

            logger.info("Servicio reiniciado correctamente")

        except Exception as e:
            logger.error(f"ERROR - Error al reiniciar servicio: {e}")

    async def run(self):
        """Ejecuta el updater en bucle continuo
        Chequea actualizaciones cada check_interval segundos"""
        logger.info("Sistema de actualizaciones OTA iniciado")
        self.running = True

        current = self.get_current_version()
        logger.info(
            f"Commit actual: {current.get('commit_hash', 'unknown')[:8]}, "
            f"última actualización: {current.get('last_update', 'desconocida')}"
        )

        try:
            while self.running:
                # Esperar intervalo configurado
                await asyncio.sleep(self.check_interval)

                # Verificar si hay actualizaciones
                if self.check_for_updates():
                    # Aplicar actualización
                    if self.apply_update():
                        logger.info("Actualización completada exitosamente")

                        # Auto-reiniciar si está habilitado
                        if self.auto_restart:
                            logger.info("Reiniciando servicio en 5 segundos...")
                            await asyncio.sleep(5)
                            self.restart_service()
                        else:
                            logger.info(
                                "Reinicio automático deshabilitado. "
                                "Reinicia manualmente para aplicar cambios."
                            )
                    else:
                        logger.error("Error al aplicar actualización")

        except asyncio.CancelledError:
            logger.info("Sistema de actualizaciones OTA detenido")
        except Exception as e:
            logger.error(f"Error en sistema OTA: {e}", exc_info=True)

    def stop(self):
        """Detiene el updater"""
        self.running = False


async def main():
    """Punto de entrada para testing del updater"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    updater = OTAUpdater(
        repo_path=os.getcwd(),
        check_interval=60,  # Chequear cada minuto para testing
        auto_restart=False,  # No auto-reiniciar en testing
    )

    try:
        await updater.run()
    except KeyboardInterrupt:
        logger.info("Deteniendo updater...")
        updater.stop()


if __name__ == "__main__":
    asyncio.run(main())
