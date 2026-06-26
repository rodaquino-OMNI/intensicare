# Catálogo de Alertas Clínicos Inteligentes — Intensicare

**Versão:** 1.0.0
**Data:** 26 de Junho de 2026
**Status:** Proposta para Fase 2

---

## Sobre este Catálogo

Este documento cataloga todos os alertas clínicos inteligentes propostos para a Fase 2 do Intensicare, organizados por domínio clínico. Cada entrada especifica: identificador único, nome clínico, severidade, dados de entrada necessários, lógica de gatilho, base de evidência, integração com o AMH Data Platform, e prioridade de implementação.

### Legenda de Severidade

| Código | Severidade | Significado | Cor |
|--------|-----------|-------------|-----|
| **CRIT** | Crítica | Risco iminente de vida — ação em < 5 min | 🔴 |
| **URG** | Urgente | Deterioração significativa — ação em < 30 min | 🟠 |
| **WARN** | Alerta | Alteração relevante — ação em < 2h | 🟡 |
| **INFO** | Informativo | Tendência ou risco — ação em < 6h | 🔵 |

### Legenda de Prioridade de Implementação

| Prioridade | Critério |
|------------|----------|
| **P1** | Alto impacto + alta disponibilidade de dados + baixa complexidade |
| **P2** | Alto impacto + média disponibilidade de dados + média complexidade |
| **P3** | Moderado impacto + baixa disponibilidade de dados + alta complexidade |

---

## 1. Infecção e Detecção de Sepse

### SEP-001: SIRS Positivo com Suspeita de Infecção

| Campo | Valor |
|-------|-------|
| **ID** | `SEP-001` |
| **Nome** | SIRS positivo com suspeita de infecção |
| **Severidade** | 🟠 URG |
| **Prioridade** | P1 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| Temperatura corporal | Monitor multiparamétrico (HL7 ORU) / FHIR | `Observation` (LOINC 8310-5) | Contínua / a cada 1h | Sim |
| Frequência cardíaca | Monitor multiparamétrico (HL7 ORU) | `Observation` (LOINC 8867-4) | Contínua / a cada 5 min | Sim |
| Frequência respiratória | Monitor multiparamétrico (HL7 ORU) | `Observation` (LOINC 9279-1) | Contínua / a cada 5 min | Sim |
| Leucócitos | Laboratório (FHIR DiagnosticReport) | `Observation` (LOINC 6690-2) | A cada 24h ou on-demand | Sim |
| Cultura positiva | Laboratório (FHIR DiagnosticReport) | `Observation` (microbiologia) | On result | Não (fortalece alerta) |
| Suspeita clínica de infecção | EMR — registros médicos | `Condition` (SNOMED) | On documentation | Não (fortalece alerta) |

**Lógica de Gatilho:**

```
SEP-001 dispara quando TODOS os seguintes critérios são atendidos:
  (temp > 38.0°C OU temp < 36.0°C)                    # SIRS critério 1
  E (hr > 90 bpm)                                       # SIRS critério 2
  E (rr > 20 rpm OU PaCO₂ < 32 mmHg)                    # SIRS critério 3
  E (wbc > 12.000/μL OU wbc < 4.000/μL OU bands > 10%) # SIRS critério 4
  E pelo menos 2 critérios acima são positivos
  E (cultura positiva OU antibiótico iniciado nas últimas 24h OU registro de suspeita de infecção)

Janela de avaliação: últimas 6 horas
```

**Evidência Científica:**
- Bone RC et al. Definitions for sepsis and organ failure (ACCP/SCCM Consensus). *Chest*. 1992;101(6):1644-1655.
- Kaukonen KM et al. Systemic Inflammatory Response Syndrome Criteria in Defining Severe Sepsis. *NEJM*. 2015;372:1629-1638.
- Surviving Sepsis Campaign 2021 — reconhecimento precoce como etapa crítica.

**Limitações:** SIRS tem baixa especificidade (pode ser positivo em pancreatite, trauma, pós-operatório sem infecção). O alerta SIRS deve ser contextualizado com evidência de infecção.

**Ação Clínica Sugerida:** Avaliar foco infeccioso, coletar culturas (se ainda não coletadas), considerar início de antimicrobiano empírico.

---

### SEP-002: qSOFA ≥ 2 com Tendência de Lactato

| Campo | Valor |
|-------|-------|
| **ID** | `SEP-002` |
| **Nome** | qSOFA positivo com lactato elevado ou em elevação |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| Frequência respiratória | Monitor / FHIR | `Observation` (LOINC 9279-1) | A cada 5 min | Sim |
| Glasgow Coma Scale | Enfermagem (EMR) / FHIR | `Observation` (LOINC 9269-2) | A cada 2–6h | Sim |
| Pressão arterial sistólica | Monitor / FHIR | `Observation` (LOINC 8480-6) | Contínua | Sim |
| Lactato sérico | Laboratório / FHIR | `Observation` (LOINC 2524-7) | A cada 2–6h (bundle sepse) | Sim |
| Lactato anterior (para delta) | TimescaleDB (histórico) | Interno | Lookback 6h | Sim |

**Lógica de Gatilho:**

```
SEP-002 dispara quando:
  (rr ≥ 22 rpm)                                       # qSOFA critério 1
  E (gcs ≤ 13)                                         # qSOFA critério 2
  E (sbp ≤ 100 mmHg)                                   # qSOFA critério 3
  E (pelo menos 2 dos 3 critérios qSOFA positivos)
  E (
      lactato_atual > 2.0 mmol/L
      OU delta_lactato > 0.5 mmol/L/h nas últimas 6h
    )

Se lactato ≥ 4.0 mmol/L, elevar severidade para CRIT com flag "choque séptico iminente".
```

**Evidência Científica:**
- Seymour CW et al. Assessment of Clinical Criteria for Sepsis (Sepsis-3). *JAMA*. 2016;315(8):762-774.
- Singer M et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). *JAMA*. 2016;315(8):801-810.
- SSC 2021 — Bundle de 1h: medir lactato, coletar culturas, iniciar ATB, cristaloides 30 mL/kg, vasopressor se necessário.

**Limitações:** qSOFA pode ser negativo em pacientes imunocomprometidos ou com β-bloqueadores. Lactato pode estar elevado por outras causas (hepatopatia, uso de epinefrina, metformina).

