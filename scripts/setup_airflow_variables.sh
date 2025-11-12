#!/bin/bash

# Script para configurar variables de Airflow para el Market Data DAG
# Uso: ./scripts/setup_airflow_variables.sh

set -e

echo "=================================================="
echo "  Configuración de Variables de Airflow"
echo "  Market Data DAG"
echo "=================================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para crear variable
create_variable() {
    local key=$1
    local value=$2
    local description=$3
    
    echo -e "${BLUE}Creando variable:${NC} $key = $value"
    docker compose exec -T airflow-scheduler airflow variables set "$key" "$value" 2>&1 | grep -v "WARNING" || true
    echo -e "${GREEN}✓${NC} Variable '$key' creada"
    echo ""
}

# Función para verificar variable
check_variable() {
    local key=$1
    echo -e "${BLUE}Verificando variable:${NC} $key"
    docker compose exec -T airflow-scheduler airflow variables get "$key" 2>&1 | grep -v "WARNING" || echo "  (No configurada)"
    echo ""
}

echo "Este script configurará las siguientes variables de Airflow:"
echo ""
echo "  • market_data.default_ticker"
echo "  • market_data.max_retries"
echo "  • market_data.retry_delay"
echo "  • market_data.sensor_poke_interval"
echo "  • market_data.sensor_timeout"
echo ""
echo -e "${YELLOW}Nota:${NC} Estas variables tienen prioridad sobre las variables de entorno (.env)"
echo ""

read -p "¿Deseas continuar? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Operación cancelada."
    exit 1
fi

echo ""
echo "=================================================="
echo "  Creando Variables"
echo "=================================================="
echo ""

# Crear variables con valores por defecto
create_variable "market_data.default_ticker" "AAPL" "Default ticker symbol"
create_variable "market_data.max_retries" "3" "Maximum number of API retry attempts"
create_variable "market_data.retry_delay" "5" "Delay in seconds between retries"
create_variable "market_data.sensor_poke_interval" "30" "Sensor poke interval in seconds"
create_variable "market_data.sensor_timeout" "600" "Sensor timeout in seconds"

echo "=================================================="
echo "  Variables Creadas"
echo "=================================================="
echo ""

# Verificar variables
echo "Verificando variables creadas..."
echo ""

docker compose exec -T airflow-scheduler airflow variables list 2>&1 | grep "market_data" || echo "  No se encontraron variables"

echo ""
echo "=================================================="
echo "  Configuración Completada"
echo "=================================================="
echo ""
echo -e "${GREEN}✓${NC} Variables de Airflow configuradas correctamente"
echo ""
echo "Puedes modificar estas variables desde:"
echo "  • UI de Airflow: http://localhost:8080 → Admin → Variables"
echo "  • CLI: docker compose exec airflow-scheduler airflow variables set KEY VALUE"
echo ""
echo "Para ver la configuración activa, revisa los logs del scheduler:"
echo "  docker compose logs airflow-scheduler | grep 'CONFIGURACIÓN DEL DAG'"
echo ""

