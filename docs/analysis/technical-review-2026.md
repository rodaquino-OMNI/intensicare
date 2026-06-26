# 🔬 Análise Técnica Completa — Intensicare

**Data:** 26 de junho de 2026  
**Analista:** Parreira (Hermes DevOps Orchestrator)  
**Repositório:** `rodaquino-OMNI/intensicare` (público)  
**Commit analisado:** `9311688` — `Update README.md` (02/07/2025)  
**Conteúdo real:** 1 arquivo — `README.md` (669 linhas, ~22 KB)

---

# 1. Executive Summary

O repositório `intensicare` **não contém código-fonte, infraestrutura, configurações, modelos de dados, testes, ou qualquer artefato técnico funcional**. Consiste em um único arquivo `README.md` que descreve, em linguagem de produto acabado, uma plataforma de monitoramento de UTI que não existe.

O README é um **bom documento de visão de produto** — articula propósito claro, arquitetura aspiracional, stack moderno, APIs REST/FHIR e requisitos de compliance. No entanto, está redigido como se a plataforma já estivesse implementada, contendo comandos (`docker-compose up -d`, `kubectl apply`, `helm install`, `terraform apply`) e endpoints de API sem implementação correspondente.

**Uma descoberta fundamental desta análise:** A Americas Health já está implantando a **AMH Data Platform** (`Omni-Saude/amh-data-platform`) — um lakehouse multi-tenant healthcare-grade em AWS (sa-east-1) com Apache Iceberg, streaming CDC via Kafka/Flink, servidor FHIR R4 (HAPI), Master Patient Index (MPI) e observabilidade completa. **O Intensicare deve ser projetado para operar SOBRE esta plataforma de dados corporativa, não como um sistema isolado.**

**Veredito:** O repositório deve ser **redesenhado a partir de uma fundação técnica limpa**, aproveitando o README como ponto de partida para o Product Requirements Document (PRD) e a AMH Data Platform como infraestrutura de dados-alvo.

---

# 2. Repository Diagnosis

| Dimensão | Constatação |
|----------|-------------|
| **Conteúdo real** | 1 arquivo: `README.md` (669 linhas, 22 KB) |
| **Código-fonte** | Nenhum. Zero linhas de código em qualquer linguagem |
| **Configurações** | Nenhuma. Sem `docker-compose.yml`, `Dockerfile`, `Makefile`, `.env`, `helm charts`, `terraform` |
| **Testes** | Nenhum |
| **Docs além do README** | Nenhuma |
| **Histórico de commits** | 1 commit único (`Update README.md`) |
| **Branches** | Apenas `main` |
| **Licença** | Não declarada |
| **Maturidade** | **Pré-concept** — equivale a um documento Google Docs exportado ao GitHub |
| **Criado em** | 02/07/2025 (há ~1 ano, sem atualizações) |

---

# 3. Key Findings

## 3.1 Product Vision & Scope

### Forças
- Visão clara e clinicamente relevante: monitoramento contínuo de UTI com scores MEWS, SOFA, qSOFA, NEWS2
- Público-alvo bem definido: intensivistas, enfermeiros, equipes de resposta rápida
- Fluxos clínicos descritos fazem sentido para o domínio

### Fraquezas
- Escopo excessivamente amplo para MVP (12+ componentes de infraestrutura)
- Sem priorização — tudo apresentado como igualmente importante
- **Sem personas, user stories ou critérios de aceitação**
- Claims de validação clínica sem evidência ("15% reduction in ICU mortality")

## 3.2 Technical Architecture

### Stack descrito no README (aspiracional)
NiFi → Kafka → Flink + ONNX → TimescaleDB → FastAPI → K8s + Linkerd + Keycloak + Vault + Prometheus/Grafana + ELK

### Stack recomendado para MVP (integrado à AMH Data Platform)
FastAPI (monólito modular) → Amazon Athena sobre Gold Iceberg + PostgreSQL/TimescaleDB local para estado operacional → Redis para cache de scores

**Justificativa:** A AMH Data Platform já provê ingestão, streaming, storage, catálogo, MPI, FHIR e observabilidade. O Intensicare deve ser um **consumidor especializado** dessa plataforma, não duplicá-la.