---

### SEP-003: Procalcitonina em Elevação (Desmame/Stewardship)

| Campo | Valor |
|-------|-------|
| **ID** | `SEP-003` |
| **Nome** | Procalcitonina — orientação para antibioticoterapia |
| **Severidade** | 🔵 INFO |
| **Prioridade** | P2 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| Procalcitonina (PCT) atual | Laboratório / FHIR | `Observation` (LOINC 33959-8) | A cada 24–48h | Sim |
| PCT anterior (para delta) | TimescaleDB | Interno | Lookback 48h | Sim |
| Antimicrobiano ativo | FHIR MedicationRequest | `MedicationRequest` | On ordem | Sim |
| Data de início do ATB | FHIR MedicationAdministration | `MedicationAdministration` | On administração | Sim |

**Lógica de Gatilho:**

```
SEP-003a (Sugestão de desmame — INFO):
  pct_atual < 0.25 ng/mL
  OU (pico_pct - pct_atual) / pico_pct > 0.80
  E antibioticoterapia ativa há ≥ 48h
  E paciente estável (não atende SEP-001 ou SEP-002)

SEP-003b (Falha de resposta — URG):
  pct_atual > pct_anterior
  E delta > 0.25 ng/mL em 24h
  E antibioticoterapia ativa há ≥ 48h
```

**Evidência Científica:**
- Schuetz P et al. Procalcitonin to initiate or discontinue antibiotics in acute respiratory tract infections. *Cochrane Database Syst Rev*. 2017;10:CD007498.
- PROGRESS Trial (Jensen JU et al.). Procalcitonin-guided interventions against infections. *Lancet Infect Dis*. 2011;11(1):19-27.
- Dunkel-Cohen S et al. Procalcitonin-guided antimicrobial therapy (PROGRESS-AKI). *JAMA*. 2023;329(15):1276-1286.

**Limitações:** PCT pode estar elevada em pós-operatório de grande porte, trauma, queimaduras, carcinoma medular de tireoide sem infecção.

---

## 2. Injúria Renal Aguda (AKI) — KDIGO

### AKI-001: KDIGO Estágio 1

| Campo | Valor |
|-------|-------|
| **ID** | `AKI-001` |
| **Nome** | Injúria Renal Aguda KDIGO Estágio 1 |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P1 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| Creatinina sérica atual | Laboratório / FHIR | `Observation` (LOINC 2160-0) | A cada 24h / on-demand | Sim |
| Creatinina basal (menor valor em 3 meses ou admissão) | TimescaleDB / FHIR histórico | `Observation` | Lookback 90 dias | Sim |
| Débito urinário (mL/kg/h) | Monitor / Balanço hídrico | `Observation` (LOINC 9187-6) | Horário | Sim |
| Peso do paciente | EMR Admissão / FHIR | `Observation` (LOINC 29463-7) | Na admissão | Sim |

**Lógica de Gatilho:**

```
AKI-001 dispara quando:

  CRITÉRIO DE CREATININA:
    (cr_atual - cr_basal) ≥ 0.3 mg/dL (26.5 μmol/L) em 48h
    OU cr_atual ≥ 1.5 × cr_basal (confirmado em 7 dias)

  OU CRITÉRIO DE DÉBITO URINÁRIO:
    diurese < 0.5 mL/kg/h por ≥ 6 horas consecutivas
```

**Evidência Científica:**
- KDIGO Clinical Practice Guideline for Acute Kidney Injury. *Kidney Int Suppl*. 2012;2(1):1-138.
- Hoste EAJ et al. Epidemiology of acute kidney injury in critically ill patients. *Intensive Care Med*. 2015;41(8):1411-1423.
- Mehta RL et al. Recognition and management of acute kidney injury. *Lancet*. 2015;385(9987):1886-1903.

**Ação Clínica Sugerida:** Revisar medicamentos nefrotóxicos, otimizar hemodinâmica (PAM ≥ 65 mmHg), evitar contraste iodado, monitorizar diurese horária.

---

### AKI-002: KDIGO Estágio 2

| Campo | Valor |
|-------|-------|
| **ID** | `AKI-002` |
| **Nome** | Injúria Renal Aguda KDIGO Estágio 2 |
| **Severidade** | 🟠 URG |
| **Prioridade** | P1 |

**Lógica de Gatilho:**

```
AKI-002 dispara quando:
  cr_atual ≥ 2.0 × cr_basal
  OU diurese < 0.5 mL/kg/h por ≥ 12 horas consecutivas
```

---

### AKI-003: KDIGO Estágio 3

| Campo | Valor |
|-------|-------|
| **ID** | `AKI-003` |
| **Nome** | Injúria Renal Aguda KDIGO Estágio 3 |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Lógica de Gatilho:**

```
AKI-003 dispara quando:
  cr_atual ≥ 3.0 × cr_basal
  OU cr_atual ≥ 4.0 mg/dL (353.6 μmol/L) com aumento agudo ≥ 0.5 mg/dL
  OU diurese < 0.3 mL/kg/h por ≥ 24 horas
  OU anúria por ≥ 12 horas
  OU início de TRS (terapia renal substitutiva)
```

---

### AKI-004: Progressão de Estágio KDIGO

| Campo | Valor |
|-------|-------|
| **ID** | `AKI-004` |
| **Nome** | Progressão AKI — mudança de estágio em 24h |
| **Severidade** | 🟠 URG |
| **Prioridade** | P1 |

**Lógica de Gatilho:**

```
AKI-004 dispara quando:
  estágio_kdigo_atual > estágio_kdigo_24h_antes
  E estágio_kdigo_24h_antes != NULL
```

---

### AKI-005: Nefrotoxicidade Aditiva

| Campo | Valor |
|-------|-------|
| **ID** | `AKI-005` |
| **Nome** | Risco de AKI por nefrotoxicidade aditiva |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P2 |

**Dados de Entrada (adicionais):**

| Dado | Fonte | Tipo FHIR | Frequência |
|------|-------|-----------|------------|
| Vancomicina ativa | FHIR MedicationAdministration | medication.code | On administração |
| Aminoglicosídeo ativo | FHIR MedicationAdministration | medication.code | On administração |
| AINE ativo | FHIR MedicationAdministration | medication.code | On administração |
| Contraste iodado | FHIR Procedure | `Procedure` | Últimos 3 dias |
| IECA / BRA ativo | FHIR MedicationAdministration | medication.code | On administração |

