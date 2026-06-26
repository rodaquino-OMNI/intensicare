# ADR-001: Intensicare como Consumidor da AMH Data Platform

**Status:** Proposto  
**Data:** 26/06/2026  
**Autor:** Parreira (Hermes DevOps Orchestrator)  
**Stakeholders:** CTO Office, Time de Engenharia AMH

---

## Contexto

O Intensicare é uma plataforma de suporte à decisão clínica para UTI que precisa de dados clínicos (sinais vitais, labs, dados demográficos de pacientes) para calcular scores de risco e gerar alertas.

A Americas Health já mantém a **AMH Data Platform** (`Omni-Saude/amh-data-platform`), um lakehouse multi-tenant healthcare-grade em AWS (sa-east-1) que provê:

- Ingestão CDC de fontes transacionais (Tasy ERP, OMNI, Diagnose) via Debezium → MSK → Flink
- Lakehouse Apache Iceberg com arquitetura medallion (Raw → Bronze → Silver-Rules → Silver-Entities → Gold)
- Master Patient Index (MPI) com linking determinístico e probabilístico
- Servidor FHIR R4 (HAPI FHIR) para interoperabilidade clínica
- Observabilidade (AMP + Grafana + OTEL)
- Segurança multi-tenant (KMS por tenant, IAM ABAC, Lake Formation)

## Decisão

**O Intensicare será projetado como consumidor especializado da AMH Data Platform, não como uma plataforma de dados paralela.**

### Implicações

1. **Ingestão de dados:** O Intensicare NÃO implementará ingestão própria (NiFi, Kafka, Debezium). Lerá dados clínicos do Gold layer da AMH Data Platform via Amazon Athena.

2. **Identidade do paciente:** O Intensicare usará o `mpi_id` do MPI existente. Não criará identificadores próprios de paciente.

3. **Storage operacional:** O Intensicare manterá um banco PostgreSQL/TimescaleDB próprio para estado operacional (scores calculados, alertas ativos, configurações de thresholds). Estes são dados de aplicação, não dados analíticos.

4. **Storage analítico:** Scores históricos e agregados serão gravados de volta ao Gold layer da AMH Data Platform como fatos analíticos (`fact_patient_score`, `fact_alert`), permitindo analytics corporativo.

5. **FHIR:** O Intensicare consumirá dados clínicos via HAPI FHIR existente quando precisar de contexto enriquecido. Não operará seu próprio servidor FHIR.

6. **Observabilidade:** Métricas e traces serão emitidos via OpenTelemetry para o stack AMP + Grafana existente.

7. **Segurança:** O Intensicare herdará o modelo de segurança da AMH Data Platform (IAM Identity Center para SSO, KMS por tenant para criptografia, ABAC via Lake Formation para acesso a dados).

8. **Deploy:** O Intensicare será deployado em ECS Fargate na mesma VPC e contas AWS da AMH Data Platform, alinhado ao padrão corporativo.

## Alternativas consideradas

### Alternativa A: Plataforma independente (stack próprio de ingestão e storage)

**Prós:** Autonomia total, sem dependência da AMH Data Platform.  
**Contras:** Duplicação de infraestrutura (Kafka, Flink, Iceberg, MPI, FHIR), custo 3-5x maior, inconsistência de dados entre plataformas, equipe de engenharia fragmentada.

**Decisão:** Rejeitada. A AMH Data Platform já é a fonte canônica de verdade para dados clínicos. Duplicar é antieconômico e arquiteturalmente inconsistente.

### Alternativa B: Híbrido (ingestão própria + storage compartilhado)

**Prós:** Menor latência para dados de UTI (não depende do pipeline batch da AMH DP).  
**Contras:** Complexidade de manter dois pipelines de ingestão, risco de divergência de dados.

**Decisão:** Rejeitada para MVP. Pode ser reconsiderada na Fase 4 se a latência do pipeline batch da AMH DP (P95 < 30 min para Silver-Entities) for insuficiente para o caso de uso de UTI. Nesse caso, um canal de streaming dedicado (MSK topic adicional) poderia alimentar o Intensicare diretamente.

## Consequências

- O time do Intensicare precisa de acesso ao Athena, Glue Data Catalog e Lake Formation da AMH Data Platform
- O schema de dados de entrada do Intensicare é definido pelas tabelas Gold da AMH Data Platform
- Mudanças no schema Gold da AMH Data Platform são breaking changes para o Intensicare e devem ser versionadas
- O Intensicare herda os SLOs da AMH Data Platform para disponibilidade de dados (99,5% analytics)

## Referências

- [SAD da Plataforma de Dados AMH](https://github.com/Omni-Saude/amh-data-platform/blob/main/architecture/sad/SAD-AMH-Plataforma-Dados.md)
- [Medallion Lakehouse — AMH Data Platform](https://github.com/Omni-Saude/amh-data-platform/blob/main/docs/concepts/medallion-lakehouse.md)
- [Reference Architecture — AMH Data Platform](https://github.com/Omni-Saude/amh-data-platform/blob/main/architecture/diagrams/reference-architecture/reference-architecture.md)
