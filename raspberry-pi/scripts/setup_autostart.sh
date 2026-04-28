#!/bin/bash

echo "=================== Configuración de Inicio Automático ==================="
echo ""

# Verificar primero que el servicio existe
if [ ! -f "/etc/systemd/system/iot-agent.service" ]; then
    echo "ERROR - Servicio systemd no encontrado"
    echo "Ejecuta primero: ./install.sh"
    exit 1
fi

# Habilitar servicio
echo "Habilitando servicio systemd..."
sudo systemctl enable iot-agent

# Iniciar servicio ahora
echo "Iniciando servicio..."
sudo systemctl start iot-agent

# Esperar un poco
sleep 3

# Verificar estado
if systemctl is-active --quiet iot-agent; then
    echo ""
    echo "========= Servicio configurado y corriendo ========="
    echo ""
    echo "Comandos útiles:"
    echo "  Ver estado:    sudo systemctl status iot-agent"
    echo "  Ver logs:      sudo journalctl -u iot-agent -f"
    echo "  Ver logs app:  tail -f logs/system.log"
    echo "  Reiniciar:     sudo systemctl restart iot-agent"
    echo "  Parar:         sudo systemctl stop iot-agent"
    echo "  Deshabilitar:  sudo systemctl disable iot-agent"
    echo ""
    echo "El sistema ahora se iniciará automáticamente al encender la Raspberry Pi"
else
    echo ""
    echo "ERROR - Error al iniciar el servicio"
    echo "Ver logs: sudo journalctl -u iot-agent -xe"
    exit 1
fi