**Lógica de Gatilho:**

```
AKI-005 dispara quando:
  cr_atual > cr_basal + 0.2 mg/dL (tendência de elevação)
  E (
      (vancomicina + aminoglicosídeo simultâneos)
      OU (vancomicina + contraste em 72h)
      OU (aminoglicosídeo + AINE)
      OU (IECA/BRA + depleção de volume + Cr em elevação)
    )
```

**Evidência Científica:**
- KDIGO Drug-Induced Kidney Injury. *Kidney Int*. 2023;104(1):1-19.
- Rybak MJ et al. Therapeutic monitoring of vancomycin. *Am J Health Syst Pharm*. 2020;77(11):835-864.

---

## 3. Insuficiência Respiratória

### RESP-001: SDRA Leve (Berlin — SpO₂/FiO₂)

| Campo | Valor |
|-------|-------|
| **ID** | `RESP-001` |
| **Nome** | SDRA Leve — SpO₂/FiO₂ ≤ 315 |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P2 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| SpO₂ | Monitor / FHIR | `Observation` (LOINC 2708-6) | Contínua / 5 min | Sim |
| FiO₂ | Ventilador / EMR | `Observation` (LOINC 19935-6) | A cada mudança | Sim |
| PaO₂ (gasometria) | Laboratório / FHIR | `Observation` (LOINC 2703-7) | On gasometria | Opcional (se disponível) |
| PEEP | Ventilador / EMR | `Observation` (LOINC 20077-4) | A cada ajuste | Opcional |

**Lógica de Gatilho:**

```
RESP-001 dispara quando:
  paciente em ventilação mecânica ou O₂ suplementar
  E spo2_fio2_ratio ≤ 315   # Equivalente aproximado de PaO₂/FiO₂ 200-300
    ONDE spo2_fio2_ratio = SpO₂ / FiO₂ (FiO₂ como fração decimal: 0.21 a 1.0)

  Se gasometria disponível:
    pao2_fio2_ratio ≤ 300 E > 200 (confirma SDRA leve)
  E PEEP ou CPAP ≥ 5 cmH₂O
```

**Nota técnica — Equivalência SpO₂/FiO₂ para PaO₂/FiO₂:**
- SpO₂ ≤ 97%: PaO₂/FiO₂ ≈ 0,95 × (SpO₂/FiO₂)
- SpO₂ > 97%: SpO₂/FiO₂ superestima PaO₂/FiO₂ (usar com cautela)
- Referência: Rice TW et al. *Chest*. 2017;152(3):518-526.

---

### RESP-002: SDRA Moderada a Grave

| Campo | Valor |
|-------|-------|
| **ID** | `RESP-002` |
| **Nome** | SDRA Moderada (SpO₂/FiO₂ ≤ 235) |
| **Severidade** | 🟠 URG |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
RESP-002 (Moderada):
  spo2_fio2_ratio ≤ 235 (equiv. PaO₂/FiO₂ 100-200)
  E em ventilação mecânica

RESP-002b (Grave — elevar para CRIT):
  spo2_fio2_ratio ≤ 148 (equiv. PaO₂/FiO₂ < 100)
  OU pao2_fio2_ratio < 100 (se gasometria disponível)
```

---

### RESP-003: Deterioração Ventilatória em Curso

| Campo | Valor |
|-------|-------|
| **ID** | `RESP-003` |
| **Nome** | Deterioração ventilatória — tendência SpO₂/FiO₂ |
| **Severidade** | 🟠 URG |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
RESP-003 dispara quando:
  delta_spo2_fio2_6h < -20%    # Queda > 20% em 6 horas
  OU (
      fiO₂_atual > fiO₂_6h_antes * 1.3   # Aumento > 30% da FiO₂
      E spo2_atual ≤ spo2_6h_antes       # SpO₂ igual ou menor apesar de mais O₂
    )
```

---

### RESP-004: Prontidão para Desmame (Informação Positiva)

| Campo | Valor |
|-------|-------|
| **ID** | `RESP-004` |
| **Nome** | Prontidão para desmame ventilatório |
| **Severidade** | 🔵 INFO |
| **Prioridade** | P3 |

**Lógica de Gatilho:**

```
RESP-004 dispara quando TODOS os critérios estão presentes por ≥ 2h:
  spo2_fio2_ratio > 315
  E peep ≤ 8 cmH₂O
  E rsbi < 105 (FR/Vt — Rapid Shallow Breathing Index, se disponível)
  E ausência de vasopressor em dose alta (noradrenalina ≤ 0,2 μg/kg/min)
  E RASS ≥ -2 (paciente despertável)
```

**Evidência Científica:**
- Boles JM et al. Weaning from mechanical ventilation. *Eur Respir J*. 2007;29(5):1033-1056.
- Thille AW et al. The decision to extubate in the intensive care unit. *Am J Respir Crit Care Med*. 2013;187(12):1294-1302.

---

## 4. Instabilidade Hemodinâmica

### HEMO-001: Shock Index Elevado

| Campo | Valor |
|-------|-------|
| **ID** | `HEMO-001` |
| **Nome** | Shock Index > 0,9 — hipoperfusão oculta |
| **Severidade** | 🟠 URG |
| **Prioridade** | P2 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| Frequência cardíaca | Monitor | `Observation` (LOINC 8867-4) | Contínua | Sim |
| Pressão arterial sistólica | Monitor | `Observation` (LOINC 8480-6) | Contínua | Sim |
| Pressão arterial média (PAM) | Monitor (invasivo ou oscilométrico) | `Observation` (LOINC 8478-0) | Contínua | Sim |

**Lógica de Gatilho:**

```
HEMO-001 (Shock Index clássico):
  si = hr / sbp
  si > 0.9 sustentado por > 15 minutos

HEMO-001b (Shock Index modificado — MSI):
  msi = hr / map
  msi > 1.3 sustentado por > 15 minutos
```

**Evidência Científica:**
- Rady MY et al. A comparison of the shock index and conventional vital signs. *Ann Emerg Med*. 1994;24(4):685-690.
- Liu YC et al. Modified Shock Index and Mortality in Septic Shock. *Crit Care*. 2012;16(5):R174.
- Cannon CM et al. Shock index predicts mortality in emergency department patients. *West J Emerg Med*. 2011;12(2):197-202.

