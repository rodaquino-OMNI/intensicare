# Visão do Produto — Intensicare

**Versão:** 0.2.0-draft
**Data:** 26 de Junho de 2026
**Status:** Em expansão (escopo de alertas inteligentes)

---

## 1. Propósito

O Intensicare é uma plataforma de suporte à decisão clínica para Unidades de Terapia Intensiva (UTI), projetada para hospitais brasileiros. A plataforma opera sobre o **AMH Data Platform** (lakehouse com Apache Iceberg, MPI e FHIR R4), ingerindo sinais vitais, resultados laboratoriais e dados de prontuário eletrônico para gerar alertas inteligentes e recomendações baseadas em evidência.

---

## 2. Escopo Atual (Fase 1 — MVP)

### 2.1 Escores de Alerta Precoce Implementados

| Escore | Descrição | Status |
|--------|-----------|--------|
| **MEWS** | Modified Early Warning Score — deterioração clínica geral | ✅ Implementado |
| **NEWS2** | National Early Warning Score 2 (NHS UK) — incluindo escala para hipercápnicos | ✅ Implementado |
| **SOFA** | Sequential Organ Failure Assessment — disfunção orgânica diária | ✅ Implementado |
| **qSOFA** | Quick SOFA — triagem de sepse à beira-leito | ✅ Implementado |

### 2.2 Pilares Técnicos Atuais

- **Ingestão:** HL7 v2 (MLLP) via listener Python → JSON → API FastAPI
- **Processamento:** Funções determinísticas em Python (sem ML runtime no MVP)
- **Armazenamento:** PostgreSQL + TimescaleDB (hypertables para séries temporais)
- **Filas/Cache:** Redis (cache de estado, rate limiting, pub/sub para alertas)
- **Interface:** API REST (FastAPI) + WebSocket para push em tempo real

---

## 3. Expansão de Escopo — Alertas Clínicos Inteligentes (Fase 2)

A Fase 2 expande o Intensicare além dos escores de alerta precoce tradicionais (MEWS/NEWS), incorporando **7 domínios clínicos de monitoramento inteligente** que combinam sinais vitais, resultados laboratoriais (via FHIR), dados de prontuário (EMR) e análise de tendências temporais.

### 3.1 Infecção e Detecção de Sepse

**Justificativa clínica:** A sepse é a principal causa de morte em UTIs brasileiras (incidência ~30%, mortalidade ~55% segundo ILAS). A detecção precoce (< 1h da identificação) reduz mortalidade em 25–30%.

**Alertas propostos:**

| Alerta | Gatilho | Evidência |
|--------|---------|-----------|
| **SIRS + suspeita de infecção** | ≥2 critérios SIRS + cultura positiva/presumida | Surviving Sepsis Campaign 2021 |
| **qSOFA ≥ 2 com tendência de lactato** | qSOFA ≥2 + lactato > 2 mmol/L ou delta lactato > 0.5 mmol/L/h | Seymour et al., JAMA 2016 |
| **Choque séptico iminente** | Lactato ≥ 4 mmol/L + PAM < 65 mmHg apesar de fluidos | SSC 2021 Bundle de 1h |
| **Procalcitonina em elevação** | PCT > 0.5 ng/mL + delta > 0.25 ng/mL em 24h | Schuetz et al., Lancet ID 2018 |
| **Desmame antimicrobiano** | PCT < 0.25 ng/mL ou queda > 80% do pico + 48h de estabilidade | PROGRESS Trial, JAMA 2023 |

**Dados necessários:** Sinais vitais (FC, FR, temperatura, PA), leucograma, lactato sérico, procalcitonina, culturas, PAM.

**Integração:** FHIR Observation (sinais vitais + labs), FHIR DiagnosticReport (culturas), FHIR MedicationRequest (antimicrobianos).

### 3.2 Injúria Renal Aguda (AKI)

**Justificativa clínica:** AKI ocorre em 30–60% dos pacientes de UTI e está associada a aumento de 6,5× na mortalidade. O diagnóstico precoce pelo KDIGO permite intervenção em estágios reversíveis.

**Alertas propostos:**

