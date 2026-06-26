# PROJECT STATUS — Intensicare

**Versão:** `0.1.0-alpha`
**Data:** 26 de junho de 2026
**Ambiente:** Desenvolvimento / MVP

---

## 🎯 Visão Geral

O Intensicare é uma plataforma de suporte à decisão clínica para UTIs que realiza:

1. **Ingestão** de sinais vitais via API REST e HL7 v2 (MLLP)
2. **Cálculo** de scores clínicos: MEWS, NEWS2, SOFA e qSOFA
3. **Geração** de alertas baseados em thresholds configuráveis
4. **Exibição** em dashboard clínico (React) com grid de leitos e detalhes do paciente
5. **Broadcast** de alertas em tempo real via WebSocket

---

## ✅ O que funciona (MVP)

### Backend (Python/FastAPI)

| Componente | Status | Arquivo principal |
|-----------|:------:|-------------------|
| API FastAPI com lifespan | ✅ | `src/intensicare/main.py` |
| Configuração centralizada (pydantic-settings) | ✅ | `src/intensicare/config.py` |
| Engine SQLAlchemy async + session dependency | ✅ | `src/intensicare/core/database.py` |
| Redis client (lazy init) | ✅ | `src/intensicare/core/redis.py` |
| WebSocket Manager (connect/subscribe/broadcast) | ✅ | `src/intensicare/core/websocket.py` |
| JWT authentication (login/register/logout) | ✅ | `src/intensicare/auth/` |
| POST /api/v1/vitals — ingestão de sinais vitais | ✅ | `src/intensicare/api/vitals.py` |
| GET /api/v1/patients/{mpi_id}/status | ✅ | `src/intensicare/api/patients.py` |
| GET /api/v1/patients/{mpi_id}/detail | ✅ | `src/intensicare/api/v1/dashboard.py` |
| GET /api/v1/dashboard — grid de leitos | ✅ | `src/intensicare/api/v1/dashboard.py` |
| GET /api/v1/alerts — listagem de alertas | ✅ | `src/intensicare/api/v1/alerts.py` |
| POST /api/v1/alerts/{id}/acknowledge | ✅ | `src/intensicare/api/v1/alerts.py` |
| GET /api/v1/alerts/{id}/trace | ✅ | `src/intensicare/api/v1/alerts.py` |
| CRUD /api/v1/thresholds (admin-only) | ✅ | `src/intensicare/api/thresholds.py` |
| MEWS scoring engine (5 parâmetros, determinístico) | ✅ | `src/intensicare/services/mews.py` |
| NEWS2 scoring engine (7 parâmetros, escala 1 e 2) | ✅ | `src/intensicare/services/news2.py` |
| SOFA scoring engine (6 sistemas orgânicos) | ✅ | `src/intensicare/services/sofa.py` |
| qSOFA scoring engine (3 critérios binários) | ✅ | `src/intensicare/services/qsofa.py` |
| Alert engine (threshold check + Redis rate limiting + cooldown) | ✅ | `src/intensicare/services/alert_engine.py` |
| Idempotência de ingestão (X-Idempotency-Key) | ✅ | `src/intensicare/services/vitals.py` |
| MLLP Listener (servidor TCP, HL7 v2 → JSON) | ✅ | `src/intensicare/mllp_listener.py` |
| Versionamento de algoritmos (algorithm_version) | ✅ | Em todos os scores |
| Health check (/health) | ✅ | `src/intensicare/main.py` |

### Frontend (React/TypeScript/Vite)

| Componente | Status |
|-----------|:------:|
| Dashboard de leitos (BedGrid) | ✅ |
| Card de leito com MEWS/NEWS2/alertas (BedCard) | ✅ |
| Detalhes do paciente (PatientDetail) | ✅ |
| Histórico de sinais vitais (VitalsChart) | ✅ |
| Histórico de scores (ScoreTrendChart) | ✅ |
| Painel de alertas (AlertPanel) | ✅ |
| Login (LoginForm) | ✅ |
| Autenticação via JWT (useAuth hook) | ✅ |
| Cliente HTTP com interceptors (api/client) | ✅ |