---

### HEMO-002: Clearance de Lactato Inadequado

| Campo | Valor |
|-------|-------|
| **ID** | `HEMO-002` |
| **Nome** | Clearance de lactato < 10% em 2h |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
HEMO-002 dispara quando:
  lactato_inicial ≥ 2.0 mmol/L
  E clearance_lactato_2h < 10%
      ONDE clearance = (lactato_inicial - lactato_2h) / lactato_inicial
  OU lactato_6h > 2.0 mmol/L após ressuscitação ativa
```

**Evidência Científica:**
- Jones AE et al. Lactate clearance vs central venous oxygen saturation as goals of early sepsis therapy. *JAMA*. 2010;303(8):739-746.
- Jansen TC et al. Early lactate-guided therapy in intensive care unit patients. *Am J Respir Crit Care Med*. 2010;182(6):752-761.

---

### HEMO-003: Vasopressor Escalating

| Campo | Valor |
|-------|-------|
| **ID** | `HEMO-003` |
| **Nome** | Escalonamento de vasopressor |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P2 |

**Dados de Entrada (adicionais):**

| Dado | Fonte | Tipo FHIR | Frequência |
|------|-------|-----------|------------|
| Noradrenalina — dose atual | Bomba de infusão / EMR | `MedicationAdministration` (dose.rate) | Contínua |
| Noradrenalina — dose 2h antes | TimescaleDB | Interno | Lookback 2h |
| Vasopressina — dose atual | Bomba de infusão / EMR | `MedicationAdministration` | Contínua |
| Dobutamina — dose atual | Bomba de infusão / EMR | `MedicationAdministration` | Contínua |

**Lógica de Gatilho:**

```
HEMO-003a (Dose escalation):
  dose_noradrenalina_atual > dose_noradrenalina_2h_antes * 1.5  # Aumento > 50%

HEMO-003b (Adição de 2º vasopressor):
  noradrenalina_ativa = true
  E (vasopressina_iniciada_em_2h = true OU dobutamina_iniciada_em_2h = true)

HEMO-003c (Vasopressor máximo — choque refratário):
  dose_noradrenalina > 1.0 μg/kg/min
  E map < 65 mmHg por > 30 min
```

**Evidência Científica:**
- SEPSISPAM Trial (Asfar P et al.). High versus Low Blood-Pressure Target in Septic Shock. *NEJM*. 2014;370(17):1583-1593.
- SCCM Guidelines 2024 — vasopressor management.

---

### HEMO-004: Fluid Responsiveness Negativo

| Campo | Valor |
|-------|-------|
| **ID** | `HEMO-004` |
| **Nome** | Não responsivo a fluidos — risco de sobrecarga |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P3 |

**Lógica de Gatilho:**

```
HEMO-004 dispara quando (requer monitor avançado):
  ppv < 10% OU svv < 10%   # Variação de pressão de pulso / volume sistólico
  E delta_sv_apos_fluid < 10%   # Fluid challenge sem resposta
  E balanço_hidrico_24h > 3000 mL positivo

Se PPV/SVV não disponível, usar:
  fluid_challenge_realizado = true (500 mL cristaloide em 30 min)
  E delta_map < 5 mmHg após fluid
  E delta_lactato < 5% após fluid
```

**Evidência Científica:**
- Marik PE et al. Dynamic changes in arterial waveform derived variables and fluid responsiveness. *Crit Care Med*. 2013;41(5):1288-1294.
- Monnet X et al. Prediction of fluid responsiveness. *Intensive Care Med*. 2016;42(12):1926-1935.

---

## 5. Delirium — Gatilhos CAM-ICU

### DEL-001: RASS Fora da Faixa Alvo

| Campo | Valor |
|-------|-------|
| **ID** | `DEL-001` |
| **Nome** | Sedação fora da faixa alvo (RASS) |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P3 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| RASS (Richmond Agitation-Sedation Scale) | Enfermagem / EMR | `Observation` (LOINC 75826-6) | A cada 2–4h | Sim |
| Indicação de sedação profunda | EMR | `Condition` / plano terapêutico | On documentation | Sim |
| Ventilação mecânica | Monitor / EMR | `Procedure` | Contínua | Contexto |

**Lógica de Gatilho:**

```
DEL-001 dispara quando:
  (rass > +1)  # Agitação — risco de autoextubação, remoção de dispositivos
  OU (
      rass < -3                            # Sedação profunda
      E sem_indicação_sedacao_profunda = true   # Sem SDRA grave, ECMO, BNM, PIC elevada
      E em_ventilacao_mecanica = true
    )
  sustentado por > 2 avaliações consecutivas (≥ 4h)
```

---

### DEL-002: CAM-ICU Positivo

| Campo | Valor |
|-------|-------|
| **ID** | `DEL-002` |
| **Nome** | Delirium — CAM-ICU positivo |
| **Severidade** | 🟠 URG |
| **Prioridade** | P3 |

**Dados de Entrada (adicionais):**

| Dado | Fonte | Tipo FHIR | Frequência |
|------|-------|-----------|------------|
| CAM-ICU Feature 1 (Alteração aguda / curso flutuante) | Enfermagem / EMR | `Observation` (LOINC 8683-5) | A cada turno (8–12h) |
| CAM-ICU Feature 2 (Inatenção) | Enfermagem / EMR | `Observation` (LOINC 8684-3) | A cada turno |
| CAM-ICU Feature 3 (Nível de consciência alterado) | = RASS ≠ 0 | `Observation` | Idem RASS |
| CAM-ICU Feature 4 (Desorganização do pensamento) | Enfermagem / EMR | `Observation` (LOINC 8686-8) | A cada turno |

**Lógica de Gatilho:**

```
DEL-002 dispara quando:
  cam_icu_f1 = positivo  # Alteração aguda ou curso flutuante
  E cam_icu_f2 = positivo  # Inatenção
  E (cam_icu_f3 = positivo OU cam_icu_f4 = positivo)  # RASS ≠ 0 OU desorganização
  OU cam_icu_resultado_global = "positivo"