| Alerta | Gatilho | Evidência |
|--------|---------|-----------|
| **KDIGO Estágio 1** | Aumento de Cr ≥ 0,3 mg/dL em 48h OU Cr ≥ 1,5× basal OU diurese < 0,5 mL/kg/h por 6h | KDIGO 2012 Guidelines |
| **KDIGO Estágio 2** | Cr ≥ 2,0× basal OU diurese < 0,5 mL/kg/h por 12h | KDIGO 2012 |
| **KDIGO Estágio 3** | Cr ≥ 3,0× basal OU Cr ≥ 4,0 mg/dL com aumento agudo ≥ 0,5 mg/dL OU diurese < 0,3 mL/kg/h por 24h OU anúria por 12h | KDIGO 2012 |
| **Progressão AKI** | Mudança de estágio KDIGO em janela de 24h | KDIGO 2012 |
| **Nefrotoxicidade por drogas** | Início de vancomicina + aminoglicosídeo + contraste + Cr em elevação | AIN Consensus 2020 |

**Dados necessários:** Creatinina sérica (seriado), débito urinário horário, peso do paciente, medicamentos nefrotóxicos.

**Integração:** FHIR Observation (creatinina, diurese), FHIR MedicationRequest, balanço hídrico do monitor multiparamétrico.

### 3.3 Insuficiência Respiratória

**Justificativa clínica:** A monitorização da relação SpO₂/FiO₂ permite detecção de deterioração respiratória equivalente à PaO₂/FiO₂, sem coleta invasiva de gasometria arterial repetida.

**Alertas propostos:**

| Alerta | Gatilho | Evidência |
|--------|---------|-----------|
| **SDRA Leve (Berlin)** | SpO₂/FiO₂ ≤ 315 (equiv. PaO₂/FiO₂ 200–300) OU PaO₂/FiO₂ 200–300 + infiltrados bilaterais | Berlin Definition, JAMA 2012 |
| **SDRA Moderada** | SpO₂/FiO₂ ≤ 235 (equiv. PaO₂/FiO₂ 100–200) OU PaO₂/FiO₂ 100–200 | Berlin Definition |
| **SDRA Grave** | SpO₂/FiO₂ ≤ 148 (equiv. PaO₂/FiO₂ < 100) OU PaO₂/FiO₂ < 100 | Berlin Definition |
| **Deterioração ventilatória** | Queda > 20% em SpO₂/FiO₂ em 6h OU aumento > 30% da FiO₂ para manter SpO₂ alvo | Rice et al., Chest 2017 |
| **Assincronia ventilatória** | FR espontânea > FR programada + P plateau > 30 cmH₂O (se disponível) | Thille et al., ICM 2016 |
| **Prontidão para desmame** | SpO₂/FiO₂ > 315 + PEEP ≤ 8 + FR/Vt < 105 (RSBI) estável por 2h | Boles et al., ERJ 2017 |

**Dados necessários:** SpO₂ contínua, FiO₂ do ventilador, PaO₂ e PaCO₂ (gasometria), FR, volume corrente (Vt), PEEP, P plateau.

**Integração:** FHIR Observation (SpO₂, gasometria), dados do ventilador mecânico via HL7 ORU (OBX segments específicos do fabricante).

### 3.4 Instabilidade Hemodinâmica

**Justificativa clínica:** O choque circulatório não reconhecido tem mortalidade > 80%. Índices combinados (shock index, clearance de lactato) superam a monitorização isolada da pressão arterial.

**Alertas propostos:**

| Alerta | Gatilho | Evidência |
|--------|---------|-----------|
| **Shock Index elevado** | FC / PAS > 0,9 sustentado por > 15 min | Rady et al., Ann Emerg Med 1994 |
| **Shock Index modificado** | FC / PAM > 1,3 sustentado por > 15 min | Liu et al., Crit Care 2012 |
| **Clearance de lactato inadequado** | Clearance < 10% em 2h OU lactato persistente > 2 mmol/L após 6h de ressuscitação | Jones et al., JAMA 2010 |
| **Vasopressor escalating** | Aumento > 50% na dose de noradrenalina em 2h OU adição de 2º vasopressor | SCCM 2024 Guidelines |
| **Hipotensão permissiva não controlada** | PAM < 65 mmHg por > 30 min apesar de vasopressor máximo (ex: noradrenalina > 1 μg/kg/min) | SEPSISPAM Trial, NEJM 2014 |
| **Fluid responsiveness negativo** | Variação de pressão de pulso (PPV) < 10% + fluid challenge sem resposta (aumento VS < 10%) | Marik et al., Crit Care Med 2013 |

