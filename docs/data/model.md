# Data Model — Intensicare

Este documento descreve o modelo de dados operacional do Intensicare (PostgreSQL/TimescaleDB).
Dados analíticos residem no Gold layer da AMH Data Platform (Apache Iceberg).

---

## Diagrama de Entidades (Conceitual)

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│   Patient     │──1:N──│   VitalSign       │──1:N──│   Score      │
│               │       │                   │       │              │
│ mpi_id (FK→  │       │ patient_id (FK)   │       │ patient_id   │
│  MPI da AMH) │       │ timestamp          │       │ timestamp    │
│ tenant_id    │       │ heart_rate         │       │ score_type   │
└──────────────┘       │ systolic_bp        │       │ score_value  │
                       │ diastolic_bp       │       │ components   │
                       │ temperature        │       └──────┬───────┘
                       │ spo2               │            │
                       │ respiratory_rate   │            │ triggers
                       │ avpu               │            ▼
                       └──────────────────┘       ┌──────────────┐
                                                   │    Alert     │
                                                   │              │
                                                   │ patient_id   │
                                                   │ score_id     │
                                                   │ severity     │
                                                   │ status       │
                                                   │ acknowledged │
                                                   └──────────────┘
```

---

## Tabelas

### 1. `patient_cache`

Cache local de dados demográficos do paciente. Fonte primária: MPI da AMH Data Platform.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `mpi_id` | VARCHAR(64) | FK para `mpi.patients.master_patient_id` |
| `tenant_id` | VARCHAR(32) | Tenant AMH (ex: `austa_clinicas`) |
| `display_name` | VARCHAR(255) | Nome para exibição (hash se LGPD restrito) |
| `mrn` | VARCHAR(64) | Medical Record Number (local) |
| `gender` | VARCHAR(16) | Sexo |
| `birth_date` | DATE | Data de nascimento |
| `admission_dt` | TIMESTAMPTZ | Data/hora de admissão na UTI |
| `bed_id` | VARCHAR(32) | Identificador do leito |
| `unit` | VARCHAR(64) | Unidade (ex: `UTI-ADULTO`, `UTI-CORONARIANA`) |
| `synced_at` | TIMESTAMPTZ | Última sincronização com MPI |
| `is_active` | BOOLEAN | Paciente ainda internado |

### 2. `vital_sign`

Sinais vitais recebidos. Fonte primária: Gold layer da AMH Data Platform (via Athena query).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | BIGSERIAL | PK |
| `mpi_id` | VARCHAR(64) | FK para `patient_cache` |
| `recorded_at` | TIMESTAMPTZ | Momento da coleta do sinal vital |
| `heart_rate` | INT | Frequência cardíaca (bpm) |
| `systolic_bp` | INT | Pressão sistólica (mmHg) |
| `diastolic_bp` | INT | Pressão diastólica (mmHg) |
| `temperature` | DECIMAL(4,1) | Temperatura (°C) |
| `spo2` | INT | Saturação de O2 (%) |
| `respiratory_rate` | INT | Frequência respiratória (rpm) |
| `avpu` | VARCHAR(4) | Nível de consciência (A/V/P/U) |
| `supplemental_o2` | BOOLEAN | O2 suplementar |
| `source_system` | VARCHAR(32) | Sistema de origem (ex: `tasy`, `philips_monitor`) |
| `ingested_at` | TIMESTAMPTZ | Timestamp de ingestão no Intensicare |

> **Índice:** Hypertable do TimescaleDB em `recorded_at`, particionado por `mpi_id`.

### 3. `clinical_score`

Scores clínicos calculados pelo engine.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | BIGSERIAL | PK |
| `mpi_id` | VARCHAR(64) | FK para `patient_cache` |
| `score_type` | VARCHAR(16) | `MEWS`, `NEWS2`, `SOFA`, `qSOFA` |
| `score_value` | INT | Valor calculado do score |
| `calculated_at` | TIMESTAMPTZ | Momento do cálculo |
| `vital_sign_id` | BIGINT | FK para `vital_sign` que originou o cálculo |
| `components` | JSONB | Componentes do score (ex: `{"respiratory_rate": 2, "spo2": 1, ...}`) |
| `trend` | VARCHAR(16) | `increasing`, `decreasing`, `stable` vs score anterior |
| `delta_from_previous` | INT | Variação vs score anterior |

> **Índice:** Hypertable em `calculated_at`, particionado por `mpi_id`.

### 4. `alert`

Alertas gerados a partir de scores que excedem thresholds.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | BIGSERIAL | PK |
| `mpi_id` | VARCHAR(64) | FK para `patient_cache` |
| `score_id` | BIGINT | FK para `clinical_score` |
| `severity` | VARCHAR(16) | `watch`, `urgent`, `critical` |
| `status` | VARCHAR(16) | `active`, `acknowledged`, `resolved`, `expired` |
| `title` | VARCHAR(255) | Ex: "MEWS 6 — Deterioração Respiratória" |
| `body` | TEXT | Detalhes do alerta |
| `created_at` | TIMESTAMPTZ | Timestamp de criação |
| `acknowledged_at` | TIMESTAMPTZ | Quando foi reconhecido |
| `acknowledged_by` | VARCHAR(255) | Usuário que reconheceu |
| `resolved_at` | TIMESTAMPTZ | Quando foi resolvido |
| `resolution` | VARCHAR(32) | `true_positive`, `false_positive`, `intervention_done` |

### 5. `threshold_config`

Configuração de thresholds de alerta por tenant e unidade.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | PK |
| `tenant_id` | VARCHAR(32) | Tenant AMH |
| `unit` | VARCHAR(64) | Unidade (NULL = todas) |
| `score_type` | VARCHAR(16) | `MEWS`, `NEWS2`, `SOFA`, `qSOFA` |
| `watch_threshold` | INT | Threshold para alerta `watch` |
| `urgent_threshold` | INT | Threshold para alerta `urgent` |
| `critical_threshold` | INT | Threshold para alerta `critical` |
| `rate_limit_per_hour` | INT | Máximo de alertas por paciente por hora |
| `cooldown_minutes` | INT | Tempo mínimo entre alertas do mesmo tipo |
| `updated_at` | TIMESTAMPTZ | Última atualização |
| `updated_by` | VARCHAR(255) | Usuário que atualizou |

---

## Relação com a AMH Data Platform

| Dado | Onde reside | Direção |
|------|-------------|---------|
| Demografia do paciente | MPI (`mpi.patients`) → cache local `patient_cache` | Leitura |
| Sinais vitais | Gold layer → `vital_sign` | Leitura (via Athena) |
| Scores clínicos | `clinical_score` (local) → Gold `fact_patient_score` | Escrita periódica |
| Alertas | `alert` (local) → Gold `fact_alert` | Escrita periódica |
| Thresholds | `threshold_config` (local) | Local apenas |

---

## TimescaleDB Hypertables

```sql
-- Sinais vitais: hypertable por tempo
SELECT create_hypertable('vital_sign', 'recorded_at');

-- Scores: hypertable por tempo
SELECT create_hypertable('clinical_score', 'calculated_at');

-- Alertas: hypertable por tempo
SELECT create_hypertable('alert', 'created_at');
```

---

## Política de retenção

| Tabela | Retenção | Justificativa |
|--------|----------|---------------|
| `vital_sign` | 90 dias | Dados brutos mantidos para auditoria clínica de curto prazo |
| `clinical_score` | 7 anos | Scores históricos para análise de qualidade e pesquisa |
| `alert` | 7 anos | Registro de alertas para compliance e melhoria do sistema |
| `patient_cache` | Até alta + 30 dias | Cache volátil; fonte primária é o MPI |

> Dados analíticos de longo prazo residem no Gold layer da AMH Data Platform (Apache Iceberg, time-travel 30 dias, snapshots).