```

**Evidência Científica:**
- Ely EW et al. Delirium in mechanically ventilated patients: CAM-ICU. *NEJM*. 2001;345(14):1013-1020.
- Ely EW et al. Evaluation of delirium in critically ill patients. *Crit Care Med*. 2001;29(7):1370-1379.
- PADIS Guidelines (Devlin JW et al.). *Crit Care Med*. 2018;46(9):e825-e873.

---

### DEL-003: Risco de Delirium Iatrogênico

| Campo | Valor |
|-------|-------|
| **ID** | `DEL-003` |
| **Nome** | Risco de delirium iatrogênico — sedação inadequada |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P3 |

**Lógica de Gatilho:**

```
DEL-003 dispara quando:
  benzodiazepinico_infusao_continua = true
  E idade > 65 anos
  E rass ≤ -2
  E sem_indicação_sedacao_profunda = true
  # Alternativa: sugerir transição para dexmedetomidina ou propofol
```

---

### DEL-004: Delirium Hipoativo Não Reconhecido

| Campo | Valor |
|-------|-------|
| **ID** | `DEL-004` |
| **Nome** | Delirium hipoativo possivelmente não reconhecido |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P3 |

**Lógica de Gatilho:**

```
DEL-004 dispara quando:
  rass entre -3 e -1
  E sem_sedacao_ativa_por > 4h  # Sem benzodiazepínico, propofol, dexmedetomidina
  E sem_registro_cam_icu_em > 24h
  # Alerta: "Paciente com RASS reduzido sem sedativos. Considerar CAM-ICU para delirium hipoativo."
```

---

## 6. Emergências Eletrolíticas

### ELY-001: Hipercalemia Grave

| Campo | Valor |
|-------|-------|
| **ID** | `ELY-001` |
| **Nome** | Hipercalemia — K⁺ > 6,5 mmol/L (crítico) |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| Potássio sérico (K⁺) | Laboratório / FHIR | `Observation` (LOINC 6298-4) | On result | Sim |
| ECG (QTc, onda T, QRS) | ECG / FHIR | `Observation` | Últimas 24h | Contexto |
| Função renal (Cr) | Laboratório / FHIR | `Observation` (LOINC 2160-0) | Últimas 24h | Contexto |
| Medicamentos hipercalemiantes | FHIR MedicationRequest | Lista pré-definida | Ativos | Contexto |

**Lógica de Gatilho:**

```
ELY-001a (CRIT — risco de arritmia iminente):
  k > 6.5 mmol/L

ELY-001b (URG):
  k > 6.0 mmol/L E ≤ 6.5 mmol/L

ELY-001c (Tendência — WARN):
  k > 5.5 mmol/L
  E delta_k_24h > 0.5 mmol/L
  E (ckd_stage ≥ 3 OU medicamento_hipercalemiante_ativo)
```

**Medicamentos hipercalemiantes monitorados:**
- Espironolactona, eplerenona
- IECA, BRA, ARA II
- Trimetoprim-sulfametoxazol
- Heparina (prolongada)
- Succinilcolina

**Ação Clínica Sugerida (para CRIT):** ECG imediato, gluconato de cálcio IV (proteção cardíaca), glicose + insulina, β₂-agonista, resina de troca, considerar hemodiálise.

**Evidência Científica:**
- UK Kidney Association (UKKA). Clinical Practice Guidelines — Treatment of Acute Hyperkalaemia in Adults. 2023.
- Clase CM et al. Potassium homeostasis and management of dyskalemia. *BMJ*. 2020;368:m5.

---

### ELY-002: Hipocalemia Grave

| Campo | Valor |
|-------|-------|
| **ID** | `ELY-002` |
| **Nome** | Hipocalemia — K⁺ < 2,5 mmol/L (crítico) |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Lógica de Gatilho:**

```
ELY-002a (CRIT):
  k < 2.5 mmol/L

ELY-002b (URG):
  k < 3.0 mmol/L E ≥ 2.5 mmol/L

ELY-002c (WARN — contexto de alto risco):
  k < 3.5 mmol/L
  E (qtc > 500 ms OU dose_alta_furosemida OU digoxina_ativa)
```

---

### ELY-003: Hiponatremia Grave

| Campo | Valor |
|-------|-------|
| **ID** | `ELY-003` |
| **Nome** | Hiponatremia — Na⁺ < 120 mmol/L (crítico) |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Dados de Entrada (adicionais):**

| Dado | Fonte | Tipo FHIR | Frequência |
|------|-------|-----------|------------|
| Sódio sérico (Na⁺) | Laboratório / FHIR | `Observation` (LOINC 2951-2) | On result |
| Na⁺ anterior (delta) | TimescaleDB | Interno | Lookback 24h |
| Osmolalidade plasmática | Laboratório / FHIR | `Observation` (LOINC 2692-2) | Se disponível |

**Lógica de Gatilho:**

```
ELY-003a (CRIT):
  na < 120 mmol/L

ELY-003b (URG):
  na < 125 mmol/L E ≥ 120 mmol/L

ELY-003c (CRIT — correção rápida demais):
  delta_na_24h > 10 mmol/L   # Risco de mielinólise pontina (síndrome de desmielinização osmótica)
  # Este é um ALERTA DE SEGURANÇA — a correção não deve exceder 8-10 mmol/L em 24h
```

**Evidência Científica:**
- ESICM 2024 Consensus on Diagnosis and Management of Acute Hyponatremia in Intensive Care.
- Sterns RH et al. Osmotic demyelination syndrome: a potentially avoidable disaster. *JASN*. 2015;26(7):1514-1520.

---

### ELY-004: Hipernatremia Grave

| Campo | Valor |
|-------|-------|
| **ID** | `ELY-004` |
| **Nome** | Hipernatremia — Na⁺ > 160 mmol/L (crítico) |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Lógica de Gatilho:**

```
ELY-004a (CRIT):
  na > 160 mmol/L

ELY-004b (URG):
  na > 155 mmol/L

ELY-004c (WARN):
  na > 150 mmol/L E delta_na_24h > 5 mmol/L