**Dados necessários:** FC, PA sistólica/diastólica/média, lactato seriado, doses de vasopressores (droga + taxa de infusão), variação de pressão de pulso (PPV), volume sistólico (se monitor disponível).

**Integração:** FHIR Observation (PA, FC, lactato), FHIR MedicationAdministration (vasopressores com taxa de infusão), dados de monitor hemodinâmico avançado.

### 3.5 Delirium — Gatilhos CAM-ICU

**Justificativa clínica:** Delirium ocorre em 50–80% dos pacientes em ventilação mecânica. Está associado a aumento de 3× na mortalidade, prolongamento da VM e declínio cognitivo de longo prazo. O rastreamento estruturado reduz a duração do delirium em 1–2 dias.

**Alertas propostos:**

| Alerta | Gatilho | Evidência |
|--------|---------|-----------|
| **RASS alvo fora da faixa** | RASS > +1 (agitação) ou RASS < −3 (sedação profunda) em paciente sem indicação de sedação profunda | PADIS Guidelines, ICM 2018 |
| **CAM-ICU positivo** | CAM-ICU positivo (alteração aguda + inatenção + RASS ≠ 0 + desorganização do pensamento) | Ely et al., NEJM 2001 |
| **Risco de delirium iatrogênico** | Benzodiazepínico em infusão contínua + idade > 65 anos + RASS ≤ −2 | PADIS 2018, SCCM |
| **Delirium hipoativo não reconhecido** | RASS entre −1 e −3 + CAM-ICU positivo + sem sedação nas últimas 4h | van den Boogaard et al., BMJ 2014 |
| **Mobilização inadequada** | Ausência de registro de mobilização (sentar à beira-leito, sedestação, deambulação) por > 24h em paciente elegível | TEAM Study, NEJM 2022 |

**Dados necessários:** RASS (Richmond Agitation-Sedation Scale), CAM-ICU (4 features), medicamentos sedativos (droga, dose, via), registro de mobilização, idade.

**Integração:** FHIR Observation (RASS, CAM-ICU), FHIR MedicationAdministration (sedativos), registros de enfermagem (mobilização, contenção).

### 3.6 Emergências Eletrolíticas

**Justificativa clínica:** Distúrbios eletrolíticos graves (K⁺, Na⁺, Ca²⁺) são potencialmente fatais em minutos a horas. A detecção automatizada com thresholds críticos reduz o tempo para correção e previne arritmias, convulsões e parada cardíaca.

**Alertas propostos:**

| Alerta | Gatilho (Crítico) | Gatilho (Urgente) | Evidência |
|--------|--------------------|--------------------|-----------|
| **Hipercalemia grave** | K⁺ > 6,5 mmol/L | K⁺ > 6,0 mmol/L | UKKA 2023 Guidelines |
| **Hipocalemia grave** | K⁺ < 2,5 mmol/L | K⁺ < 3,0 mmol/L | UKKA 2023 |
| **Hipernatremia grave** | Na⁺ > 160 mmol/L | Na⁺ > 155 mmol/L | ESICM 2024 Consensus |
| **Hiponatremia grave** | Na⁺ < 120 mmol/L | Na⁺ < 125 mmol/L | ESICM 2024 |
| **Delta Na⁺ perigoso** | Correção de Na⁺ > 10 mmol/L em 24h (risco de mielinólise pontina) | Correção > 8 mmol/L em 24h | Sterns et al., JASN 2015 |
| **Hipercalcemia grave** | Ca²⁺ iônico > 1,60 mmol/L (ou total corrigido > 14 mg/dL) | Ca²⁺ > 1,45 mmol/L | Mousseaux et al., NDT 2022 |
| **Hipocalcemia grave** | Ca²⁺ iônico < 0,80 mmol/L (ou total corrigido < 7,0 mg/dL) | Ca²⁺ < 0,90 mmol/L | Cooper et al., ICM 2022 |
| **Hipomagnesemia** | Mg²⁺ < 0,5 mmol/L (1,2 mg/dL) | Mg²⁺ < 0,7 mmol/L (1,7 mg/dL) | Hansen et al., ICM 2018 |