## 3.3 Relationship with AMH Data Platform (CRÍTICO)

A **AMH Data Platform** é a infraestrutura de dados corporativa da Americas Health. O Intensicare **deve** ser projetado para integrar-se a ela:

| Capacidade | Onde reside | Implicação para Intensicare |
|-----------|-------------|-----------------------------|
| **Ingestão de dados** | AMH Data Platform (Debezium CDC, DMS, API connectors) | Intensicare NÃO precisa de NiFi/Kafka próprios — consome dados do lakehouse |
| **Identidade do paciente** | MPI na AMH Data Platform | Intensicare usa `mpi_id` existente, não cria identificadores próprios |
| **Armazenamento** | S3 + Apache Iceberg (camadas Bronze→Silver→Gold) | Scores clínicos podem ser persistidos como fatos no Gold layer |
| **FHIR** | HAPI FHIR R4 já operacional | Intensicare expõe dados via FHIR existente ou consome FHIR para contexto clínico |
| **Observabilidade** | AMP + Grafana + OTEL | Intensicare emite métricas/traces para o stack existente |
| **Segurança** | KMS por tenant, IAM SSO, ABAC via Lake Formation | Intensicare herda o modelo de segurança da plataforma |
| **Multi-tenancy** | Isolamento por tenant em todas as camadas | Intensicare respeita isolamento — scores de tenant A não vazam para tenant B |

## 3.4 Healthcare & Regulatory Context

### Contexto brasileiro totalmente ausente
- ❌ **LGPD** não mencionada (Lei Geral de Proteção de Dados — aplicável, não HIPAA)
- ❌ **ANVISA RDC 657/2022** — classificação SaMD (Software as Medical Device) não avaliada
- ❌ **CFM** — Resoluções sobre telemedicina e sistemas de apoio à decisão clínica não consideradas
- ❌ **ANS/TISS** — Troca de Informação em Saúde Suplementar não abordada
- ✅ **FHIR R4 e HL7 v2** mencionados (correto para interoperabilidade)

### Nota sobre a AMH Data Platform
A plataforma de dados já endereça LGPD (consent management, DPIA, right-to-erasure, data retention) e ANS/TISS (pipelines de compliance regulatório). O Intensicare pode **herdar** essas proteções.

## 3.5 Documentation Quality

| Documento | Existe? |
|-----------|:------:|
| README.md (visão de produto) | ✅ |
| Product Requirements Document | ❌ |
| Architecture Decision Records | ❌ |
| API Reference (OpenAPI real) | ❌ |
| Data Model / ERD | ❌ |
| Setup Guide funcional | ❌ |
| Security & Compliance | ❌ |
| Clinical Validation Protocol | ❌ |
| License | ❌ |

---

# 4. Critical Gaps

| # | Gap | Severidade | Impacto |
|---|-----|:--------:|---------|
| 1 | **Zero código implementado** | 🔴 Crítico | O projeto não existe tecnicamente |
| 2 | **Sem integração com a AMH Data Platform** | 🔴 Crítico | Risco de arquitetura duplicada e inconsistente com a estratégia corporativa |
| 3 | **Claims clínicos sem fundamento** | 🔴 Crítico | Risco regulatório e reputacional |
| 4 | **Contexto brasileiro ausente** (LGPD, ANVISA, CFM, ANS) | 🔴 Crítico | Inviabiliza adoção no mercado-alvo |
| 5 | **README enganoso** — comandos/endpoints inexistentes | 🟠 Alto | Confunde stakeholders e devs |
| 6 | **Arquitetura superdimensionada** (12+ componentes) | 🟠 Alto | Complexidade mata o projeto antes da primeira feature |
| 7 | **Sem licença** | 🟠 Alto | Impossibilita uso legal e contribuições |
| 8 | **Sem dados de teste** | 🟡 Médio | Impede validação de conceitos |

---

# 5. Proposed Target Architecture (Integrada à AMH Data Platform)

