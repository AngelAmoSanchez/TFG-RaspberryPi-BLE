#!/bin/bash
echo "====== Sistema de Conteo Bluetooth BLE en Raspberry Pi como Agente IoT ======"

# VERIFICACIONES PREVIAS

# Verificar que estamos en el directorio raiz del proyecto
if [ ! -f "requirements.txt" ]; then
    echo "ERROR - Ejecuta desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que el Bluetooth está encendido
if ! systemctl is-active --quiet bluetooth; then
    echo "Iniciando servicio Bluetooth..."
    sudo systemctl start bluetooth
    sleep 2
fi

# Verificar que se ha realizado la instalación previamente
if [ ! -d "venv" ]; then
    echo "ERROR - El proyecto no está instalado"
    echo "Ejecuta primero: ./install.sh"
    exit 1
fi

# Verificar permisos BLE
if ! getcap venv/bin/python3 | grep -q "cap_net_raw"; then
    echo "Configurando permisos BLE..."
    sudo setcap cap_net_raw,cap_net_admin+eip venv/bin/python3
fi

# Verificar archivo de configuración
if [ ! -f ".env" ]; then
    echo "ERROR - Archivo .env no encontrado"
    echo "Copia .env.example a .env y configura tus credenciales"
    exit 1
fi

# Función para limpiar procesos
cleanup() {
    echo ""
    echo "Deteniendo sistema..."
    kill $AGENT_PID 2>/dev/null
    echo "Sistema detenido"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Iniciar agente IoT
echo "Iniciando IoT Agent..."
source venv/bin/activate
python3 -m src.main &
AGENT_PID=$!

sleep 5  # Esperar a que el agente esté listo

# Verificar que el agente está iniciado
if ! kill -0 $AGENT_PID 2>/dev/null; then
    echo "ERROR - El agente no se inició correctamente"
    echo "Ver logs en: logs/system.log"
    exit 1
fi

echo ""
echo "========= Sistema iniciado ========="
echo "  - Agente IoT iniciado (PID: $AGENT_PID)"
echo "  - Modo: $(grep COMMUNICATION_MODE .env | cut -d'=' -f2)"
echo "  - Device ID: $(grep DEVICE_ID .env | cut -d'=' -f2)"
echo ""
echo "  - Ver logs en tiempo real:"
echo "     tail -f logs/system.log"
echo ""
echo "Presiona Ctrl+C para detener el sistema"
echo ""

# Mostrar logs en tiempo real
tail -f logs/system.log &
TAIL_PID=$!

# Función de cleanup actualizada
cleanup() {
    echo ""
    echo "Deteniendo sistema..."
    kill $TAIL_PID 2>/dev/null
    kill $AGENT_PID 2>/dev/null
    echo "Sistema detenido"
    exit 0
}

wait $AGENT_PID
