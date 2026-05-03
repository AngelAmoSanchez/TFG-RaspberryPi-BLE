#!/bin/bash

set -e

echo "=============================================="
echo "Configuración del Sistema de Actualizaciones OTA"
echo "=============================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "ota/ota_update.py" ]; then
    echo "ERROR: Este script debe ejecutarse desde /home/pi/TFG-RaspberryPi-BLE/raspberry-pi"
    exit 1
fi

# Definir rutas
PROJECT_ROOT="$(pwd)"
SYSTEMD_SERVICE="/etc/systemd/system/ota-updater.service"

echo "Rutas del proyecto:"
echo "  - Proyecto: $PROJECT_ROOT"
echo "  - Servicio: $SYSTEMD_SERVICE"
echo ""

# Verificar que existe el entorno virtual
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "ERROR: No se encontró el entorno virtual en $PROJECT_ROOT/venv"
    echo "Ejecuta primero: ./install.sh"
    exit 1
fi

# Verificar que existe Git
if ! command -v git &> /dev/null; then
    echo "ERROR: Git no está instalado"
    exit 1
fi

# Crear directorio ota si no existe
echo "Creando directorio OTA..."
mkdir -p "$PROJECT_ROOT/ota"

# Inicializar archivo de versión si no existe
if [ ! -f "$PROJECT_ROOT/ota/version.json" ]; then
    echo "Creando archivo de versión inicial..."
    cat > "$PROJECT_ROOT/ota/version.json" << EOF
{
  "commit_hash": "initial",
  "last_update": "$(date -Iseconds)"
}
EOF
fi

# Crear servicio systemd para OTA updater
echo "Configurando servicio systemd..."

sudo tee $SYSTEMD_SERVICE > /dev/null << EOF
[Unit]
Description=Sistema de Actualizaciones OTA para Raspberry
Documentation=https://github.com/AngelAmoSanchez/TFG-RaspberryPi-BLE
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=$PROJECT_ROOT

# Ejecutar OTA updater
ExecStart=$PROJECT_ROOT/venv/bin/python3 -m ota.ota_update

# Reiniciar siempre si falla
Restart=always
RestartSec=30

# Logs
StandardOutput=append:$PROJECT_ROOT/logs/ota.log
StandardError=append:$PROJECT_ROOT/logs/ota-error.log
SyslogIdentifier=ota-updater

# Variables de entorno
Environment="PYTHONUNBUFFERED=1"

# Timeouts
TimeoutStartSec=30
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recargar systemd
echo "Recargando systemd..."
sudo systemctl daemon-reload

# Habilitar servicio para que arranque al inicio
echo "Habilitando inicio automático del servicio OTA..."
sudo systemctl enable ota-updater.service

echo ""
echo "=============================================="
echo "Configuración completada"
echo "=============================================="
echo ""
echo "Comandos útiles:"
echo ""
echo "  Iniciar servicio OTA:"
echo "    sudo systemctl start ota-updater"
echo ""
echo "  Detener servicio OTA:"
echo "    sudo systemctl stop ota-updater"
echo ""
echo "  Ver estado del servicio:"
echo "    sudo systemctl status ota-updater"
echo ""
echo "  Ver logs en tiempo real:"
echo "    tail -f logs/ota.log"
echo ""
echo "  Reiniciar servicio OTA:"
echo "    sudo systemctl restart ota-updater"
echo ""
echo "  Deshabilitar inicio automático:"
echo "    sudo systemctl disable ota-updater"
echo ""
echo "NOTA: El servicio OTA comprobará actualizaciones cada 1 hora."
echo "      Si hay actualizaciones, descargará y reiniciará el agente."
echo ""