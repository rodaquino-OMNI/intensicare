# 🔍 Relatório de Auditoria Independente — Intensicare

**Data:** 26 de junho de 2026  
**Auditores:** Equipe de 4 agentes especialistas (Clinical Scoring, Invariants, Claims, Data Architecture)  
**Orquestrador:** Parreira  
**Escopo:** Verificação de claims clínicos, invariantes arquiteturais, conformidade documental e integridade de dados

---

## 1. Sumário Executivo

A auditoria independente do Intensicare v0.1.0-alpha revelou **achados significativos** que devem ser endereçados antes de qualquer uso com dados reais de pacientes:

| Área | Resultado |
|------|:---------:|
| **Clinical Scoring** | ⚠️ 13 discrepâncias em MEWS e NEWS2 Scale 2 |
| **Invariantes Arquiteturais** | ❌ 4 de 6 invariantes FALHANDO |
| **Claims Documentais** | ✅ Corrigidos — documentação atual honesta |
| **Risco Regulatório** | 🔴 3 itens de ALTO RISCO identificados |

**Veredito:** O projeto tem código funcional e bem estruturado, mas **não está pronto para dados de pacientes**. Três invariantes de segurança são críticos e ausentes. Os motores de scoring MEWS e NEWS2 têm erros de implementação que afetam a acurácia clínica.

---

## 2. Clinical Scoring Audit

### 2.1 MEWS (Modified Early Warning Score)

**Referência:** Subbe et al. 2001, *QJM: An International Journal of Medicine*

| Parâmetro | Valor | Código | Subbe MEWS | Erro |
|-----------|-------|:------:|:----------:|:----:|
| Heart Rate | ≤40 | **3** | 2 | **+1** |
| Heart Rate | 41-50 | **2** | 1 | **+1** |
| Respiratory Rate | ≤8 | **3** | 2 | **+1** |
| Temperature | ≤35.0°C | **3** | 2 | **+1** |

**Causa raiz:** Os thresholds baixos (bradicardia, bradipneia, hipotermia) foram copiados do NEWS2 (Royal College of Physicians 2017) em vez do MEWS original (Subbe 2001). Os thresholds altos estão corretos.

**Impacto clínico:** Pacientes bradicárdicos e hipotérmicos recebem scores inflados em +1 ponto, potencialmente gerando alertas falsos-positivos.

### 2.2 NEWS2 (National Early Warning Score 2)

**Referência:** Royal College of Physicians, 2017

#### NEWS2 Scale 2 (Hypercapnic) — SpO₂

| SpO2 | Código | RCP 2017 | Erro |
|------|:------:|:--------:|:----:|
| 86% | **2** | 1 | **+1** |
| 87% | **2** | 1 | **+1** |
| 88% | **1** | 0 | **+1** |
| 89% | **1** | 0 | **+1** |
| 92% | **1** | 0 | **+1** |

**Tabela correta RCP 2017 Scale 2:** ≤83=3, 84-85=2, 86-87=1, 88-92=0, ≥93 on air=0

**Causa raiz:** Off-by-one shift nas bandas 86-87% e 88-92% em `services/news2.py` função `score_spo2()`.

#### NEWS2 Scale 2 — Integração O₂

Paciente hipercápnico com SpO2=97% em O₂:
- Código retorna: 0+2 = **2** (errado)
- RCP 2017 correto: 3+2 = **5**

A função `score_spo2(spo2, hypercapnic=True)` não aceita o parâmetro `supplemental_o2`, impedindo o cálculo correto para SpO2 ≥93% em O₂ na Scale 2.

### 2.3 SOFA (Sequential Organ Failure Assessment)

**Referência:** Vincent et al. 1996, Sepsis-3 (Seymour et al. 2016)

✅ Scoring dos 6 sistemas orgânicos: **CORRETO**  
⚠️ **Inconsistência arquitetural:** Dois caminhos de classificação de risco com thresholds e formatos diferentes:

| SOFA | Caminho Live | Caminho Idempotent Replay |
|------|-------------|--------------------------|
| 5 | `"low"` | `"Moderate (20-50%)"` |
| 9 | `"moderate"` | `"High (50-90%)"` |
| 11 | `"high"` | `"Very High (>90%)"` |

Consumidores downstream receberão labels diferentes dependendo do caminho de execução.

### 2.4 qSOFA (quick SOFA)

**Referência:** Seymour et al. 2016, *JAMA*

✅ **Totalmente correto.** 3 critérios binários (RR≥22, SBP≤100, GCS<15), score ≥2 = alto risco. Sem discrepâncias.

### 2.5 Algorithm Versioning

✅ Todos os 4 motores reportam `algorithm_version` corretamente:
- MEWS: `MEWS-v1.0`
- NEWS2: `NEWS2-v1.0`
- SOFA: `SOFA-v1.0`
- qSOFA: `qSOFA-v1.0`

---

## 3. Architectural Invariants Audit

### Resultados

