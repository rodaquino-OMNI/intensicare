# Plano de Implementação — Intensicare

**Status:** Plano Diretor  
**Versão:** 1.0  
**Data:** 26 de junho de 2026  
**Autor:** Parreira (Hermes DevOps Orchestrator), com contribuições dos agentes especialistas  
**Stakeholders:** CTO Office AMH, Time de Engenharia

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Product Requirements Document (PRD)](#2-product-requirements-document)
3. [Arquitetura Validada](#3-arquitetura-validada)
4. [Fundação DevOps](#4-fundação-devops)
5. [Compliance Baseline](#5-compliance-baseline)
6. [Roadmap Faseado](#6-roadmap-faseado)
7. [Governança e Métricas](#7-governança-e-métricas)
8. [Apêndices](#8-apêndices)

---

## 1. Visão Geral

### 1.1 O que é o Intensicare (agora)

O Intensicare é uma plataforma de suporte à decisão clínica para UTIs que calcula scores de deterioração (MEWS, SOFA, qSOFA, NEWS2) a partir de sinais vitais e gera alertas para equipes clínicas. Opera como **consumidor especializado da AMH Data Platform**, não como plataforma independente.

### 1.2 Três pilares da análise

Este plano consolida o trabalho de 4 agentes especialistas:

| Analista | Escopo | Documento |
|----------|--------|-----------|
| **Parreira** (orquestrador) | Análise completa do repositório, integração AMH Data Platform | [`technical-review-2026.md`](analysis/technical-review-2026.md) |
| **Arquiteto de Sistemas** | Validação da stack MVP, invariantes, riscos | [`CRITICA_MVP.md`](../../CRITICA_MVP.md) |
| **Compliance Regulatório** | ANVISA SaMD, LGPD, CFM, ANS/TISS, certificações | `intensicare-regulatory-analysis.md` |
| **CI/CD & DevOps** | Estrutura de projeto, Docker, CI/CD, ferramentas | `pyproject.toml`, `docker-compose.yml`, `Makefile`, etc. |

### 1.3 Repositório-alvo

```
intensicare/
├── README.md                         # Atualizado: disclaimer + links
├── LICENSE                            # AGPLv3
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── .env.example
├── .secrets.baseline
├── pyproject.toml                    # Python 3.12+, FastAPI, SQLAlchemy, ruff, mypy
├── docker-compose.yml                # API + PostgreSQL/TimescaleDB + Redis
├── Dockerfile                        # Multi-estágio (dev + prod)
├── Makefile                          # +25 comandos
├── alembic.ini + alembic/           # Migrações async
├── .github/workflows/ci.yml         # 7 jobs de CI/CD
├── src/intensicare/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app com lifespan + health check
│   ├── config.py                    # pydantic-settings
│   ├── api/                         # Rotas REST
│   ├── core/
│   │   └── database.py              # SQLAlchemy async + dependency
│   ├── models/                      # SQLAlchemy models
│   └── services/                    # Scoring, alerting, HL7 parser
├── tests/
│   ├── conftest.py                  # Fixtures: engine, client HTTP async
│   └── test_main.py                 # Health check test
└── docs/
    ├── analysis/
    │   └── technical-review-2026.md
    ├── product/
    │   ├── vision.md
    │   └── personas.md
    ├── architecture/
    │   └── adr/
    │       └── ADR-001-amh-data-platform-consumer.md
    ├── data/
    │   └── model.md
    └── implementation-plan.md       # ← Este documento
```

---

## 2. Product Requirements Document (PRD)

### 2.1 Personas

| Persona | Nome | Prioridade |
|---------|------|:----------:|
| Médico Intensivista | Dr. Carlos | P0 |
| Enfermeiro de UTI | Enf. Ana | P0 |
| Coordenador de UTI | Dra. Fernanda | P1 |
| Equipe de Resposta Rápida | Dr. Rafael | P1 |

> Detalhamento completo: [`docs/product/personas.md`](product/personas.md)

### 2.2 User Stories Priorizadas (MoSCoW)

#### MUST HAVE (MVP — Fase 1)

| ID | User Story | Persona | Critério de Aceitação |
|----|-----------|---------|----------------------|
| **US-01** | Como enfermeiro, quero que sinais vitais sejam ingeridos automaticamente via HL7 v2 para eliminar cálculo manual de scores | Ana | Mensagens HL7 ORU-R01 com vitais são parseadas e armazenadas em <5s após recebimento |
| **US-02** | Como intensivista, quero ver o score MEWS de cada paciente calculado em tempo real | Carlos | MEWS disponível em <30s após ingestão dos vitais; tela mostra score + tendência |
| **US-03** | Como intensivista, quero receber alertas quando o MEWS ≥ 5 (urgente) ou ≥ 7 (crítico) | Carlos | Alerta gerado em <5s após score exceder threshold; notificação no dashboard |
| **US-04** | Como enfermeiro, quero visualizar quais parâmetros contribuíram para o score elevado | Ana | Tela de detalhes do score mostra componentes individuais (FR, SpO2, PA, etc.) |
| **US-05** | Como intensivista, quero reconhecer (acknowledge) um alerta para sinalizar que estou tratando | Carlos | Botão "Reconhecer" no alerta; registra timestamp + usuário |
| **US-06** | Como coordenador, quero ver o painel de leitos da UTI com scores e status de alertas | Fernanda | Grid de leitos mostrando nome, score, status do alerta, tempo desde último vital |

#### SHOULD HAVE (Fase 2)

| ID | User Story | Persona |
|----|-----------|---------|
| **US-07** | Como intensivista, quero scores SOFA e NEWS2 além do MEWS | Carlos |
| **US-08** | Como RRT, quero receber alertas críticos no celular | Rafael |
| **US-09** | Como coordenador, quero dashboard de métricas (tempo de resposta, taxa de alertas) | Fernanda |
| **US-10** | Como intensivista, quero ver tendência de scores nas últimas 24h em gráfico | Carlos |

#### COULD HAVE (Fase 3)

| ID | User Story | Persona |
|----|-----------|---------|
| **US-11** | Como intensivista, quero sugestões baseadas em evidência para scores elevados | Carlos |
| **US-12** | Como enfermeiro, quero documentar ação tomada após alerta em 1 clique | Ana |

#### WON'T HAVE (agora)

| ID | Item | Justificativa |
|----|------|---------------|
| — | Modelo preditivo de sepse (ML) | Modelo não validado clinicamente; requer estudo formal |
| — | SMART-on-FHIR apps | Requer Keycloak + fluxo OAuth2 complexo; postergar |
| — | App mobile nativo (React Native) | Web app responsivo supre 80% da necessidade |

### 2.3 Funcionalidades do MVP

| Funcionalidade | Status | Stack |
|---------------|--------|-------|
| **Ingestão HL7 v2 (ORU-R01)** | MUST | MLLP Listener + `python-hl7` |
| **Leitura de dados do Gold layer (AMH DP)** | MUST | Amazon Athena |
| **Cálculo MEWS** | MUST | Python puro (função determinística) |
| **Cálculo NEWS2** | MUST | Python puro |
| **Alertas (dashboard)** | MUST | FastAPI + Redis Pub/Sub |
| **Dashboard de leitos** | MUST | React/Next.js (responsivo) |
| **Autenticação** | MUST | JWT simples (`python-jose`) |
| **Cálculo SOFA** | FASE 2 | Python + agregações temporais |
| **Cálculo qSOFA** | FASE 2 | Python puro |
| **Alertas mobile** | FASE 2 | Web push notifications |
| **Gravação de scores no Gold layer** | FASE 2 | Athena INSERT ou Spark job |

---

## 3. Arquitetura Validada

### 3.1 Stack Final para MVP

```
┌──────────────────────────────────────────────────────────────────┐
│                   AMH DATA PLATFORM (já existente)               │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Gold Layer│  │    MPI     │  │HAPI FHIR │  │AMP + Grafana │   │
│  │(Iceberg) │  │ (patients) │  │  (R4)    │  │(observability)│   │
│  └────┬─────┘  └───────────┘  └────┬─────┘  └──────────────┘   │
└───────┼─────────────────────────────┼────────────────────────────┘
        │ Athena queries              │ FHIR REST
        ▼                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     INTENSICARE (MVP)                             │
│                                                                    │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │MLLP Listener│──▶│  FastAPI     │   │   Dashboard (React)  │  │
│  │(HL7→JSON)   │   │  Monolith    │   │   Mobile-first       │  │
│  └─────────────┘   │              │   └──────────────────────┘  │
│                    │ ┌──────────┐ │                               │
│                    │ │Vitals    │ │   ┌──────────────────────┐  │
│                    │ │Scoring   │ │   │  Reverse Proxy       │  │
│                    │ │Alerting  │ │   │  (Caddy/Nginx + TLS) │  │
│                    │ └──────────┘ │   └──────────────────────┘  │
│                    └──┬────┬────┬─┘                               │
│                       │    │    │                                  │
│  ┌────────────────────▼┐ ┌─▼────▼──┐ ┌────────────────────────┐  │
│  │ PostgreSQL 16       │ │ Redis 7 │ │ ARQ Worker              │  │
│  │ + TimescaleDB 2.x   │ │         │ │ (async task queue)      │  │
│  │ + pgcrypto          │ │         │ │                         │  │
│  └─────────────────────┘ └─────────┘ └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Componentes e Decisões

| Componente | Decisão | Justificativa |
|-----------|---------|---------------|
| **Linguagem** | Python 3.12+ | Ecossistema HL7 (`hl7apy`), científico (scipy), mão de obra BR |
| **Framework** | FastAPI | Async nativo, OpenAPI auto, WebSocket, performance |
| **Banco** | PostgreSQL 16 + TimescaleDB 2.18 | Time-series + relacional + JSONB para HL7 |
| **Cache/Queue** | Redis 7 | Cache de scores, rate limiting, pub/sub, task queue |
| **Task Queue** | ARQ | Async sobre Redis, retry nativo, simples |
| **Reverse Proxy** | Caddy | TLS automático, simples, performance |
| **Container** | Docker Compose | Suficiente para 1-3 UTIs (30-90 leitos) |

### 3.3 Invariantes Arquiteturais Não-Negociáveis

Estes **DEVEM** ser implementados antes do primeiro paciente real:

| # | Invariante | Implementação | Riscos se ausente |
|---|-----------|---------------|-------------------|
| **1** | **Trilha de auditoria imutável** | Tabela PostgreSQL `audit_trail` append-only + trigger anti-mutação | Ilegal (LGPD + CFM 1.821/07) |
| **2** | **Idempotência de ingestão** | `MSH-10` como chave única; `INSERT ON CONFLICT DO NOTHING` | Duplicação de dados clínicos, alertas falsos |
| **3** | **Versionamento de algoritmos** | Coluna `algorithm_version` em `clinical_scores` | Impossibilidade de auditar scores históricos |
| **4** | **Criptografia em repouso** | `pgcrypto` para PHI (nome, CPF, CNS) | Violação LGPD Art. 46 |
| **5** | **Health check + Dead man's switch** | `/api/v1/health` + script externo de monitoramento | Risco de paciente: sistema cai e ninguém sabe |
| **6** | **Retry com backoff** | ARQ retry nativo para notificações (SMS, push) | Alertas perdidos |

### 3.4 Gap: MLLP Listener

**Problema:** FastAPI não suporta MLLP (protocolo de framing binário do HL7 v2 sobre TCP).

**Solução MVP:**
- Container separado (`mllp-listener`) no mesmo Docker Compose
- Implementação: Python `asyncio` + `hl7apy`
- Escuta na porta TCP 2575, parseia HL7 v2 → JSON, faz POST para `http://api:8000/api/v1/vitals`
- Alternativa se hospital tiver barramento (Mirth/InterSystems): consumir webhook REST

```python
# Exemplo conceitual do MLLP Listener
import asyncio
import hl7
import httpx

async def handle_mllp(reader, writer):
    data = b""
    while True:
        chunk = await reader.read(4096)
        if not chunk:
            break
        data += chunk
        if b"\x1c\x0d" in data:  # FS + CR = fim MLLP
            break
    
    message = data.strip(b"\x0b\x1c\x0d").decode("utf-8")
    parsed = hl7.parse(message)
    
    # Extrai segmentos relevantes (PID, OBR, OBX)
    vitals = extract_vitals(parsed)
    
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://api:8000/api/v1/vitals",
            json=vitals,
            headers={"X-Idempotency-Key": str(parsed.segment("MSH")[10])}
        )

async def main():
    server = await asyncio.start_server(handle_mllp, "0.0.0.0", 2575)
    await server.serve_forever()
```

---

## 4. Fundação DevOps

### 4.1 Stack de Desenvolvimento

| Ferramenta | Propósito |
|-----------|-----------|
| **hatchling** | Build system (PEP 517) |
| **Ruff** | Linter + formatter (substitui flake8, isort, black) |
| **MyPy** | Type checking (strict mode) |
| **Bandit** | Security scanning |
| **pytest** | Testes (unit + integration + async) |
| **Alembic** | Migrações de banco |
| **pre-commit** | Hooks de qualidade (8 hooks) |
| **Trivy** | Container vulnerability scanning (CI) |
| **Cosign** | Image signing (CI) |

### 4.2 Ambiente de Desenvolvimento

```bash
# Setup inicial (1 vez)
git clone git@github.com:rodaquino-OMNI/intensicare.git
cd intensicare
make setup              # virtualenv + dependências + pre-commit hooks
cp .env.example .env    # Editar .env

# Desenvolvimento diário
make dev-up             # Sobe API + Postgres + Redis
make dev-logs-api       # Logs da API
make check              # lint + test (antes de commitar)
make db-revision msg='add_feature_x'  # Criar migração
make db-migrate         # Aplicar migrações

# Parar
make dev-down           # Para serviços
make clean-all          # Limpa tudo (containers + volumes + venv)
```

### 4.3 CI/CD Pipeline (GitHub Actions)

```
Push / PR → main, develop
    │
    ├── Job 1: Lint (ruff + mypy) ──────── 2 min
    ├── Job 2: Test (pytest 3.12 + 3.13) ─ 4 min
    ├── Job 3: Coverage (≥80% gate) ────── 2 min
    ├── Job 4: Security (bandit + trivy) ── 3 min
    │
    ├── [main only] Job 5: Build + Push ── 5 min
    ├── [main only] Job 6: Deploy Staging ─ 3 min
    └── [tag v*] Job 7: Release ─────────── 5 min
```

### 4.4 Comandos Makefile

| Comando | Descrição |
|---------|-----------|
| `make setup` | Cria venv + instala deps + pre-commit hooks |
| `make dev-up` | Sobe Docker: API + Postgres + Redis |
| `make dev-down` | Para serviços Docker |
| `make dev-logs` | Logs de todos os serviços |
| `make test` | pytest (exceto slow) |
| `make test-cov` | pytest com coverage HTML |
| `make lint` | ruff + mypy |
| `make format` | Formata código com ruff |
| `make check` | lint + test (use antes de commit) |
| `make db-revision msg='...'` | Cria migração Alembic |
| `make db-migrate` | Aplica migrações |
| `make db-reset` | Reseta banco (dev apenas) |
| `make security-scan` | bandit + pip-audit |
| `make build-prod` | Build Docker imagem produção |
| `make clean-all` | Remove tudo (containers + volumes + venv + cache) |

---

## 5. Compliance Baseline

### 5.1 Resumo Regulatório

| Dimensão | Conclusão | Ação |
|----------|-----------|------|
| **ANVISA SaMD** | Classe II (risco de Classe III) | Contratar consultoria antes do desenvolvimento; registrar antes da comercialização |
| **LGPD** | Dados de saúde = sensíveis | RIPD obrigatório; base legal: proteção da vida (Art. 11, II, "g"); criptografia obrigatória |
| **CFM** | Sem resolução específica para IA | Responsabilidade médica indelegável; transparência obrigatória em scores |
| **ANS/TISS** | FHIR R4 suficiente para interop clínica | TISS XML apenas se faturamento; delegar ao barramento hospitalar |
| **HIPAA** | **NÃO SE APLICA** | Erro no README — remover e substituir por LGPD |
| **Certificações** | SBIS (primária) + ISO 27001 (recomendada) + pentest anual | Incluir no roadmap pré-lançamento |

### 5.2 Ações Imediatas de Compliance

1. 🔴 **Corrigir README**: Remover "HIPAA" e "GDPR"; substituir por "LGPD" e "SBIS"
2. 🔴 **Contratar consultoria ANVISA**: Classificação SaMD antes de escrever código clínico
3. 🟠 **Elaborar RIPD**: Data Protection Impact Assessment para processamento de sinais vitais
4. 🟠 **Implementar auditoria**: Tabela `audit_trail` antes da primeira ingestão de dados reais

### 5.3 Roadmap Regulatório

| Fase | Marco Regulatório |
|------|-------------------|
| **Imediato** | Corrigir README; contratar consultoria ANVISA |
| **Desenvolvimento** | RIPD; segurança by design; documentar intended use |
| **Pré-lançamento** | Registro ANVISA; pentest externo; certificação SBIS; ISO 27001 |
| **Pós-lançamento** | Monitoramento contínuo ANVISA/ANPD/CFM; renovações |

---

## 6. Roadmap Faseado

### Fase 0: Fundação (Semanas 1-2)

**Objetivo:** Repositório profissional, documentação honesta, ambiente de desenvolvimento funcional.

| Task | Responsável | Artefato |
|------|-------------|----------|
| Atualizar README com disclaimer + links | Parreira | ✅ Feito |
| Adicionar LICENSE (AGPLv3) | Time | `LICENSE` |
| Estruturar diretórios `docs/` | Parreira | ✅ Feito |
| Criar PRD (vision + personas + user stories) | PM | ✅ Feito |
| Criar ADR-001 (AMH Data Platform integration) | Arquiteto | ✅ Feito |
| Setup Docker Compose funcional | DevOps | ✅ Feito (`docker-compose.yml`) |
| Setup CI/CD (GitHub Actions) | DevOps | ✅ Feito (`.github/workflows/ci.yml`) |
| Criar projeto Python (pyproject.toml + src/) | DevOps | ✅ Feito |
| Validar ambiente: `make dev-up` passa | Time | `curl localhost:8000/health → 200 OK` |

### Fase 1: MVP Core (Semanas 3-8)

**Objetivo:** Primeira versão funcional com MEWS + alertas para 1 UTI piloto.

| Sprint | Tasks | Entregável |
|--------|-------|------------|
| **Sprint 1** (Semana 3-4) | Modelo de dados (TimescaleDB hypertables) + migrações | `make db-migrate` cria tabelas |
| | Implementar `POST /api/v1/vitals` (ingestão de vitais) | Curl envia vitals → 201 Created |
| | Implementar `GET /api/v1/patients/{id}` | Retorna paciente + scores |
| | Triggers de auditoria (`audit_trail`) | Toda ingestão gera registro imutável |
| **Sprint 2** (Semana 5-6) | Implementar scoring engine (MEWS + NEWS2) | Score calculado em <30s após vital |
| | Implementar alert engine (thresholds configuráveis) | Alerta disparado se MEWS ≥ 5 |
| | `POST /api/v1/alerts/{id}/acknowledge` | Alerta marcado como reconhecido |
| | Redis cache de scores recentes | Scores cacheados com TTL |
| **Sprint 3** (Semana 7-8) | Dashboard web (React): grid de leitos com scores | Visualização de 20 leitos com scores |
| | Dashboard web: detalhes do paciente + tendência | Gráfico de scores 24h |
| | Autenticação JWT simples | Login com token |
| | Testes de integração (pytest + testcontainers) | Cobertura ≥ 70% |
| | **Piloto interno com dados sintéticos** | Demo para time clínico |

### Fase 2: Interoperabilidade & Expansão (Semanas 9-14)

**Objetivo:** Integração hospitalar real, scores adicionais, mobile.

| Sprint | Tasks |
|--------|-------|
| **Sprint 4** (Semana 9-10) | MLLP Listener (HL7 v2 → JSON) |
| | Validar com tráfego HL7 real do hospital piloto (48h) |
| | Implementar SOFA + qSOFA scoring |
| **Sprint 5** (Semana 11-12) | Integração com HAPI FHIR (contexto clínico enriquecido) |
| | WebSocket para alertas em tempo real no dashboard |
| | Notificações push (Web Push API) |
| **Sprint 6** (Semana 13-14) | Gravar scores de volta ao Gold layer AMH Data Platform |
| | Prometheus metrics exporter (`/metrics`) |
| | Dashboard Grafana básico |
| | Testes de carga (30-90 leitos simulados) |

### Fase 3: Produção (Semanas 15-20)

**Objetivo:** Deploy em produção, segurança, DR.

| Sprint | Tasks |
|--------|-------|
| **Sprint 7** (Semana 15-16) | Deploy em ECS Fargate (alinhado stack AMH) |
| | IAM roles + KMS por tenant |
| | Testes de penetração (externos) |
| **Sprint 8** (Semana 17-18) | DR e backup alinhados à AMH Data Platform |
| | Documentação de operação (runbooks) |
| | Treinamento da equipe clínica |
| **Sprint 9** (Semana 19-20) | Piloto clínico com 1 UTI (Hospital AUSTA) |
| | Monitoramento 24/7 |
| | Coleta de feedback clínico |

### Fase 4: ML & Advanced (Semanas 21+)

- Modelo preditivo de sepse (treinamento em dados MIMIC-IV + dados locais)
- Inferência via Bedrock ou SageMaker
- Validação clínica formal
- Registro ANVISA (se SaMD Classe III)

---

## 7. Governança e Métricas

### 7.1 Code Review

- PR mínimo: 1 reviewer (2 para paths de produção)
- CI deve passar (lint + test + coverage)
- Conventional Commits obrigatório (enforced via pre-commit)
- CODEOWNERS definidos nos paths críticos

### 7.2 Métricas de Qualidade

| Métrica | Target MVP | Target Produção |
|---------|:----------:|:---------------:|
| Cobertura de testes | ≥ 70% | ≥ 85% |
| Complexidade ciclomática (ruff) | ≤ 10 | ≤ 10 |
| Type coverage (mypy) | ≥ 90% | 100% |
| Vulnerabilidades críticas (trivy) | 0 | 0 |
| Tempo de CI | < 10 min | < 15 min |

### 7.3 SLOs da Aplicação

| SLO | Target MVP | Target Produção |
|-----|:----------:|:---------------:|
| Disponibilidade API | 99% | 99,5% |
| Latência P95 ingestão vital | < 500ms | < 200ms |
| Latência P95 cálculo score | < 30s | < 5s |
| Latência P95 alerta | < 5s | < 2s |
| RPO banco operacional | 24h (backup diário) | 1h (WAL shipping) |
| RTO banco operacional | 4h | 1h |

---

## 8. Apêndices

### 8.1 Documentos de Referência

| Documento | Localização |
|-----------|-------------|
| Análise técnica completa | [`docs/analysis/technical-review-2026.md`](analysis/technical-review-2026.md) |
| Crítica arquitetural MVP | [`CRITICA_MVP.md`](../../CRITICA_MVP.md) |
| Análise regulatória | `ops-compliance-gate/references/intensicare-regulatory-analysis.md` |
| Visão do produto | [`docs/product/vision.md`](product/vision.md) |
| Personas | [`docs/product/personas.md`](product/personas.md) |
| ADR-001: Consumidor AMH DP | [`docs/architecture/adr/ADR-001-amh-data-platform-consumer.md`](architecture/adr/ADR-001-amh-data-platform-consumer.md) |
| Modelo de dados | [`docs/data/model.md`](data/model.md) |
| AMH Data Platform | [`Omni-Saude/amh-data-platform`](https://github.com/Omni-Saude/amh-data-platform) |

### 8.2 Stack Tecnológico (Resumo)

```
Aplicação:      Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic
Banco:          PostgreSQL 16 + TimescaleDB 2.18 + pgcrypto
Cache/Queue:    Redis 7 + ARQ
Proxy:          Caddy (TLS automático)
Container:      Docker Compose (dev), ECS Fargate (prod)
CI/CD:          GitHub Actions
Observabilidade: OpenTelemetry → AMP → Grafana (AMH DP)
Segurança:      KMS por tenant + IAM ABAC (AMH DP)
```

### 8.3 Riscos Identificados e Mitigações

| Risco | Prob. | Impacto | Mitigação |
|-------|:-----:|:-------:|-----------|
| Classificação ANVISA Classe III | Média | Alto | Contratar consultoria antes do código; documentar intended use como "suporte apenas" |
| Dificuldade de integração HL7 real | Alta | Médio | Validar com 48h de tráfego real do hospital piloto; ter fallback de entrada manual |
| Resistência clínica à adoção | Média | Alto | Envolver médico intensivista no design desde o dia 1; iterar com feedback |
| Latência da AMH Data Platform | Baixa | Médio | Monitorar freshness do Gold layer; se >30min, negociar streaming direto |
| Vazamento de dados de paciente | Baixa | Crítico | Criptografia em repouso + trânsito; auditoria; pentest; DPA com hospital |

---

*Plano compilado por Parreira com contribuições de 3 agentes especialistas (Arquitetura, Compliance Regulatório, CI/CD/DevOps).*

*Última atualização: 26 de junho de 2026.*
