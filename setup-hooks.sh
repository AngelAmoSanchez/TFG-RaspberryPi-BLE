#!/bin/bash

set -e

echo ""
echo ""
echo "==================== Git Hooks Setup Script ===================="

# Verificar que estamos en un repositorio git
if [ ! -d ".git" ]; then
    echo "ERROR - No es un repositorio git"
    echo "Ejecuta: git init"
    exit 1
fi

# Instalar pre-commit
echo ""
echo "Instalando pre-commit..."

if command -v pre-commit &> /dev/null; then
    echo "OK - pre-commit ya instalado previamente"
else
    pip install pre-commit
    echo "OK - pre-commit instalado"
fi

echo ""
echo "Instalando hooks de pre-commit..."
pre-commit install
pre-commit install --hook-type commit-msg

echo "OK - Hooks instalados"

# Probar los hooks
echo ""
echo "Probando configuración de hooks..."
pre-commit run --all-files || true

echo ""
echo "================ Instalación completada ================"
echo ""
echo "Hooks instalados:"
echo "  - conventional-pre-commit - Valida los mensajes de commit según Conventional Commits"
echo ""
echo "Comandos útiles:"
echo "  - Actualización de hooks: pre-commit autoupdate"
echo "  - Ejecutar hooks manualmente: pre-commit run --all-files"
echo "  - Reinstalar hooks: pre-commit install"
echo ""

