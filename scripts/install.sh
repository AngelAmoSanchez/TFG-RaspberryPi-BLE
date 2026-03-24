#!/bin/bash
set -e  # Salir si ocurre un error

echo "=== Instalación del Sistema de Conteo Bluetooth BLE ==="

# Actualizar el sistema antes de instalar dependencias
echo "Actualizando sistema..."
sudo apt-get update -qq

# Instalar dependencias del sistema
echo "Instalando dependencias del sistema..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    bluetooth \
    bluez \
    nodejs \
    npm \
    sqlite3


# Habilitar Bluetooth siempre
echo "Habilitando Bluetooth..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth


# Crear entorno virtual de Python e instalar dependencias
echo "Configurando entorno virtual de Python..."
PROJECT_ROOT="$(pwd)"
cd raspberry-pi

python3 -m venv --copies venv
source venv/bin/activate
pip install --upgrade pip -qq
pip install -r requirements.txt -qq

echo "Otorgando permisos BLE al proyecto..."
sudo setcap cap_net_raw,cap_net_admin+eip "$PROJECT_ROOT/raspberry-pi/venv/bin/python3"

# Inicializar la base de datos
echo "Inicializando la base de datos..."
python3 << 'PYEOF'
import asyncio
from src.infrastructure.repository import SQLiteDeviceRepository

async def init():
    repo = SQLiteDeviceRepository()
    await repo.initialize()
    print("OK - Base de datos inicializada")

asyncio.run(init())
PYEOF

# Crear los demás directorios necesarios
mkdir -p data exports logs

deactivate
cd ..

# Instalar dependencias del frontend
echo "Instalando dependencias del frontend..."
cd web-interface
npm install > /dev/null 2>&1
echo "OK: Dependencias del frontend instaladas"
cd ..



# Configurar servicio systemd para auto-inicio
echo "Configurando inicio automático (systemd)..."
SYSTEMD_FILE="/etc/systemd/system/bluetooth-counter.service"

sudo tee $SYSTEMD_FILE > /dev/null << EOF
[Unit]
Description=Bluetooth People Counter Service
Documentation=https://github.com/AngelAmoSanchez/TFG-RaspberryPi-BLE
After=network.target bluetooth.target
Wants=bluetooth.target
BindsTo=bluetooth.target

[Service]
Type=exec
User=$USER
WorkingDirectory=$(pwd)/raspberry-pi

ExecStartPre=/bin/sleep 5
ExecStart=$(pwd)/raspberry-pi/venv/bin/python3 -m src.main

Restart=always
RestartSec=15
StartLimitBurst=10
StartLimitInterval=200

StandardOutput=append:$(pwd)/raspberry-pi/logs/system.log
StandardError=append:$(pwd)/raspberry-pi/logs/error.log
SyslogIdentifier=bluetooth-counter

TimeoutStartSec=30
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recargar todo el systemd
sudo systemctl daemon-reload



echo ""
echo "=================== Instalación completada ==================="
echo ""
echo "Para ejecutar el sistema:"
echo "  Manual:"
echo "   ./scripts/run_system.sh"
echo ""
echo "  Automático (al iniciar la Raspberry Pi):"
echo "   ./scripts/setup_autostart.sh"
echo ""

