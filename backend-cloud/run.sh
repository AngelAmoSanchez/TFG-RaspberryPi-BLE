#!/bin/bash
# Script para ejecutar el backend en modo desarrollo

echo "Iniciando Backend Cloud..."

# Activar venv si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ejecutar con uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