**Dados necessários:** K⁺, Na⁺, Ca²⁺ (total e iônico), Mg²⁺, albumina (para correção do Ca), creatinina (clearance para correção de Na⁺).

**Integração:** FHIR Observation (painel eletrolítico), dados de reposição eletrolítica (FHIR MedicationAdministration).

### 3.7 Interações Medicamentosas via EMR

**Justificativa clínica:** Pacientes de UTI recebem em média 12–20 medicamentos simultâneos. Interações medicamentosas graves (contraindicações, QTc prolongamento, síndrome serotoninérgica) são responsáveis por 5–10% dos eventos adversos em UTI.

**Alertas propostos:**

| Alerta | Gatilho | Evidência |
|--------|---------|-----------|
| **QTc prolongamento — risco de Torsades** | QTc > 500 ms (ou delta > 60 ms) + ≥ 2 drogas com risco conhecido de Torsades (CredibleMeds lista) | Tisdale et al., Circ 2013 |
| **Síndrome serotoninérgica** | ≥ 2 agentes serotoninérgicos (ISRS + linezolida + fentanil + ondansetrona + metoclopramida) + clônus/hipertermia/hiperreflexia | Boyer & Shannon, NEJM 2005 |
| **Nefrotoxicidade aditiva** | Vancomicina + aminoglicosídeo + AINE + contraste iodado em 72h | KDIGO Drug-Induced AKI 2023 |
| **Depressão respiratória sinérgica** | ≥ 2 depressores SNC (opioide + benzodiazepínico + gabapentinoide) + FR < 10 ou SpO₂ < 90% | Overdyk et al., Anesth Analg 2016 |
| **Duplicidade terapêutica** | 2+ medicamentos da mesma classe (ex: 2 IBP, 2 antieméticos, 2 anticoagulantes) | ISMP Guidelines 2023 |
| **Síndrome de abstinência** | Suspensão abrupta de BZD/opioide após > 7 dias de uso contínuo + sintomas autonômicos | SCCM PADIS 2018 |
| **Antimicrobiano sem ajuste renal** | Antimicrobiano com clearance renal + CrCl < 30 mL/min sem ajuste de dose | Rybak et al., AJHP 2020 (vancomicina) |

**Dados necessários:** Lista completa de medicamentos ativos (droga, dose, via, frequência, data de início), ECG (QTc), FR, SpO₂, creatinina + clearance estimado, sintomas documentados (clônus, rigidez, hipertermia).

**Integração:** FHIR MedicationRequest + MedicationAdministration, FHIR Observation (ECG, Cr, SpO₂), FHIR Condition (registros de diagnóstico).

---

## 4. Arquitetura de Dados para Alertas Inteligentes (Fase 2)

### 4.1 Modelo de Integração com AMH Data Platform

