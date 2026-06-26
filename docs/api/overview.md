# Documentação da API — Intensicare v0.1.0

> Documentação interativa: http://localhost:8000/docs (Swagger UI)
> Documentação alternativa: http://localhost:8000/redoc

---

## 🔐 Autenticação

Todos os endpoints protegidos requerem header `Authorization: Bearer <token>`.

### POST /auth/login

Autentica usuário e retorna tokens JWT.

**Request:**
```json
{
  "username": "medico01",
  "password": "senha-segura-123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### POST /auth/register

Registra novo usuário (**requer role admin**).

**Request:**
```json
{
  "username": "enfermeira_ana",
  "email": "ana@hospital.com",
  "password": "senha-segura-456",
  "display_name": "Enf. Ana"
}
```

**Response (201):**
```json
{
  "id": 2,
  "username": "enfermeira_ana",
  "email": "ana@hospital.com",
  "display_name": "Enf. Ana",
  "is_admin": false,
  "is_active": true
}
```

### POST /auth/logout

Invalida o token atual (blacklist no Redis). Requer autenticação.

**Response (200):**
```json
{
  "detail": "Logged out successfully"
}
```

---

## 🩺 Sinais Vitais

### POST /api/v1/vitals

Ingere sinais vitais de um paciente, calcula MEWS + NEWS2 + SOFA + qSOFA e dispara alert engine.

**Headers opcionais:**
- `X-Idempotency-Key: <chave>` — Garante idempotência (MSH-10 para HL7)

**Request:**
```json
{
  "mpi_id": "MPI-00012345",
  "recorded_at": "2026-06-26T10:00:00Z",
  "heart_rate": 88,
  "systolic_bp": 125,
  "diastolic_bp": 80,
  "temperature": 37.0,
  "spo2": 97,
  "respiratory_rate": 16,
  "avpu": "A",
  "supplemental_o2": false,
  "source_system": "philips_monitor",
  "pao2_fio2": null,
  "mechanical_ventilation": false,
  "platelets": null,
  "bilirubin": null,
  "map_value": null,
  "vasopressor_type": null,
  "vasopressor_dose_mcg_kg_min": null,
  "gcs": null,
  "creatinine": null,
  "urine_output_ml_day": null
}
```

**Campos obrigatórios:**
- `mpi_id` (string, max 64): Master Patient Identifier
- `recorded_at` (datetime ISO 8601): Momento da coleta

**Campos opcionais para MEWS:**
- `heart_rate` (int, 0-300): Frequência cardíaca (bpm)
- `systolic_bp` (int, 0-350): Pressão sistólica (mmHg)
- `diastolic_bp` (int, 0-250): Pressão diastólica (mmHg)
- `temperature` (float, 25.0-45.0): Temperatura (°C)
- `spo2` (int, 0-100): Saturação O2 (%)
- `respiratory_rate` (int, 0-80): Frequência respiratória (rpm)
- `avpu` (string, "A"/"V"/"P"/"U"): Nível de consciência
- `supplemental_o2` (bool): Oxigênio suplementar
- `source_system` (string, max 32): Sistema de origem

**Campos laboratoriais para SOFA:**
- `pao2_fio2` (float, 0-800): Razão PaO2/FiO2 (mmHg)
- `mechanical_ventilation` (bool): Ventilação mecânica
- `platelets` (float, ≥0): Plaquetas (×10³/µL)
- `bilirubin` (float, ≥0): Bilirrubina total (mg/dL)
- `map_value` (float, 0-250): Pressão arterial média (mmHg)
- `vasopressor_type` (string): Tipo de vasopressor
- `vasopressor_dose_mcg_kg_min` (float, ≥0): Dose (µg/kg/min)
- `gcs` (int, 3-15): Glasgow Coma Scale
- `creatinine` (float, ≥0): Creatinina sérica (mg/dL)
- `urine_output_ml_day` (float, ≥0): Débito urinário 24h (mL/dia)

**Response (201 Created):**
```json
{
  "id": 42,
  "mpi_id": "MPI-00012345",
  "recorded_at": "2026-06-26T10:00:00Z",
  "ingested_at": "2026-06-26T10:00:05.123456Z",
  "mews_score": 0,
  "news2_score": 0,
  "news2_risk_category": "low",
  "sofa_score": 0,
  "sofa_mortality_risk": "low",
  "qsofa_score": 0,
  "qsofa_is_high_risk": false,
  "message": "Vital signs ingested successfully"
}
```

**Response (200 OK — idempotent replay):**
```json
{
  "id": 42,
  "mpi_id": "MPI-00012345",
  ...
  "message": "Idempotent replay — vital signs already ingested"
}
```

**Errors:** 422 (validação), 500 (erro interno)

---

## 👤 Pacientes

### GET /api/v1/patients/{mpi_id}/status

Retorna status agregado do paciente: sinais vitais mais recentes, último score e tendência.

**Query params:**
- `score_type` (string, default "MEWS"): Tipo de score ("MEWS", "NEWS2", "SOFA", "qSOFA")

**Response (200):**
```json
{
  "mpi_id": "MPI-00012345",
  "latest_vitals": {
    "id": 42,
    "recorded_at": "2026-06-26T10:00:00Z",
    "heart_rate": 88,
    "systolic_bp": 125,
    "diastolic_bp": 80,
    "temperature": 37.0,
    "spo2": 97,
    "respiratory_rate": 16,
    "avpu": "A",
    "supplemental_o2": false
  },
  "latest_mews": {
    "id": 55,
    "score_type": "MEWS",
    "score_value": 0,
    "calculated_at": "2026-06-26T10:00:05Z",
    "components": {
      "heart_rate": 0,
      "systolic_bp": 0,
      "respiratory_rate": 0,
      "temperature": 0,
      "avpu": 0,
      "algorithm_version": "MEWS-v1.0"
    },
    "trend": "stable",
    "delta_from_previous": 0
  },
  "trend": {
    "values": [0, 0],
    "current_trend": "stable"
  },
  "last_updated": "2026-06-26T10:00:05Z"
}
```

**Nota:** Retorna 200 mesmo sem dados — `latest_vitals` e `latest_mews` vêm como `null` para pacientes nunca ingeridos.

### GET /api/v1/patients/{mpi_id}/detail

**Response (200):**
```json
{
  "mpi_id": "MPI-00012345",
  "bed_id": "LEITO-01",
  "display_name": "João Silva",
  "unit": "UTI-A",
  "vitals_history": [
    {
      "recorded_at": "2026-06-26T10:00:00Z",
      "heart_rate": 88,
      "systolic_bp": 125,
      "diastolic_bp": 80,
      "temperature": 37.0,
      "spo2": 97,
      "respiratory_rate": 16,
      "avpu": "A",
      "supplemental_o2": false
    }
  ],
  "mews_history": [
    {
      "calculated_at": "2026-06-26T10:00:05Z",
      "score_type": "MEWS",
      "score_value": 0,
      "trend": null
    }
  ],
  "news2_history": [
    {
      "calculated_at": "2026-06-26T10:00:05Z",
      "score_type": "NEWS2",
      "score_value": 0,
      "trend": null
    }
  ],
  "active_alerts": []
}
```

---

## 📊 Dashboard

### GET /api/v1/dashboard

Retorna grid de leitos com scores e status de alertas para todos os pacientes ativos.

**Query params:**
- `unit` (string, opcional): Filtrar por unidade

**Response (200):**
```json
{
  "patients": [
    {
      "mpi_id": "MPI-00012345",
      "bed_id": "LEITO-01",
      "display_name": "João Silva",
      "unit": "UTI-A",
      "latest_mews": 0,
      "latest_news2": 0,
      "news2_risk": "low",
      "mews_trend": "stable",
      "news2_trend": null,
      "active_alerts_count": 0,
      "highest_alert_severity": null,
      "last_updated": "2026-06-26T10:00:00Z"
    }
  ],
  "total": 1,
  "active_alerts_total": 0
}
```

---

## 🚨 Alertas

### GET /api/v1/alerts

Lista alertas com filtros opcionais.

**Query params:**
- `status` (string, default "active"): Filtrar por status ("active", "acknowledged", "resolved")
- `mpi_id` (string, opcional): Filtrar por paciente
- `unit` (string, opcional): Filtrar por unidade
- `limit` (int, default 50, max 200): Limite de resultados
- `offset` (int, default 0): Offset para paginação

**Response (200):**
```json
[
  {
    "id": 1,
    "mpi_id": "MPI-SEPSIS01",
    "score_id": 10,
    "severity": "critical",
    "status": "active",
    "title": "MEWS CRITICAL: 8",
    "body": "Patient MPI-SEPSIS01 — MEWS score: 8\nThreshold: 7\nTenant: hospital-austa, Unit: UTI-A",
    "created_at": "2026-06-26T14:30:01Z",
    "acknowledged_at": null,
    "acknowledged_by": null,
    "resolved_at": null,
    "resolution": null
  }
]
```

### POST /api/v1/alerts/{alert_id}/acknowledge

Confirma (acknowledge) um alerta. Requer autenticação.

**Request (opcional):**
```json
{
  "notes": "Paciente em avaliação pela equipe de resposta rápida"
}
```

**Response (200):**
```json
{
  "id": 1,
  "status": "acknowledged",
  "acknowledged_at": "2026-06-26T14:32:00Z",
  "acknowledged_by": "medico01",
  ...
}
```

**Errors:** 401 (não autenticado), 404 (alerta não encontrado), 409 (já confirmado)

### GET /api/v1/alerts/{alert_id}/trace

Retorna detalhes completos de um alerta específico (rastreabilidade).

**Response (200):**
```json
{
  "id": 1,
  "mpi_id": "MPI-SEPSIS01",
  "severity": "critical",
  "status": "acknowledged",
  "title": "MEWS CRITICAL: 8",
  "body": "Patient MPI-SEPSIS01 — MEWS score: 8\n...",
  "created_at": "2026-06-26T14:30:01Z",
  "acknowledged_at": "2026-06-26T14:32:00Z",
  "acknowledged_by": "medico01",
  "resolved_at": null,
  "resolution": null
}
```

---

## ⚙️ Thresholds (Admin)

Todos os endpoints de thresholds requerem autenticação com role **admin**.

### GET /api/v1/thresholds

Lista todas as configurações de threshold.

**Query params:**
- `tenant_id` (string, opcional): Filtrar por tenant

**Response (200):**
```json
[
  {
    "id": 1,
    "tenant_id": "hospital-austa",
    "unit": "UTI-A",
    "score_type": "MEWS",
    "watch_threshold": 3,
    "urgent_threshold": 5,
    "critical_threshold": 7,
    "rate_limit_per_hour": 10,
    "cooldown_minutes": 15,
    "updated_at": "2026-06-26T10:00:00Z",
    "updated_by": "admin"
  }
]
```

### GET /api/v1/thresholds/{threshold_id}

Retorna uma configuração específica por ID.

### POST /api/v1/thresholds

Cria nova configuração de threshold.

**Request:**
```json
{
  "tenant_id": "hospital-austa",
  "unit": "UTI-A",
  "score_type": "MEWS",
  "watch_threshold": 3,
  "urgent_threshold": 5,
  "critical_threshold": 7,
  "rate_limit_per_hour": 10,
  "cooldown_minutes": 15
}
```

**Response (201):** Threshold criado com ID.

### PUT /api/v1/thresholds/{threshold_id}

Atualiza configuração existente (partial update).

### DELETE /api/v1/thresholds/{threshold_id}

Remove configuração. **Response (204 No Content).**

---

## 🔌 WebSocket `/ws`

Conexão WebSocket para receber alertas em tempo real.

### Mensagens do cliente → servidor

**Subscribe a um paciente:**
```json
{"action": "subscribe", "patient_id": "MPI-00012345"}
```

**Unsubscribe de um paciente:**
```json
{"action": "unsubscribe", "patient_id": "MPI-00012345"}
```

**Ping (keepalive):**
```json
{"action": "ping"}
```

### Mensagens do servidor → cliente

**Confirmação de subscribe:**
```json
{"type": "subscribed", "patient_id": "MPI-00012345"}
```

**Alerta em tempo real:**
```json
{
  "type": "alert",
  "id": 1,
  "mpi_id": "MPI-00012345",
  "severity": "critical",
  "status": "active",
  "title": "MEWS CRITICAL: 8",
  "body": "Patient MPI-00012345 — MEWS score: 8\n...",
  "created_at": "2026-06-26T14:30:01Z"
}
```

**Erro:**
```json
{"type": "error", "message": "Invalid JSON message"}
```

**Pong:**
```json
{"type": "pong"}
```

### Comportamento de broadcast

- Clientes sem subscriptions recebem **todos** os alertas
- Clientes com subscriptions recebem apenas alertas dos pacientes subscritos
- Alertas são enviados automaticamente após cada ingestão de vitais que gera alerta

---

## 💚 Health Check

### GET /health

**Response (200):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

---

## 🏷️ Códigos de Resposta

| Código | Significado |
|--------|-------------|
| 200 | Sucesso (ou replay idempotente) |
| 201 | Recurso criado |
| 204 | Recurso removido (sem corpo) |
| 401 | Não autenticado / token inválido |
| 403 | Sem permissão (admin required) |
| 404 | Recurso não encontrado |
| 409 | Conflito (ex: alerta já acknowledged) |
| 422 | Erro de validação |
| 500 | Erro interno do servidor |

---

## 📝 Notas

1. **Idempotência**: O header `X-Idempotency-Key` garante que uma mesma requisição enviada múltiplas vezes não crie registros duplicados. Use o `MSH-10` de mensagens HL7 como chave.

2. **Versionamento de algoritmos**: Todo `ClinicalScore` armazena `algorithm_version` (ex: `MEWS-v1.0`). Isso garante que scores históricos possam ser recalculados com a versão correta do algoritmo.

3. **Rate Limiting de alertas**: O alert engine usa Redis para limitar a taxa de alertas por paciente/score_type (configurável via thresholds) e impor cooldown entre alertas do mesmo tipo/severidade.

4. **Scores ausentes**: Componentes de score com valor `null` contribuem com 0 pontos e são marcados como `missing` nos componentes. O score total é a soma dos componentes disponíveis.
