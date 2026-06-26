#!/usr/bin/env bash
# =============================================================================
# Intensicare — run-tests.sh
# Executa pytest dentro do container Docker com o boilerplate tratado.
#
# Uso:
#   ./scripts/run-tests.sh                          # todos os testes
#   ./scripts/run-tests.sh -v                       # verbose
#   ./scripts/run-tests.sh tests/test_mews.py       # arquivo específico
#   ./scripts/run-tests.sh -k "test_calculate"      # filtro por nome
#   ./scripts/run-tests.sh -m integration           # marker
#   ./scripts/run-tests.sh --cov=src/intensicare    # cobertura
#
# Variáveis de ambiente:
#   INTENSICARE_CONTAINER  — nome do container (default: intensicare-api)
#   DOCKER_COMPOSE         — comando docker compose (default: docker compose)
# =============================================================================

set -euo pipefail

# ── Configuração ────────────────────────────────────────────────────────────
CONTAINER="${INTENSICARE_CONTAINER:-intensicare-api}"
COMPOSE="${DOCKER_COMPOSE:-docker compose}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Função para log com cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Help ────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Intensicare — Test Runner (Docker)"
    echo ""
    echo "USO:"
    echo "  $0 [pytest args...]"
    echo ""
    echo "EXEMPLOS:"
    echo "  $0                                          # todos os testes"
    echo "  $0 -v                                       # verbose"
    echo "  $0 tests/test_mews.py                       # arquivo específico"
    echo "  $0 -k 'test_calculate'                      # filtro por nome"
    echo "  $0 -m integration                           # marcador"
    echo "  $0 --cov=src/intensicare --cov-report=html  # cobertura"
    echo ""
    echo "ENV VARS:"
    echo "  INTENSICARE_CONTAINER   container alvo (default: intensicare-api)"
    echo "  DOCKER_COMPOSE          comando compose (default: docker compose)"
    exit 0
fi

# ── Verifica se o container está rodando ────────────────────────────────────
echo -e "${CYAN}[run-tests]${NC} Verificando container '${CONTAINER}'..."

if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "${CONTAINER}"; then
    echo -e "${RED}[run-tests]${NC} ✗ Container '${CONTAINER}' não está rodando."
    echo ""
    echo "  Para iniciar o ambiente de desenvolvimento:"
    echo "    make dev-up"
    echo ""
    echo "  Para ver os containers ativos:"
    echo "    docker ps"
    echo ""
    exit 1
fi

echo -e "${GREEN}[run-tests]${NC} ✓ Container '${CONTAINER}' está rodando."

# ── Constrói o comando pytest ───────────────────────────────────────────────
PYTEST_ARGS="${*:-tests -v}"

echo -e "${CYAN}[run-tests]${NC} Executando: pytest ${PYTEST_ARGS}"
echo ""

# ── Executa no container ────────────────────────────────────────────────────
${COMPOSE} exec api pytest ${PYTEST_ARGS}
EXIT_CODE=$?

echo ""
if [[ ${EXIT_CODE} -eq 0 ]]; then
    echo -e "${GREEN}[run-tests]${NC} ✓ Todos os testes passaram."
else
    echo -e "${RED}[run-tests]${NC} ✗ Testes falharam (exit code: ${EXIT_CODE})."
fi

exit ${EXIT_CODE}
