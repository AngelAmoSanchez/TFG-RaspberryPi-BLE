#!/bin/bash

echo "=================== Configuración de Inicio Automático ==================="
echo ""

# Habilitar servicio
echo "Habilitando servicio systemd..."
sudo systemctl enable bluetooth-counter

# Iniciar servicio ahora
echo "Iniciando servicio..."
sudo systemctl start bluetooth-counter

# Esperar un poco
sleep 3

# Verificar estado
if systemctl is-active --quiet bluetooth-counter; then
    echo ""
    echo "========= Servicio configurado y corriendo ========="
    echo ""
    echo "Comandos necesarios:"
    echo "  Ver estado:  sudo systemctl status bluetooth-counter"
    echo "  Ver logs:    sudo journalctl -u bluetooth-counter -f"
    echo "  Parar:       sudo systemctl stop bluetooth-counter"
    echo "  Deshabilitar:sudo systemctl disable bluetooth-counter"
    echo ""
    echo "El sistema ahora se iniciará automáticamente al encender la RPi"
else
    echo "ERROR - Error al iniciar el servicio"
    echo "Ver logs: sudo journalctl -u bluetooth-counter -xe"
    exit 1
fi