```
┌──────────────────────────────────────────────────────────────────┐
│                    AMH DATA PLATFORM (já existente)               │
│                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │  Bronze   │──▶│  Silver   │──▶│   Gold    │──▶│ Athena (SQL) │  │
│  │ (Iceberg) │   │ (Iceberg) │   │ (Iceberg) │   │  workgroups  │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘  │
│                                          │                        │
│  ┌──────────┐   ┌──────────┐            │                        │
│  │   MPI     │   │   FHIR    │           │                        │
│  │ (patients)│   │ (HAPI R4) │           │                        │
│  └──────────┘   └──────────┘            │                        │
│                                          │                        │
│  ┌──────────────────────────────────────┐│                        │
│  │  Observabilidade (AMP + Grafana + OTEL)                       │
│  │  Segurança (KMS tenant + IAM + ABAC)                          │
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
                           │
                           │ Consome dados via Athena + FHIR
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    INTENSICARE (a construir)                       │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                    API Layer (FastAPI)                        ││
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   ││
│  │  │ Vitals       │  │ Scoring      │  │ Alert            │   ││
│  │  │ Service      │  │ Engine       │  │ Engine           │   ││
│  │  │ (read from   │  │ (MEWS, SOFA, │  │ (rules +         │   ││
│  │  │  Gold layer) │  │  NEWS2, qSOFA)│  │  notification)  │   ││
│  │  └─────────────┘  └──────────────┘  └──────────────────┘   ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  PostgreSQL 14 + TimescaleDB                                  ││
│  │  (estado operacional: scores calculados, alertas,            ││
│  │   configurações de thresholds por tenant)                     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Redis                                                         ││
│  │  (cache de scores recentes, pub/sub para WebSocket alerts)    ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Clinical Dashboard (React / Next.js)                         ││
│  │  Mobile PWA (Responsive Web)                                  ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Por que esta arquitetura?

1. **Não duplica o que já existe.** A AMH Data Platform já ingere dados do Tasy, processa CDC via Kafka/Flink, mantém o lakehouse Iceberg com camadas medallion, gerencia identidade longitudinal via MPI, e expõe interoperabilidade via FHIR R4.

2. **Intensicare é um consumidor especializado.** Lê dados clínicos do Gold layer (via Athena), calcula scores, e escreve resultados como fatos no próprio Gold ou em seu banco operacional.

3. **PostgreSQL/TimescaleDB para estado operacional.** Scores, alertas e configurações de thresholds são estado quente que precisa de baixa latência. TimescaleDB é otimizado para séries temporais (vitals ao longo do tempo).

4. **Redis para real-time.** Cache de scores recentes e pub/sub para notificações WebSocket aos dashboards clínicos.

5. **Herda observabilidade.** Métricas e traces são emitidos via OTEL para o AMP/Grafana já existente.

---

# 6. Stack Comparison: README vs Recomendado

| Componente | README (aspiracional) | Recomendado (integrado) | Justificativa |
|-----------|----------------------|------------------------|---------------|
| **Ingestão** | Apache NiFi | AMH Data Platform (Debezium + DMS) | Já implementado corporativamente |
| **Streaming** | Apache Kafka | AMH Data Platform (MSK Serverless) | Já implementado |
| **Processamento** | Apache Flink + ONNX | FastAPI background tasks | Flink já existe na AMH DP para CDC→FHIR |
| **Storage analítico** | TimescaleDB | AMH Data Platform (S3 + Iceberg) | Gold layer já existe |
| **Storage operacional** | — | PostgreSQL 14 + TimescaleDB | Scores, alertas, thresholds |
| **Cache/Broker** | — | Redis | Real-time scores + WebSocket pub/sub |
| **API** | FastAPI + WebSockets | FastAPI + WebSockets | ✅ Manter |
| **Orquestração** | Kubernetes + Helm | Docker Compose (MVP), ECS Fargate (prod) | Alinhado com stack AMH |
| **Auth** | Keycloak | IAM Identity Center (já existe) | SSO corporativo unificado |
| **Observabilidade** | Prometheus + Grafana + ELK | AMP + AMG + OTEL (já existe) | Stack corporativo unificado |
| **FHIR** | — (mencionado) | HAPI FHIR (já existe) | Canal clínico corporativo |
| **ML** | ONNX | Amazon Bedrock (já provisionado) | Claude para agentes IA |

---

# 7. Codebase Decision

| Classificação | Componente | Justificativa |
|:---:|------------|---------------|
| 📝 **Keep (como doc)** | `README.md` | Manter como documento de visão, após adicionar disclaimer de status real |
| 🔄 **Refactor** | `README.md` | Transformar em `docs/product/vision.md` |
| 🆕 **Create** | Todo o código, configs, testes, dados | Criar do zero, integrado à AMH Data Platform |

---

# 8. Development Roadmap

## Fase 0: Fundação (Semanas 1-2)
- [ ] Adicionar disclaimer de status real no README
- [ ] Adicionar licença (AGPLv3 ou proprietária alinhada à AMH)
- [ ] Criar estrutura de diretórios
- [ ] Criar PRD baseado no README atual
- [ ] ADR-001: Decisão de integrar com AMH Data Platform (não duplicar ingestão/streaming)
- [ ] Setup de desenvolvimento com Docker Compose (API + PostgreSQL + Redis)
- [ ] Conectar ao Athena da AMH Data Platform para leitura de dados

## Fase 1: MVP Core (Semanas 3-8)
- [ ] Implementar leitura de vitals do Gold layer via Athena
- [ ] Implementar scoring engine: MEWS, NEWS2
- [ ] Implementar alert engine baseado em thresholds configuráveis
- [ ] Implementar autenticação via IAM Identity Center (SSO corporativo)
- [ ] Criar fixtures de dados sintéticos
- [ ] Criar testes unitários e de integração
- [ ] Dashboard web mínimo: visão de leitos com scores

## Fase 2: Interoperabilidade & Expansão (Semanas 9-14)
- [ ] Integrar com HAPI FHIR para contexto clínico enriquecido
- [ ] Adicionar SOFA e qSOFA scoring
- [ ] WebSocket para alertas em tempo real
- [ ] Gravar scores calculados de volta ao Gold layer (para analytics)
- [ ] Métricas via OTEL → AMP → Grafana

## Fase 3: Produção (Semanas 15-20)
- [ ] Deploy em ECS Fargate (alinhado à stack AMH)
- [ ] CI/CD com GitHub Actions
- [ ] Testes de carga e performance
- [ ] DR e backup alinhados à estratégia da AMH Data Platform
- [ ] Documentação de operação

## Fase 4: ML & Advanced (Semanas 21+)
- [ ] Modelo de predição de sepse (treinamento em dados do lakehouse)
- [ ] Inferência via Bedrock ou SageMaker
- [ ] Validação clínica formal com hospital parceiro
- [ ] Classificação ANVISA (se aplicável como SaMD)

---

# 9. Final Verdict

### O repositório deve ser continuado como está?
**Não.** É um documento de visão disfarçado de projeto implementado.

### O que deve ser feito?
**Redesenhar a partir de uma fundação técnica limpa, integrada à AMH Data Platform.**

O Intensicare tem mérito como conceito — monitoramento inteligente de UTI é uma necessidade real no mercado brasileiro. O problema não é a ideia, mas o gap entre a visão documentada e a realidade do repositório.

**O caminho correto:**

1. Transformar o README atual em `docs/product/vision.md`
2. Criar um novo README honesto sobre o estágio real do projeto
3. Criar PRD formal com personas, user journeys e critérios de aceitação
4. Projetar o Intensicare como **consumidor especializado da AMH Data Platform**
5. Começar com um monólito modular (FastAPI + PostgreSQL + Redis)
6. Subir para ECS Fargate quando pronto para produção (alinhado ao stack AMH)

**A AMH Data Platform é o ativo estratégico.** O Intensicare deve ser uma aplicação clínica que opera sobre essa fundação, não uma plataforma paralela competindo por recursos de engenharia.

---

*Análise conduzida por Parreira (Hermes DevOps Orchestrator) com consulta ao repositório `Omni-Saude/amh-data-platform` como referência de arquitetura corporativa.*