```

---

### ELY-005: Hipocalcemia / Hipercalcemia Graves

| Campo | Valor |
|-------|-------|
| **ID** | `ELY-005` |
| **Nome** | Distúrbio grave do cálcio |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P1 |

**Dados de Entrada (adicionais):**

| Dado | Fonte | Tipo FHIR | Frequência |
|------|-------|-----------|------------|
| Cálcio iônico (Ca²⁺) | Laboratório / Gasometria | `Observation` (LOINC 1994-3) | On result |
| Cálcio total | Laboratório / FHIR | `Observation` (LOINC 17861-6) | On result |
| Albumina | Laboratório / FHIR | `Observation` (LOINC 1751-7) | Para correção |
| ECG (QTc) | ECG / FHIR | `Observation` | Últimas 24h |

**Lógica de Gatilho:**

```
ELY-005a (CRIT — hipocalcemia):
  ca_ionico < 0.80 mmol/L
  OU (ca_total_corrigido < 7.0 mg/dL E ca_ionico_indisponivel)
    ONDE ca_corrigido = ca_total + 0.8 × (4.0 - albumina)

ELY-005b (CRIT — hipercalcemia):
  ca_ionico > 1.60 mmol/L
  OU (ca_total_corrigido > 14.0 mg/dL E ca_ionico_indisponivel)

ELY-005c (URG):
  ca_ionico < 0.90 mmol/L OU ca_ionico > 1.45 mmol/L
```

---

### ELY-006: Hipomagnesemia Grave

| Campo | Valor |
|-------|-------|
| **ID** | `ELY-006` |
| **Nome** | Hipomagnesemia — Mg²⁺ < 0,5 mmol/L |
| **Severidade** | 🟠 URG |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
ELY-006a (URG):
  mg < 0.5 mmol/L (1.2 mg/dL)

ELY-006b (WARN):
  mg < 0.7 mmol/L (1.7 mg/dL)

ELY-006c (WARN — contexto):
  mg < 0.9 mmol/L
  E (k < 3.5 mmol/L OU qtc > 500 ms)  # Hipomagnesemia exacerba hipocalemia e prolonga QTc
```

---

## 7. Interações Medicamentosas (EMR)

### DDX-001: QTc Prolongamento — Risco de Torsades de Pointes

| Campo | Valor |
|-------|-------|
| **ID** | `DDX-001` |
| **Nome** | Risco de Torsades por prolongamento de QTc + múltiplas drogas |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P2 |

**Dados de Entrada:**

| Dado | Fonte | Tipo FHIR | Frequência | Obrigatório |
|------|-------|-----------|------------|-------------|
| ECG — QTc (Bazett/Fridericia) | ECG / FHIR | `Observation` (LOINC 44974-4) | Último disponível (24h) | Sim |
| Lista de medicamentos ativos | EMR / FHIR | `MedicationRequest` + `MedicationAdministration` | Em tempo real | Sim |
| K⁺ sérico | Laboratório / FHIR | `Observation` (LOINC 6298-4) | Último disponível | Sim |
| Mg²⁺ sérico | Laboratório / FHIR | `Observation` (LOINC 19123-9) | Último disponível | Sim |
| Idade, sexo | EMR / MPI | `Patient` | Admissão | Sim |

**Lista de drogas de alto risco TdP (CredibleMeds — Known Risk):**
Amiodarona, azitromicina, ciprofloxacino, claritromicina, cloroquina, clorpromazina, citalopram, droperidol, escitalopram, haloperidol, hidroxicloroquina, levofloxacino, metadona, moxifloxacino, ondansetrona, quinidina, sotalol.

**Lógica de Gatilho:**

```
DDX-001 dispara quando:
  qtc > 500 ms
  E ≥ 2 drogas da lista CredibleMeds "Known Risk" ativas simultaneamente

DDX-001b (WARN):
  qtc > 500 ms
  E ≥ 1 droga da lista CredibleMeds "Known Risk" ativa
  E (k < 3.5 mmol/L OU mg < 0.7 mmol/L)  # Distúrbio eletrolítico agravante

DDX-001c (WARN — delta QTc):
  delta_qtc > 60 ms em relação ao ECG anterior
  E ≥ 1 droga de risco iniciada entre os dois ECGs
```

**Evidência Científica:**
- Tisdale JE et al. Development and validation of a risk score to predict QTc prolongation. *Circ Cardiovasc Qual Outcomes*. 2013;6(4):479-487.
- CredibleMeds® — QTdrugs List (www.crediblemeds.org).
- Drew BJ et al. Prevention of Torsade de Pointes in Hospital Settings. *J Am Coll Cardiol*. 2010;55(9):934-947.

---

### DDX-002: Síndrome Serotoninérgica

| Campo | Valor |
|-------|-------|
| **ID** | `DDX-002` |
| **Nome** | Risco de síndrome serotoninérgica — múltiplos agentes |
| **Severidade** | 🟠 URG |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
DDX-002 dispara quando:
  ≥ 2 agentes serotoninérgicos ativos simultaneamente
  E (registro_de_clonus = true OU hipertermia_sem_infeccao = true OU hiperreflexia_documentada = true)

Agentes serotoninérgicos monitorados:
  - ISRS (sertralina, fluoxetina, citalopram, escitalopram, paroxetina)
  - ISRSN (venlafaxina, duloxetina)
  - Linezolida (antibiótico com ação IMAO)
  - Fentanil (opioide com atividade serotoninérgica)
  - Ondansetrona (antiemético 5-HT₃)
  - Metoclopramida (antiemético pró-cinético)
  - Tramadol
  - Azul de metileno
  - Erva de São João (Hypericum)

DDX-002b (WARN — sem sintomas):
  ≥ 3 agentes serotoninérgicos ativos simultaneamente (risco elevado mesmo sem sintomas)
```

**Evidência Científica:**
- Boyer EW, Shannon M. The Serotonin Syndrome. *NEJM*. 2005;352:1112-1120.
- Isbister GK et al. Relative toxicity of selective serotonin reuptake inhibitors. *J Clin Psychiatry*. 2004;65(8):1052-1057.

---

### DDX-003: Depressão Respiratória Sinérgica

| Campo | Valor |
|-------|-------|
| **ID** | `DDX-003` |
| **Nome** | Depressão respiratória por sinergismo de depressores SNC |
| **Severidade** | 🔴 CRIT |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
DDX-003 dispara quando:
  ≥ 2 depressores SNC ativos simultaneamente
  E (rr < 10 rpm OU spo2 < 90%)

Depressores SNC monitorados:
  - Opioides: morfina, fentanil, metadona, tramadol, codeína
  - Benzodiazepínicos: midazolam, diazepam, lorazepam, clonazepam
  - Gabapentinoides: gabapentina, pregabalina
  - Antipsicóticos sedativos: quetiapina, olanzapina, clorpromazina
  - Barbitúricos: fenobarbital, tiopental
  - Anti-histamínicos sedativos: difenidramina, hidroxizina

DDX-003b (WARN):
  ≥ 3 depressores SNC ativos
  E sem monitorização de SpO₂ contínua documentada
```

