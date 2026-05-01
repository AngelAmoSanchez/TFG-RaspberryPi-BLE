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
    git

# Habilitar Bluetooth siempre
echo "Habilitando Bluetooth..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Crear entorno virtual de Python e instalar dependencias
echo "Configurando entorno virtual de Python..."
PROJECT_ROOT="$(pwd)"

# Eliminar venv antiguo si existe
if [ -d "venv" ]; then
    echo "Eliminando entorno virtual antiguo..."
    rm -rf venv
fi

# Crear venv
python3 -m venv --copies venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "Otorgando permisos BLE al proyecto..."
sudo setcap cap_net_raw,cap_net_admin+eip "$PROJECT_ROOT/venv/bin/python3"

deactivate

# Crear directorios
echo "Creando directorios de trabajo..."
mkdir -p logs data
sudo chown -R pi:pi /home/pi/TFG-RaspberryPi-BLE/raspberry-pi/logs
chmod -R 775 /home/pi/TFG-RaspberryPi-BLE/raspberry-pi/logs

# Copiar .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creando archivo de configuración..."
        cp .env.example .env
        echo "IMPORTANTE - Edita el archivo .env con las credenciales correctas"
    fi
fi

# Crear wrapper script para ejecutar con sudo
echo "Creando script de ejecución..."
cat > run.sh << 'WRAPPER'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
exec python3 src/main.py
WRAPPER

chmod +x run.sh

# Configurar servicio systemd
echo "Configurando servicio systemd..."
SYSTEMD_FILE="/etc/systemd/system/ble-scanner.service"

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
ExecStart=$PROJECT_ROOT/venv/bin/python3 src/main.py

Restart=always
RestartSec=15
StartLimitBurst=10
StartLimitInterval=200

Environment="PYTHONUNBUFFERED=1"

TimeoutStartSec=30
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recargar todo el systemd
sudo systemctl daemon-reload

echo ""
echo "============== Instalación completada =============="
echo ""
echo "Pasos siguientes:"
echo ""
echo "1. Editar configuración (OBLIGATORIO):"
echo "   nano .env"
echo "   # Añadir MQTT_USERNAME y MQTT_PASSWORD"
echo ""
echo "2. Probar manualmente:"
echo "   sudo ./run.sh"
echo "   # Debe mostrar: OK - MQTT conectado"
echo ""
echo "3. Habilitar auto-inicio:"
echo "   sudo systemctl enable ble-scanner"
echo "   sudo systemctl start ble-scanner"
echo ""
echo "4. Ver logs:"
echo "   sudo journalctl -u ble-scanner -f"
echo ""
echo "5. Ver estado:"
echo "   sudo systemctl status ble-scanner"
echo ""
