#!/bin/bash
set -e
echo "Instalando Hermes Agent..."
pip install hermes-agent
echo "Iniciando Hermes..."
python3 main.py