**Evidência Científica:**
- Overdyk FJ et al. Continuous oximetry/capnometry monitoring reveals frequent desaturation. *Anesth Analg*. 2016;122(5):1568-1573.
- Lee LA et al. Postoperative opioid-induced respiratory depression. *Anesthesiology*. 2015;122(3):659-665.

---

### DDX-004: Duplicidade Terapêutica

| Campo | Valor |
|-------|-------|
| **ID** | `DDX-004` |
| **Nome** | Duplicidade terapêutica — 2+ medicamentos da mesma classe |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P2 |

**Classes monitoradas para duplicidade:**

| Classe Terapêutica | Exemplos |
|--------------------|----------|
| Inibidores de bomba de prótons (IBP) | Omeprazol + Pantoprazol |
| Anticoagulantes | Enoxaparina + Heparina não fracionada em dose plena |
| Antiagregantes plaquetários | AAS + Clopidogrel sem indicação de dupla antiagregação |
| Antieméticos da mesma classe | Ondansetrona + Granisetrona |
| Antipsicóticos | Haloperidol + Quetiapina + Olanzapina |
| Benzodiazepínicos | Midazolam contínuo + Diazepam SOS |
| AINEs | Ibuprofeno + Cetorolaco |

**Lógica de Gatilho:**

```
DDX-004 dispara quando:
  ≥ 2 medicamentos da MESMA classe terapêutica ativos
  E sem_indicacao_combinacao_documentada = true
  E classes_marcadas_como "alerta_duplicidade" = true
```

**Evidência Científica:**
- ISMP (Institute for Safe Medication Practices). Guidelines for Preventing Duplicate Therapy. 2023.
- Maviglia SM et al. Automating duplicate checking in CPOE. *J Am Med Inform Assoc*. 2006;13(3):306-313.

---

### DDX-005: Síndrome de Abstinência Iatrogênica

| Campo | Valor |
|-------|-------|
| **ID** | `DDX-005` |
| **Nome** | Risco de síndrome de abstinência por suspensão abrupta |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P3 |

**Lógica de Gatilho:**

```
DDX-005 dispara quando:
  (benzodiazepinico_continuo_por > 7_dias OU opioide_continuo_por > 7_dias)
  E suspensao_abrupta = true (sem desmame documentado)
  E ≥ 1 sintoma autonomico:
      hr > 100 bpm (taquicardia nova)
      OU sbp > 160 mmHg (hipertensão nova)
      OU temp > 38.0°C (hipertermia nova)
      OU sudorese_documentada
      OU agitacao_documentada (RASS > +1)
```

**Evidência Científica:**
- Devlin JW et al. PADIS Guidelines. *Crit Care Med*. 2018;46(9):e825-e873.
- Korak-Leiter M et al. Iatrogenic withdrawal syndrome in the ICU. *Intensive Care Med*. 2018;44(9):1458-1466.

---

### DDX-006: Antimicrobiano sem Ajuste para Função Renal

| Campo | Valor |
|-------|-------|
| **ID** | `DDX-006` |
| **Nome** | Antimicrobiano com clearance renal sem ajuste para CrCl |
| **Severidade** | 🟡 WARN |
| **Prioridade** | P2 |

**Lógica de Gatilho:**

```
DDX-006 dispara quando:
  antimicrobiano_com_clearance_renal_ativo = true
  E crcl < 30 mL/min (CKD-EPI ou Cockcroft-Gault)
  E dose_prescrita > dose_recomendada_para_crcl_30

Antimicrobianos com ajuste renal monitorados (lista parcial):
  - Vancomicina (dose e intervalo)
  - Meropenem, Imipenem
  - Piperacilina-Tazobactam
  - Cefepime
  - Aciclovir
  - Fluconazol (ajuste se CrCl < 50)
  - Oseltamivir
```

**Evidência Científica:**
- Rybak MJ et al. Therapeutic monitoring of vancomycin: revised consensus guidelines. *Am J Health Syst Pharm*. 2020;77(11):835-864.
- Matzke GR et al. Drug dosing consideration in patients with acute and chronic kidney disease. *Kidney Int*. 2011;80(11):1121-1137.

---

## 8. Tabela-Resumo de Prioridades

