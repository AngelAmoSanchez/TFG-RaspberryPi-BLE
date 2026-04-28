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
    git \
    sqlite3

# Habilitar Bluetooth siempre
echo "Habilitando Bluetooth..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Crear entorno virtual de Python e instalar dependencias
echo "Configurando entorno virtual de Python..."
PROJECT_ROOT="$(pwd)"

python3 -m venv --copies venv
source venv/bin/activate
pip install --upgrade pip -qq
pip install -r requirements.txt -qq

echo "Otorgando permisos BLE al proyecto..."
sudo setcap cap_net_raw,cap_net_admin+eip "$PROJECT_ROOT/venv/bin/python3"

# Crear los directorios necesarios
echo "Creando directorios de trabajo..."
mkdir -p logs data

# Copiar archivo de configuración de ejemplo
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creando archivo de configuración..."
        cp .env.example .env
        echo "IMPORTANTE - Edita el archivo .env con las credenciales correctas"
    fi
fi

deactivate

# Configurar servicio systemd para auto-inicio
echo "Configurando inicio automático (systemd)..."
SYSTEMD_FILE="/etc/systemd/system/iot-agent.service"

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
WorkingDirectory=$PROJECT_ROOT

ExecStartPre=/bin/sleep 5
ExecStart=$PROJECT_ROOT/venv/bin/python3 -m src.main

Restart=always
RestartSec=15
StartLimitBurst=10
StartLimitInterval=200

StandardOutput=append:$PROJECT_ROOT/logs/system.log
StandardError=append:$PROJECT_ROOT/logs/error.log
SyslogIdentifier=iot-agent

Environment="PYTHONUNBUFFERED=1"

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
echo "     - Primero editar archivo de configuración: nano .env"
echo ""
echo "     Manual:"
echo "       ./scripts/run_system.sh"
echo ""
echo "     Automático (al iniciar la Raspberry Pi):"
echo "       ./scripts/setup_autostart.sh"
echo ""
echo "     Ver logs:"
echo "       tail -f logs/system.log"
echo ""
