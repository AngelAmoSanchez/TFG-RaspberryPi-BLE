#!/bin/bash
echo "====== Sistema de Conteo Bluetooth BLE local en Raspberry Pi ======"

# VERIFICACIONES PREVIAS

# Verificar que estamos en el directorio raiz del proyecto
if [ ! -f "README.md" ]; then
    echo "ERROR - Ejecuta desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que el Bluetooth está encendido
if ! systemctl is-active --quiet bluetooth; then
    echo "Iniciando servicio Bluetooth..."
    sudo systemctl start bluetooth
    sleep 2
fi

# Verificar que se ha relizado la instalación previamente
if [ ! -d "raspberry-pi/venv" ]; then
    echo "ERROR - El proyecto no está instalado"
    echo "Ejecuta primero: ./scripts/install.sh"
    exit 1
fi

# Verificar permisos BLE
if ! getcap raspberry-pi/venv/bin/python3 | grep -q "cap_net_raw"; then
    echo "Configurando permisos BLE..."
    sudo setcap cap_net_raw,cap_net_admin+eip raspberry-pi/venv/bin/python3
fi



# Función para limpiar procesos
cleanup() {
    echo ""
    echo "Deteniendo sistema..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Sistema detenido"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Iniciar backend
echo "Iniciando backend..."
cd raspberry-pi
source venv/bin/activate
python3 -m src.main &
BACKEND_PID=$!

sleep 10  # Esperar a que el backend esté listo

# Verificar que el backend está iniciado
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR - El backend no se inició correctamente"
    echo "Ver logs en: raspberry-pi/logs/system.log"
    exit 1
fi

echo "OK - Backend iniciado (PID: $BACKEND_PID)"

# Iniciar frontend
echo "Iniciando frontend..."
cd ../web-interface
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========= Sistema iniciado ========="
echo "  - Backend: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - Documentación: http://localhost:8000/docs"
echo ""
echo "Presiona Ctrl+C para detener el sistema"

wait