| ID | Domínio | Nome | Severidade | Prioridade | Complexidade |
|----|---------|------|------------|------------|--------------|
| SEP-001 | Sepse | SIRS + suspeita infecção | 🟠 URG | **P1** | Baixa |
| SEP-002 | Sepse | qSOFA + lactato | 🔴 CRIT | **P1** | Média |
| SEP-003 | Sepse | Procalcitonina (stewardship) | 🔵 INFO | P2 | Média |
| AKI-001 | Renal | KDIGO Estágio 1 | 🟡 WARN | **P1** | Baixa |
| AKI-002 | Renal | KDIGO Estágio 2 | 🟠 URG | **P1** | Baixa |
| AKI-003 | Renal | KDIGO Estágio 3 | 🔴 CRIT | **P1** | Baixa |
| AKI-004 | Renal | Progressão KDIGO | 🟠 URG | **P1** | Baixa |
| AKI-005 | Renal | Nefrotoxicidade aditiva | 🟡 WARN | P2 | Média |
| RESP-001 | Respiratória | SDRA Leve | 🟡 WARN | P2 | Média |
| RESP-002 | Respiratória | SDRA Moderada/Grave | 🟠 URG | P2 | Média |
| RESP-003 | Respiratória | Deterioração ventilatória | 🟠 URG | P2 | Média |
| RESP-004 | Respiratória | Prontidão desmame | 🔵 INFO | P3 | Média |
| HEMO-001 | Hemodinâmica | Shock Index elevado | 🟠 URG | P2 | Baixa |
| HEMO-002 | Hemodinâmica | Clearance lactato | 🔴 CRIT | P2 | Média |
| HEMO-003 | Hemodinâmica | Vasopressor escalating | 🔴 CRIT | P2 | Média |
| HEMO-004 | Hemodinâmica | Fluid responsiveness | 🟡 WARN | P3 | Alta |
| DEL-001 | Delirium | RASS fora do alvo | 🟡 WARN | P3 | Baixa |
| DEL-002 | Delirium | CAM-ICU positivo | 🟠 URG | P3 | Média |
| DEL-003 | Delirium | Risco delirium iatrogênico | 🟡 WARN | P3 | Média |
| DEL-004 | Delirium | Delirium hipoativo | 🟡 WARN | P3 | Média |
| ELY-001 | Eletrólitos | Hipercalemia (K⁺ > 6,5) | 🔴 CRIT | **P1** | Baixa |
| ELY-002 | Eletrólitos | Hipocalemia (K⁺ < 2,5) | 🔴 CRIT | **P1** | Baixa |
| ELY-003 | Eletrólitos | Hiponatremia (Na⁺ < 120) | 🔴 CRIT | **P1** | Baixa |
| ELY-004 | Eletrólitos | Hipernatremia (Na⁺ > 160) | 🔴 CRIT | **P1** | Baixa |
| ELY-005 | Eletrólitos | Cálcio crítico | 🔴 CRIT | **P1** | Baixa |
| ELY-006 | Eletrólitos | Hipomagnesemia | 🟠 URG | P2 | Baixa |
| DDX-001 | Drogas | QTc + Torsades | 🔴 CRIT | P2 | Alta |
| DDX-002 | Drogas | Síndrome serotoninérgica | 🟠 URG | P2 | Alta |
| DDX-003 | Drogas | Depressão respiratória | 🔴 CRIT | P2 | Média |
| DDX-004 | Drogas | Duplicidade terapêutica | 🟡 WARN | P2 | Média |
| DDX-005 | Drogas | Abstinência iatrogênica | 🟡 WARN | P3 | Média |
| DDX-006 | Drogas | ATB sem ajuste renal | 🟡 WARN | P2 | Média |

**Total de alertas:** 32
- **P1 (Fase 2a):** 14 alertas
- **P2 (Fase 2b):** 13 alertas
- **P3 (Fase 2c):** 5 alertas

**Distribuição por severidade:**
- 🔴 CRIT: 10 alertas
- 🟠 URG: 10 alertas
- 🟡 WARN: 10 alertas
- 🔵 INFO: 2 alertas

---

## 9. Dependências de Dados — Matriz de Disponibilidade

| Fonte de Dados | Disponibilidade Típica (Hospitais Brasileiros) | Domínios Dependentes |
|----------------|-----------------------------------------------|---------------------|
| Sinais vitais (FC, FR, PA, Temp, SpO₂) — HL7 ORU | ✅ Alta (todos os monitores multiparamétricos) | Todos |
| Laboratório (Cr, K⁺, Na⁺, Ca²⁺, Mg²⁺, leuco, lactato, PCT) | ✅ Alta (interfaceamento ASTM/HL7 comum) | Sepse, AKI, Eletrólitos |
| Gasometria arterial (PaO₂, PaCO₂, pH) | ✅ Alta (gasômetro integrado ao LIS) | Respiratória |
| Débito urinário horário | 🟡 Média (balanço hídrico em prontuário eletrônico, raramente automatizado) | AKI |
| Dados do ventilador mecânico (FiO₂, PEEP, Vt, FR programada) | 🟡 Média (depende do fabricante e interfaceamento HL7) | Respiratória |
| Medicamentos ativos (com dose e via) | 🟡 Média (prescrição eletrônica, mas administração nem sempre registrada em tempo real) | Drogas, Delirium |
| ECG com QTc calculado | 🟡 Média (ECG digital disponível, mas QTc automático varia com algoritmo) | Drogas, Eletrólitos |
| CAM-ICU / RASS estruturado | 🔴 Baixa (geralmente texto livre em evolução de enfermagem) | Delirium |
| PPV / SVV (variação de pressão de pulso) | 🔴 Baixa (requer monitor invasivo + software específico) | Hemodinâmica |

---

## 10. Referências do Catálogo

1. **Bone RC et al.** Definitions for sepsis and organ failure (ACCP/SCCM Consensus). *Chest*. 1992;101(6):1644-1655.
2. **Seymour CW et al.** Assessment of Clinical Criteria for Sepsis (Sepsis-3). *JAMA*. 2016;315(8):762-774.
3. **Evans L et al.** Surviving Sepsis Campaign 2021. *Intensive Care Med*. 2021;47:1181-1247.
4. **KDIGO.** Clinical Practice Guideline for Acute Kidney Injury. *Kidney Int Suppl*. 2012;2(1):1-138.
5. **Rice TW et al.** Comparison of the SpO₂/FiO₂ ratio and the PaO₂/FiO₂ ratio in ARDS. *Chest*. 2017;152(3):518-526.
6. **ARDS Definition Task Force.** Berlin Definition. *JAMA*. 2012;307(23):2526-2533.
7. **Rady MY et al.** Shock index and conventional vital signs. *Ann Emerg Med*. 1994;24(4):685-690.
8. **Jones AE et al.** Lactate clearance in sepsis. *JAMA*. 2010;303(8):739-746.
9. **Ely EW et al.** CAM-ICU validation. *NEJM*. 2001;345(14):1013-1020.
10. **Devlin JW et al.** PADIS Guidelines. *Crit Care Med*. 2018;46(9):e825-e873.
11. **UKKA.** Treatment of Acute Hyperkalaemia in Adults. 2023.
12. **Tisdale JE et al.** QTc prolongation risk score. *Circ Cardiovasc Qual Outcomes*. 2013;6(4):479-487.
13. **Boyer EW, Shannon M.** Serotonin Syndrome. *NEJM*. 2005;352:1112-1120.
14. **Rybak MJ et al.** Vancomycin therapeutic monitoring. *Am J Health Syst Pharm*. 2020;77(11):835-864.
15. **Overdyk FJ et al.** Oximetry/capnometry monitoring. *Anesth Analg*. 2016;122(5):1568-1573.