### Infraestrutura

| Componente | Status |
|-----------|:------:|
| Docker Compose (API + DB + Redis + MLLP + Frontend) | ✅ |
| Dockerfile multi-estágio (dev + prod) | ✅ |
| Migrações Alembic (3 migrações) | ✅ |
| Modelo de dados (6 tabelas SQLAlchemy) | ✅ |
| Testes (12 arquivos, cobrindo todos os componentes) | ✅ |
| Makefile (25+ comandos) | ✅ |
| CI/CD (GitHub Actions, 7 jobs) | ✅ |
| Ruff (linter + formatter) | ✅ |
| MyPy (strict mode) | ✅ |

---

## 🟡 O que está pendente (Fase 2)

| Item | Prioridade |
|------|:----------:|
| **audit_trail imutável** (invariante #1) | 🔴 Crítica |
| Criptografia em repouso (pgcrypto para PHI) | 🔴 Crítica |
| Integração com HAPI FHIR (AMH Data Platform) | 🟠 Alta |
| ARQ task queue para notificações assíncronas | 🟠 Alta |
| Reverse proxy Caddy + TLS | 🟠 Alta |
| Prometheus metrics (/metrics) | 🟡 Média |
| Grafana dashboards | 🟡 Média |
| Web Push notifications (mobile) | 🟢 Baixa |
| Modelo preditivo de sepse (ML) | 🟢 Baixa (Fase 4) |

---

## 🏗️ Arquitetura Atual

```
┌─────────────────────────────────────────────────────────────────┐
│                     FONTES DE DADOS                               │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────────────┐  │
│  │Monitores │   │ HL7 v2 MLLP  │   │ AMH Data Platform       │  │
│  │Philips/GE│   │ TCP:2575     │   │ (Gold Layer / MPI)      │  │
│  └────┬─────┘   └──────┬───────┘   └───────────┬─────────────┘  │
└───────┼────────────────┼───────────────────────┼─────────────────┘
        │                │                       │
        ▼                ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INTENSICARE API (FastAPI)                      │
│                                                                   │
│  ┌──────────┐   ┌───────────────┐   ┌────────────────────────┐  │
│  │ REST API │   │ MLLP Listener │   │ WebSocket (/ws)        │  │
│  │ :8000    │   │    :2575      │   │ (real-time alerts)     │  │
│  └────┬─────┘   └──────┬────────┘   └───────────┬────────────┘  │
│       │                │                         │                │
│  ┌────▼────────────────▼─────────────────────────▼────────────┐  │
│  │                   SERVICES LAYER                            │  │
│  │  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐ │  │
│  │  │ Vitals   │ │ Scoring   │ │ Alert    │ │ Dashboard    │ │  │
│  │  │ Ingestion│ │ Engines   │ │ Engine   │ │ Aggregation  │ │  │
│  │  └──────────┘ │           │ │          │ │              │ │  │
│  │               │ MEWS      │ │ Threshold│ │ Bed Grid     │ │  │
│  │               │ NEWS2     │ │ RL Redis │ │ Patient      │ │  │
│  │               │ SOFA      │ │ Cooldown │ │ Detail       │ │  │
│  │               │ qSOFA     │ │          │ │              │ │  │
│  │               └───────────┘ └──────────┘ └──────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                   DATA LAYER                                 │  │
│  │  ┌─────────────────────────┐ ┌─────────────────────────────┐ │  │
│  │  │ PostgreSQL 16           │ │ Redis 7                     │ │  │
│  │  │ + TimescaleDB 2.x       │ │ cache / rate limiting       │ │  │
│  │  │                         │ │ pub/sub                     │ │  │
│  │  │ Tab*** │Tabelas:                 │ │                             │ │  │
│  │  │  vital_sign (hypertable) │ │                             │ │  │
│  │  │  clinical_score          │ │                             │ │  │
│  │  │  alert (hypertable)      │ │                             │ │  │
│  │  │  threshold_config        │ │                             │ │  │
│  │  │  patient_cache           │ │                             │ │  │
│  │  │  users                   │ │                             │ │  │
│  │  └─────────────────────────┘ └─────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FRONTEND (React + Vite + TypeScript)             │
│  ┌────────────┐ ┌───────────────┐ ┌──────────────────────────┐  │
│  │ BedGrid    │ │ PatientDetail │ │ AlertPanel               │  │
│  │ (grid de   │ │ (detalhes com │ │ (alertas ativos          │  │
│  │  leitos)   │ │  gráficos)    │ │  com acknowledge)        │  │
│  └────────────┘ └───────────────┘ └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Modelo de Dados

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   VitalSign     │────▶│  ClinicalScore   │────▶│     Alert       │
│                 │     │                  │     │                 │
│ id (PK)         │     │ id (PK)          │     │ id (PK)         │
│ mpi_id          │     │ mpi_id           │     │ mpi_id          │
│ recorded_at     │     │ score_type       │     │ score_id (FK)   │
│ heart_rate      │     │ score_value      │     │ severity        │
│ systolic_bp     │     │ algorithm_version│     │ status          │
│ diastolic_bp    │     │ calculated_at    │     │ title           │
│ temperature     │     │ vital_sign_id(FK)│     │ body            │
│ spo2            │     │ components(JSONB)│     │ created_at      │
│ respiratory_rate│     │ trend            │     │ acknowledged_at │
│ avpu            │     │ delta_from_prev  │     │ acknowledged_by │
│ supplemental_o2 │     └──────────────────┘     │ resolved_at     │
│ source_system   │                              │ resolution      │
│ ingested_at     │     ┌──────────────────┐     └─────────────────┘
│                 │     │ ThresholdConfig  │
│ [lab fields:    │     │                  │     ┌─────────────────┐
│  pao2_fio2,     │     │ id (PK)          │     │  PatientCache   │
│  platelets,     │     │ tenant_id        │     │                 │
│  bilirubin,     │     │ unit             │     │ mpi_id (PK)     │
│  map_value,     │     │ score_type       │     │ tenant_id       │
│  vasopressor,   │     │ watch_threshold  │     │ display_name    │
│  gcs,           │     │ urgent_threshold │     │ bed_id          │
│  creatinine,    │     │ critical_thrshld │     │ unit            │
│  urine_output]  │     │ rate_limit       │     │ is_active       │
└─────────────────┘     │ cooldown_min     │     └─────────────────┘
                        └──────────────────┘
                        ┌─────────────────┐
                        │      User       │
                        │ id (PK)         │
                        │ username (UQ)   │
                        │ email (UQ)      │
                        │ hashed_password │
                        │ is_admin        │
                        │ is_active       │
                        └─────────────────┘
```

---

## 🚀 Como rodar

### Requisitos

- Docker e Docker Compose v2+
- Python 3.12+ (para desenvolvimento local)

### Ambiente Docker (recomendado)

```bash
cd intensicare

# Subir todos os serviços
docker compose up -d

# Verificar saúde
curl http://localhost:8000/health

# Acessar Swagger
open http://localhost:8000/docs

# Frontend
open http://localhost:3000

# Logs
docker compose logs -f api
```

### Desenvolvimento local

```bash
# Setup
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Subir dependências (DB + Redis)
docker compose up -d postgres redis

# Migrar banco
alembic upgrade head

# Rodar API
uvicorn intensicare.main:app --reload --reload-dir src

# Testes
pytest tests/ -v
```

### Ingestão de teste

```bash
# Enviar sinais vitais
curl -X POST http://localhost:8000/api/v1/vitals \
  -H "Content-Type: application/json" \
  -d '{
    "mpi_id": "MPI-00012345",
    "recorded_at": "2026-06-26T10:00:00Z",
    "heart_rate": 88,
    "systolic_bp": 125,
    "temperature": 37.0,
    "spo2": 97,
    "respiratory_rate": 16,
    "avpu": "A"
  }'

# Consultar status
curl http://localhost:8000/api/v1/patients/MPI-00012345/status

# Dashboard
curl http://localhost:8000/api/v1/dashboard
```

---

## 📊 Cobertura de Testes

| Módulo | Testes | Arquivo |
|--------|--------|---------|
| MEWS engine | Unitários de scoring | `tests/test_mews.py` |
| NEWS2 engine | 7 parâmetros + risk categories | `tests/test_news2.py` |
| SOFA engine | 6 sistemas orgânicos + mortality risk | `tests/test_sofa.py` |
| qSOFA engine | 3 critérios + high risk | `tests/test_qsofa.py` |
| Vitals API | Ingestão, idempotência, validação | `tests/test_vitals.py` |
| Auth API | Login, register, JWT | `tests/test_auth.py` |
| Alerts API | List, acknowledge, trace | `tests/test_alerts.py` |
| Alert Engine | Thresholds, rate limit, cooldown | `tests/test_alert_engine.py` |
| Thresholds API | CRUD admin-only | `tests/test_thresholds.py` |
| WebSocket | Connect, subscribe, broadcast | `tests/test_websocket.py` |
| MLLP Listener | Framing, parse HL7 | `tests/test_mllp_listener.py` |
| Main API | Health check | `tests/test_main.py` |

---

## 🔒 Status Regulatório

| Requisito | Status |
|-----------|--------|
| ANVISA SaMD Classification | 🔴 Pendente — consultoria a contratar (Q3 2026) |
| LGPD RIPD | 🔴 Pendente — DPO deve elaborar (Q3 2026) |
| SBIS Certification | 🟡 Plano elaborado — execução Q4 2026 |
| Pentest externo | 🔴 Pendente — Q4 2026 |
| audit_trail imutável | 🔴 Pendente — invariante #1 antes de dados reais |
| Criptografia PHI (pgcrypto) | 🔴 Pendente |
| Treinamento equipe clínica | 🔴 Pendente |

> Detalhes completos: [`docs/review-queue.md`](docs/review-queue.md)

---

## 📁 Estrutura de Diretórios

```
intensicare/
├── README.md
├── PROJECT_STATUS.md              ← Este arquivo
├── HANDOFF.yaml                   ← Bloqueios e itens concluídos
├── Dockerfile                     ← Multi-estágio (dev + prod)
├── docker-compose.yml             ← API + DB + Redis + MLLP + Frontend
├── Makefile                       ← 25+ alvos
├── pyproject.toml                 ← Build + tool config
├── alembic.ini + alembic/         ← Migrações de banco
├── .github/workflows/ci.yml       ← CI/CD pipeline
├── src/intensicare/               ← Código fonte
│   ├── main.py                    ← FastAPI app
│   ├── config.py                  ← Settings
│   ├── auth.py / auth/            ← Auth dependencies + JWT
│   ├── mllp_listener.py           ← HL7 v2 MLLP server
│   ├── api/                       ← REST endpoints
│   ├── core/                      ← Database, Redis, WebSocket
│   ├── models/                    ← SQLAlchemy models (6)
│   ├── schemas/                   ← Pydantic schemas
│   └── services/                  ← Business logic (8 services)
├── tests/                         ← 12 arquivos de teste
├── frontend/                      ← React dashboard
│   └── src/
│       ├── components/            ← BedGrid, PatientDetail, etc.
│       ├── hooks/                 ← useAuth
│       ├── api/                   ← HTTP client
│       └── types/                 ← TypeScript types
└── docs/                          ← Documentação
    ├── api/overview.md            ← API docs (endpoints + exemplos)
    ├── product/                   ← Visão, personas
    ├── architecture/adr/          ← ADRs
    ├── data/model.md              ← Modelo de dados
    ├── implementation-plan.md     ← Roadmap completo
    └── review-queue.md            ← Fila regulatória
```

---

**Última atualização:** 26 de junho de 2026
**Próximo marco:** Fase 2 — Interoperabilidade & Expansão (Semanas 9-14)
