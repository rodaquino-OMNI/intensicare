# =============================================================================
# Intensicare — Makefile para comandos de desenvolvimento
# =============================================================================

SHELL := /bin/bash
.SILENT:
.DEFAULT_GOAL := help

# Cores no terminal
GREEN  := \033[0;32m
YELLOW := \033[1;33m
CYAN   := \033[0;36m
RED    := \033[0;31m
NC     := \033[0m  # No Color

# Variáveis
PYTHON     ?= python3.12
PIP        ?= pip
DOCKER     ?= docker
COMPOSE    ?= docker compose
POETRY     ?= poetry
RUFF       ?= ruff
MYPY       ?= mypy
PYTEST     ?= pytest
ALEMBIC    ?= alembic

VENV       ?= .venv
SRC_DIR    := src
TEST_DIR   := tests

# ═══════════════════════════════════════════════════════════════════════════
# Ajuda
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: help
help: ## Mostra esta mensagem de ajuda
	@echo "$(CYAN)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║              Intensicare — Comandos de Desenvolvimento          ║$(NC)"
	@echo "$(CYAN)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Ambiente de Desenvolvimento:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ═══════════════════════════════════════════════════════════════════════════
# Setup inicial
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: setup
setup: setup-env setup-hooks ## Configura ambiente completo (venv + hooks + .env)

.PHONY: setup-env
setup-env: ## Cria virtualenv e instala dependências
	@echo "$(GREEN)[setup]$(NC) Criando virtualenv com Python $(PYTHON)..."
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)[setup]$(NC) Instalando dependências..."
	$(VENV)/bin/$(PIP) install --upgrade pip setuptools wheel
	$(VENV)/bin/$(PIP) install -e ".[dev]"
	@echo "$(GREEN)[setup]$(NC) ✓ Ambiente pronto. Ative com: source $(VENV)/bin/activate"

.PHONY: setup-hooks
setup-hooks: ## Instala pre-commit hooks
	@echo "$(GREEN)[hooks]$(NC) Instalando pre-commit hooks..."
	$(VENV)/bin/pre-commit install --hook-type pre-commit --hook-type commit-msg
	@echo "$(GREEN)[hooks]$(NC) ✓ Hooks instalados"

.PHONY: setup-env-file
setup-env-file: ## Cria arquivo .env a partir do .env.example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)[env]$(NC) ✓ Arquivo .env criado. Edite conforme necessário."; \
	else \
		echo "$(YELLOW)[env]$(NC) Arquivo .env já existe. Nada foi alterado."; \
	fi

# ═══════════════════════════════════════════════════════════════════════════
# Docker — ambiente de desenvolvimento
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: dev-up
dev-up: ## Sobe o ambiente Docker (API + Postgres + Redis)
	@echo "$(GREEN)[docker]$(NC) Iniciando serviços..."
	$(COMPOSE) up -d --build api postgres redis
	@echo "$(GREEN)[docker]$(NC) Aguardando serviços ficarem saudáveis..."
	@sleep 3
	$(COMPOSE) ps
	@echo "$(GREEN)[docker]$(NC) ✓ API:        http://localhost:8000"
	@echo "$(GREEN)[docker]$(NC)   Docs:       http://localhost:8000/docs"
	@echo "$(GREEN)[docker]$(NC)   Postgres:   localhost:5432"
	@echo "$(GREEN)[docker]$(NC)   Redis:      localhost:6379"

.PHONY: dev-down
dev-down: ## Para todos os serviços Docker
	@echo "$(GREEN)[docker]$(NC) Parando serviços..."
	$(COMPOSE) down
	@echo "$(GREEN)[docker]$(NC) ✓ Serviços parados"

.PHONY: dev-restart
dev-restart: dev-down dev-up ## Reinicia o ambiente Docker

.PHONY: dev-logs
dev-logs: ## Exibe logs de todos os serviços
	$(COMPOSE) logs -f

.PHONY: dev-logs-api
dev-logs-api: ## Exibe logs apenas da API
	$(COMPOSE) logs -f api

.PHONY: dev-shell
dev-shell: ## Abre shell dentro do container da API
	$(COMPOSE) exec api /bin/bash

.PHONY: dev-status
dev-status: ## Status dos serviços Docker
	$(COMPOSE) ps
	@echo ""
	@echo "$(CYAN)Health checks:$(NC)"
	@$(COMPOSE) ps --format json 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    s = json.loads(line)
    name = s.get('Name', '?')
    status = s.get('State', '?')
    health = s.get('Health', 'N/A')
    print(f'  {name:30s} → {status} ({health})')
" 2>/dev/null || echo "  (docker compose ps não retornou dados)"

.PHONY: dev-clean
dev-clean: ## Remove containers, volumes e redes Docker
	@echo "$(RED)[docker]$(NC) Removendo containers, volumes e redes..."
	$(COMPOSE) down -v --remove-orphans
	@echo "$(GREEN)[docker]$(NC) ✓ Ambiente Docker limpo"

# ═══════════════════════════════════════════════════════════════════════════
# Testes
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: test
test: ## Executa todos os testes (exceto slow)
	$(VENV)/bin/$(PYTEST) $(TEST_DIR) -v

.PHONY: test-all
test-all: ## Executa todos os testes, inclusive os lentos
	$(VENV)/bin/$(PYTEST) $(TEST_DIR) -v --run-slow

.PHONY: test-cov
test-cov: ## Executa testes com relatório de cobertura
	$(VENV)/bin/$(PYTEST) $(TEST_DIR) -v \
		--cov=$(SRC_DIR)/intensicare \
		--cov-report=html \
		--cov-report=term-missing
	@echo "$(GREEN)[test]$(NC) ✓ Relatório HTML: htmlcov/index.html"

.PHONY: test-docker
test-docker: ## Executa testes no container Docker
	$(COMPOSE) --profile testing run --rm tests

.PHONY: test-watch
test-watch: ## Executa testes com re-execução em mudanças (requer ptw)
	$(VENV)/bin/ptw -- $(TEST_DIR) -v

# ═══════════════════════════════════════════════════════════════════════════
# Linting & Formatação
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: lint
lint: lint-ruff lint-mypy ## Executa todos os linters

.PHONY: lint-ruff
lint-ruff: ## Ruff: linter + verificação de formatação
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

.PHONY: lint-ruff-fix
lint-ruff-fix: ## Ruff: corrige problemas automaticamente
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)

.PHONY: format
format: ## Formata código com Ruff
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)[format]$(NC) ✓ Código formatado"

.PHONY: lint-mypy
lint-mypy: ## Verifica tipagem estática com mypy
	$(MYPY) $(SRC_DIR)/intensicare

.PHONY: lint-all
lint-all: format lint ## Formata e depois verifica tudo

# ═══════════════════════════════════════════════════════════════════════════
# Banco de Dados (Alembic)
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: db-migrate
db-migrate: ## Aplica migrações pendentes
	$(ALEMBIC) upgrade head

.PHONY: db-rollback
db-rollback: ## Reverte a última migração
	$(ALEMBIC) downgrade -1

.PHONY: db-revision
db-revision: ## Cria nova migração automática (ex: make db-revision msg='add_patients_table')
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

.PHONY: db-reset
db-reset: ## Reseta o banco de dados (drop + recreate + migrate)
	@echo "$(RED)[db]$(NC) Resetando banco de dados..."
	$(ALEMBIC) downgrade base
	$(ALEMBIC) upgrade head
	@echo "$(GREEN)[db]$(NC) ✓ Banco resetado"

.PHONY: db-shell
db-shell: ## Abre psql no banco de dados (via Docker)
	$(COMPOSE) exec postgres psql -U intensicare -d intensicare

# ═══════════════════════════════════════════════════════════════════════════
# Segurança
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: security-scan
security-scan: ## Varredura de segurança com bandit + pip-audit
	@echo "$(GREEN)[security]$(NC) Executando bandit..."
	$(VENV)/bin/bandit -r $(SRC_DIR) -c pyproject.toml || true
	@echo ""
	@echo "$(GREEN)[security]$(NC) Verificando dependências com pip-audit..."
	$(VENV)/bin/pip-audit || true

.PHONY: check
check: lint test ## Executa lint + testes (use antes de commitar)

# ═══════════════════════════════════════════════════════════════════════════
# Build & Release
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: build
build: ## Constrói imagem Docker de produção
	$(COMPOSE) build api

.PHONY: build-prod
build-prod: ## Constrói imagem Docker otimizada para produção
	$(DOCKER) build --target production -t intensicare-api:latest .

.PHONY: clean
clean: ## Remove arquivos gerados (cache, build, .pyc)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ coverage.xml .coverage dist/ build/ 2>/dev/null || true
	@echo "$(GREEN)[clean]$(NC) ✓ Arquivos temporários removidos"

.PHONY: clean-all
clean-all: clean dev-clean ## Limpa tudo (arquivos locais + containers/volumes Docker)
	rm -rf $(VENV)
	@echo "$(GREEN)[clean-all]$(NC) ✓ Virtualenv e ambiente Docker removidos"
