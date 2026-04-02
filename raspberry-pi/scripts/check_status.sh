#!/bin/bash

echo "====== Estado del Sistema AGente IoT ======"
echo ""

# Verificar si el servicio está instalado
if [ ! -f "/etc/systemd/system/iot-agent.service" ]; then
    echo "ERROR - Servicio no instalado"
    echo "   Ejecuta: ./install.sh"
    exit 1
fi

# Estado del servicio
echo "Servicio systemd:"
if systemctl is-active --quiet iot-agent; then
    echo "  OK - Estado: Activo"
else
    echo "  ERROR - Estado: Inactivo"
fi

if systemctl is-enabled --quiet iot-agent; then
    echo "  OK - Auto-inicio: Habilitado"
else
    echo "  WARN - Auto-inicio: Deshabilitado"
fi

echo ""

# Estado de Bluetooth
echo "Bluetooth:"
if systemctl is-active --quiet bluetooth; then
    echo "  OK - Servicio activo"
else
    echo "  ERROR - Servicio inactivo"
fi

# Verificar adapter
if hciconfig hci0 | grep -q "UP RUNNING"; then
    echo "  OK - Adapter disponible"
else
    echo "  WARN - Adapter no detectado"
fi

echo ""

# Configuración
echo "Configuración:"
if [ -f ".env" ]; then
    DEVICE_ID=$(grep "^DEVICE_ID=" .env | cut -d'=' -f2)
    COMM_MODE=$(grep "^COMMUNICATION_MODE=" .env | cut -d'=' -f2)
    MQTT_BROKER=$(grep "^MQTT_BROKER=" .env | cut -d'=' -f2)
    
    echo "  Device ID: $DEVICE_ID"
    echo "  Modo comunicación: $COMM_MODE"
    echo "  MQTT Broker: $MQTT_BROKER"
else
    echo "  ERROR - Archivo .env no encontrado"
fi

echo ""

# Logs recientes
echo "Últimas 5 líneas del log del sistema:"
echo "---"
if [ -f "logs/system.log" ]; then
    tail -n 5 logs/system.log
else
    echo "  (No hay logs aún)"
fi

echo ""
echo "---"
echo ""
echo "Para ver logs en tiempo real: tail -f logs/system.log"
echo "Para ver logs de systemd: sudo journalctl -u iot-agent -f"