| # | Invariante | Verdict | Evidência |
|---|-----------|:-------:|-----------|
| **1** | Trilha de auditoria imutável | ❌ **FAIL** | Sem tabela `audit_trail`, sem modelo, sem trigger anti-mutação. `review-queue.md` diz "IMPLEMENTADO" mas é falso. |
| **2** | Idempotência (X-Idempotency-Key) | ✅ **PASS** | Funcionando via `IdempotencyStore` em memória. Necessita migração para Redis em produção (já documentado como TECH-004). |
| **3** | Versionamento de algoritmos | ✅ **PASS** | Coluna `algorithm_version` populada em todos os scores. Verificado em banco live. |
| **4** | Criptografia em repouso (PHI) | ❌ **FAIL** | Sem `pgcrypto`, sem field-level encryption. Dados de paciente em plaintext. |
| **5** | Health check + dead man's switch | ⚠️ **MISSING** | `/health` é estático — sem verificação de DB ou Redis. Sem dead man's switch externo. |
| **6** | Retry com backoff (ARQ/tenacity) | ❌ **FAIL** | `tenacity` instalado mas nunca usado (dead dependency). Sem ARQ, sem retry logic. Alert delivery sem resiliência. |

**Resumo: 2 PASS, 4 FAIL/MISSING.** Três dos seis invariantes não-negociáveis estão completamente ausentes. O projeto **não pode processar dados de pacientes** até que #1 (audit trail), #4 (encryption) e #5 (health check) sejam implementados.

---

## 4. Claims Audit

### 4.1 Original README Claims (pré-correção)

| Claim | Categoria | Risco |
|-------|:--------:|:-----:|
| HIPAA compliance | **FALSE** | 🔴 ALTO |
| GDPR compliance | **FALSE** (sem operação EU) | 🟠 MÉDIO |
| ISO 27001 certified | **FALSE** | 🔴 ALTO |
| "15% reduction in ICU mortality" | **FALSE** | 🔴 CRÍTICO |
| "Validated with 5 academic medical centers" | **FALSE** | 🔴 ALTO |
| Kubernetes/Helm deployment | **FALSE** | 🟢 BAIXO |
| Apache NiFi, Kafka, Flink, ONNX | **FALSE** (são da AMH DP, não do Intensicare) | 🟠 MÉDIO |
| FHIR R4 SMART-on-FHIR | **PARCIAL** (FHIR R4 ✅, SMART ❌) | 🟢 BAIXO |

**Status atual:** ✅ Todos os 8 claims foram removidos ou corrigidos no README atual. Documentação agora reflete honestamente o estado do projeto.

### 4.2 Current Implementation Claims

| Claim | Categoria |
|-------|:--------:|
| MEWS, NEWS2, SOFA, qSOFA funcionando | ✅ ACCURATE (com ressalvas de acurácia) |
| MLLP Listener HL7 v2 | ✅ ACCURATE |
| WebSocket real-time alerts | ✅ ACCURATE |
| FHIR R4 client | ✅ ACCURATE |
| Frontend React Dashboard | ✅ ACCURATE |
| JWT Authentication | ✅ ACCURATE |

---

## 5. Recomendações Imediatas

### 🔴 Crítico (antes de qualquer dado de paciente)

1. **Implementar trilha de auditoria imutável** (Invariante #1)
   - Criar tabela `audit_trail` com trigger anti-mutação
   - Migração Alembic + modelo SQLAlchemy
   - Corrigir `review-queue.md` (remover claim falso de "IMPLEMENTADO")

2. **Implementar criptografia em repouso** (Invariante #4)
   - Instalar `pgcrypto` no PostgreSQL
   - Criptografar colunas PHI: `display_name`, `mrn`, `birth_date`
   - Gerenciamento de chaves via variáveis de ambiente

3. **Corrigir scoring MEWS** (13 boundary errors)
   - Ajustar thresholds baixos para Subbe 2001 (não NEWS2)
   - Atualizar `algorithm_version` para `MEWS-v1.0.1`

4. **Corrigir NEWS2 Scale 2** (5 boundary errors + O₂ integration)
   - Ajustar bandas 86-87% e 88-92% para RCP 2017
   - Adicionar parâmetro `supplemental_o2` à função `score_spo2()`

### 🟠 Alto (antes do piloto clínico)

5. **Unificar caminhos de risco SOFA** — single source of truth para classificação
6. **Health check com verificações de DB e Redis** (Invariante #5)
7. **Dead man's switch externo** — script de monitoramento com alerta
8. **Migrar IdempotencyStore para Redis** — com TTL configurável

### 🟡 Médio (antes de produção)

9. **Implementar retry com backoff** (Invariante #6) — ARQ ou tenacity para notificações
10. **Pentest externo** — contratar antes do deploy em hospital
11. **Certificação SBIS** — iniciar processo

---

## 6. HANDOFF.yaml — Atualizações Necessárias

Os seguintes itens devem ser adicionados/atualizados no HANDOFF.yaml:

**Novos bloqueios:**
- `AUDIT-001` — MEWS scoring: 3 parâmetros inflados vs Subbe 2001
- `AUDIT-002` — NEWS2 Scale 2: 5 boundary errors + O₂ integration gap
- `AUDIT-003` — SOFA: dual risk-classification paths inconsistent
- `AUDIT-004` — Invariante #1: audit_trail completamente ausente
- `AUDIT-005` — Invariante #4: criptografia PHI ausente
- `AUDIT-006` — Invariante #5: health check sem depth
- `AUDIT-007` — Invariante #6: retry/backoff não implementado

---

*Auditoria conduzida por equipe de 4 agentes especialistas em 26 de junho de 2026.*  
*Próxima auditoria recomendada: após implementação dos 4 itens críticos.*