```
┌──────────────────────────────────────────────────────────────┐
│                   AMH DATA PLATFORM                           │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │   MPI    │  │  FHIR R4 │  │ Iceberg  │  │  FHIR API   │  │
│  │ (Master  │  │ (Store)  │  │(Lakehouse│  │  (Gateway)  │  │
│  │ Patient  │  │          │  │  Tables) │  │             │  │
│  │  Index)  │  │          │  │          │  │             │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘  │
│       │              │             │                │         │
│       └──────────────┴─────────────┴────────────────┘         │
│                              │                                │
└──────────────────────────────┼────────────────────────────────┘
                               │ FHIR REST API
┌──────────────────────────────▼────────────────────────────────┐
│                     INTENSICARE                               │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            ALERT ENGINE (Fase 2)                      │    │
│  │                                                       │    │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐  │    │
│  │  │ Sepsis  │ │   AKI    │ │Respiratory│ │  Hemo  │  │    │
│  │  │Detector │ │ Detector │ │  Failure  │ │dynamic │  │    │
│  │  └────┬────┘ └────┬─────┘ └─────┬─────┘ └───┬────┘  │    │
│  │       │            │             │           │       │    │
│  │  ┌────┴────────────┴─────────────┴───────────┴────┐  │    │
│  │  │  ┌─────────┐  ┌──────────┐  ┌─────────────┐   │  │    │
│  │  │  │Delirium │  │Electrolyte│  │  Drug-Drug  │   │  │    │
│  │  │  │Detector │  │  Critical │  │ Interaction │   │  │    │
│  │  │  └─────────┘  └──────────┘  └─────────────┘   │  │    │
│  │  └────────────────────────────────────────────────┘  │    │
│  │                                                       │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │  Correlation Engine (multi-domain)            │    │    │
│  │  │  - Sepsis + AKI (sepse é #1 causa de AKI)    │    │    │
│  │  │  - Respiratory + Hemodynamic (SDRA + choque)  │    │    │
│  │  │  - Drug + Electrolyte (QTc + K⁺/Mg²⁺)       │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  TimescaleDB (séries temporais + scores + alertas)   │    │
│  │  Redis (cache de estado, rate limiting, pub/sub)     │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Fontes de Dados por Domínio

| Domínio | AMH Data Platform | Dados Locais (TimescaleDB) | Frequência |
|---------|-------------------|----------------------------|------------|
| Sepse | FHIR Observation (vitals, labs, PCT, culturas) | Vitals streaming (HL7 ORU) | A cada 5 min / on lab result |
| AKI | FHIR Observation (Cr, diurese) | Balanço hídrico horário | A cada 1–6h |
| Respiratória | FHIR Observation (gasometria) | Dados do ventilador (HL7) | A cada 5 min |
| Hemodinâmica | FHIR Observation (lactato) | Monitor invasivo (PA contínua) | Contínua |
| Delirium | FHIR Observation (RASS, CAM-ICU) | Registro de enfermagem | A cada 4–12h |
| Eletrólitos | FHIR Observation (painel eletrolítico) | — | On lab result |
| Drogas | FHIR MedicationRequest / MedicationAdministration | — | On ordem/administração |

---

## 5. Priorização de Implementação

### 5.1 Matriz de Impacto vs. Viabilidade

A priorização considera: (1) evidência clínica robusta, (2) disponibilidade de dados no ecossistema AMH + hospitais brasileiros, (3) complexidade de implementação.

| Prioridade | Domínio | Impacto Clínico | Disponibilidade de Dados | Complexidade |
|------------|---------|-----------------|--------------------------|--------------|
| **P1** | Sepse / Infecção | 🔴 Crítico | Alta (vitals + labs via FHIR) | Média |
| **P2** | AKI (KDIGO) | 🔴 Crítico | Alta (creatinina + diurese) | Baixa |
| **P3** | Emergências Eletrolíticas | 🟠 Alto | Alta (painel lab via FHIR) | Baixa |
| **P4** | Instabilidade Hemodinâmica | 🔴 Crítico | Média (lactato, PA invasiva) | Média |
| **P5** | Insuficiência Respiratória | 🟠 Alto | Média (depende de dados do ventilador) | Média |
| **P6** | Interações Medicamentosas | 🟡 Moderado | Baixa (requer integração completa EMR) | Alta |
| **P7** | Delirium | 🟡 Moderado | Baixa (depende de registro clínico estruturado) | Média |

### 5.2 Cronograma Proposto

| Fase | Duração | Alertas |
|------|---------|---------|
| **Fase 2a** | Meses 1–3 | Sepse (SIRS, qSOFA, lactato) + AKI (KDIGO) + Eletrólitos críticos |
| **Fase 2b** | Meses 4–6 | Hemodinâmica (shock index, clearance lactato) + Respiratória (SpO₂/FiO₂) |
| **Fase 2c** | Meses 7–9 | Interações medicamentosas + Delirium (CAM-ICU triggers) |
| **Fase 2d** | Meses 10–12 | Correlation Engine multi-domínio + ML preditivo (sepse, AKI) |

---

## 6. Desenho de Estudos Clínicos

### 6.1 Estudo Observacional Antes/Depois (Before-After Study)

**Objetivo:** Avaliar o impacto dos alertas inteligentes em desfechos clínicos e operacionais.

**Desenho:**
- **Período controle (3 meses):** Monitoramento convencional (MEWS/NEWS sem alertas Fase 2). Dados coletados retrospectivamente.
- **Período intervenção (3 meses):** Alertas inteligentes Fase 2 ativos com notificação à equipe.
- **Washout:** 2 semanas para treinamento e calibração.

**Desfechos primários:**
- Tempo até antibiótico em sepse (meta: redução de 60 min)
- Tempo até reconhecimento de AKI KDIGO ≥ 1 (meta: redução de 6h)
- Incidência de parada cardíaca por distúrbio eletrolítico (meta: redução de 50%)

**Desfechos secundários:**
- Taxa de alertas acionados vs. confirmados (PPV — Positive Predictive Value)
- Tempo de resposta clínica ao alerta (time-to-action)
- Mortalidade em UTI em 28 dias
- Dias livres de ventilação mecânica
- Dias livres de UTI

**Critérios de inclusão:**
- Pacientes admitidos na UTI com idade ≥ 18 anos
- Permanência prevista > 24h
- Pelo menos 1 conjunto de sinais vitais + 1 resultado laboratorial nas primeiras 24h

**Tamanho amostral estimado:**
- 2 UTIs (30 leitos cada) × 3 meses = ~540 admissões por período
- Poder 80%, α = 0,05 para detectar redução de 20% no tempo-até-antibiótico

**Análise estatística:**
- Variáveis contínuas: teste t pareado ou Mann-Whitney (dependendo da distribuição)
- Variáveis categóricas: qui-quadrado ou Fisher
- Análise de séries temporais interrompidas (ITS) para tendências temporais
- Ajuste por propensity score para confundidores (idade, SAPS 3, comorbidades)

### 6.2 Ensaio Clínico Randomizado em Cluster — Stepped-Wedge

**Objetivo:** Evidência robusta (nível 1) de eficácia dos alertas inteligentes com controle de viés temporal.

**Desenho:**
- **Tipo:** Stepped-wedge cluster randomized controlled trial (SW-CRT)
- **Clusters:** 8 UTIs (4 hospitais, 2 UTIs por hospital)
- **Período total:** 18 meses
- **Steps:** 4 períodos de transição (3 clusters migram para intervenção a cada período)

```
Mês:     1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18
Cluster A: [-- Controle --][------ Intervenção (Alertas) ------]
Cluster B: [-- Controle --][------ Intervenção (Alertas) ------]
Cluster C: [----- Controle -----][------ Intervenção ---------]
Cluster D: [----- Controle -----][------ Intervenção ---------]
Cluster E: [--------- Controle ---------][--- Intervenção ----]
Cluster F: [--------- Controle ---------][--- Intervenção ----]
Cluster G: [-------------- Controle --------------][Intervenção]
Cluster H: [-------------- Controle --------------][Intervenção]
```

**Randomização:** Os clusters são randomizados para o momento de transição (step). Todos começam em controle e todos terminam em intervenção.

**Vantagens do stepped-wedge:**
- Cada cluster serve como seu próprio controle (reduz confundimento)
- Todos os centros recebem a intervenção (ética: não há privação do benefício)
- Efeito temporal (sazonalidade, mudanças de protocolo) é modelado
- Logística de implementação sequencial mais viável que RCT paralelo

**Desfechos primários (hierárquicos):**
1. Tempo até antibiótico adequado em sepse (em horas)
2. Incidência de AKI KDIGO ≥ 2 durante a internação na UTI
3. Eventos adversos graves por distúrbio eletrolítico não reconhecido

**Desfechos secundários:**
- Mortalidade em UTI (28 dias)
- Duração da ventilação mecânica
- Tempo de permanência na UTI
- Carga de alertas (alertas/paciente/dia)
- Taxa de alarm fatigue (alertas ignorados / total de alertas)
- Custos hospitalares (custo total da internação na UTI)

**Tamanho amostral:**
- 8 clusters × ~45 admissões elegíveis/mês × 18 meses = ~6.480 pacientes
- Poder > 90%, α = 0,05 (ajustado para correlação intracluster ICC = 0,02)
- Detecta redução de 25% no desfecho primário composto

**Análise estatística:**
- Modelo linear generalizado misto (GLMM) com efeitos aleatórios para cluster
- Distribuição: Gamma (log-link) para tempo-até-evento, binomial para incidência
- Covariáveis: idade, sexo, SAPS 3, comorbidades, tipo de admissão (clínica/cirúrgica)
- Análise por intenção de tratar (ITT)
- Análise de sensibilidade: per-protocol, ajuste para adesão ao alerta

**Aprovação ética:**
- CEP (Comitê de Ética em Pesquisa) institucional + CONEP (Comissão Nacional de Ética em Pesquisa)
- Registro: ReBEC (Registro Brasileiro de Ensaios Clínicos) e ClinicalTrials.gov
- Consentimento: waiver de consentimento individual (intervenção institucional) com opt-out
- DSMB (Data Safety Monitoring Board) independente com reuniões trimestrais

---

## 7. Métricas de Sucesso

### 7.1 Métricas Clínicas

| Métrica | Baseline (Fase 1) | Meta (Fase 2) |
|---------|-------------------|---------------|
| Sensibilidade para sepse (detecção em < 1h) | 45% (NEWS/qSOFA isolados) | ≥ 80% |
| PPV dos alertas (alertas acionáveis / total) | 35% | ≥ 60% |
| Tempo médio até ação clínica pós-alerta | 42 min | ≤ 15 min |
| Taxa de alarm fatigue (alertas ignorados) | 25% | ≤ 10% |
| Redução de mortalidade em UTI | Baseline | −10% (relativo) |

### 7.2 Métricas Técnicas

| Métrica | Meta |
|---------|------|
| Latência ingestão → alerta (p95) | < 30 segundos |
| Disponibilidade da plataforma | 99,9% |
| Throughput de processamento | > 500 alertas/min |
| Retenção de dados (TimescaleDB) | 7 anos (compliance LGPD/CFM) |
| Versionamento de algoritmos de alerta | 100% auditável |

---

## 8. Conformidade Regulatória (Brasil)

### 8.1 Classificação ANVISA

Alertas inteligentes que **não realizam diagnóstico automático nem substituem julgamento clínico** são classificados como **Software como Dispositivo Médico (SaMD) Classe II** (RDC 657/2022). Isso requer:
- Cadastro ANVISA (não registro pleno)
- Boas Práticas de Fabricação (BPF) — RDC 16/2013
- Rotulagem e instruções de uso em português

### 8.2 LGPD

- Dados de saúde = dados sensíveis (Art. 5º, II)
- Finalidade específica: suporte à decisão clínica (Art. 6º, I)
- Base legal: proteção da vida ou incolumidade física (Art. 7º, VII) + execução de políticas públicas de saúde (Art. 7º, III) se hospital público
- Relatório de Impacto à Proteção de Dados (RIPD) obrigatório

### 8.3 Resolução CFM

- Resolução CFM 2.299/2021: prontuário eletrônico, interoperabilidade
- Alertas devem ser registrados no prontuário do paciente (NGS — Nível de Garantia de Segurança 2)
- O médico continua sendo responsável pela decisão clínica final

---

## 9. Referências

1. **Seymour CW et al.** Assessment of Clinical Criteria for Sepsis. *JAMA*. 2016;315(8):762-774.
2. **Evans L et al.** Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021. *Intensive Care Med*. 2021;47:1181-1247.
3. **KDIGO.** Clinical Practice Guideline for Acute Kidney Injury. *Kidney Int Suppl*. 2012;2(1):1-138.
4. **ARDS Definition Task Force.** Acute Respiratory Distress Syndrome: The Berlin Definition. *JAMA*. 2012;307(23):2526-2533.
5. **Rady MY et al.** A comparison of the shock index and conventional vital signs to identify acute, critical illness. *Ann Emerg Med*. 1994;24(4):685-693.
6. **Ely EW et al.** Delirium in mechanically ventilated patients: validity and reliability of the confusion assessment method for the intensive care unit (CAM-ICU). *NEJM*. 2001;345(14):1013-1020.
7. **Tisdale JE et al.** Development and validation of a risk score to predict QT interval prolongation in hospitalized patients. *Circ Cardiovasc Qual Outcomes*. 2013;6(4):479-487.
8. **Devlin JW et al.** Clinical Practice Guidelines for the Prevention and Management of Pain, Agitation/Sedation, Delirium, Immobility, and Sleep Disruption in Adult Patients in the ICU (PADIS). *Crit Care Med*. 2018;46(9):e825-e873.
9. **Schuetz P et al.** Procalcitonin to initiate or discontinue antibiotics in acute respiratory tract infections. *Cochrane Database Syst Rev*. 2017;10:CD007498.
10. **Jones AE et al.** Lactate clearance vs central venous oxygen saturation as goals of early sepsis therapy. *JAMA*. 2010;303(8):739-746.
