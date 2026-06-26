# Intensicare — Product Vision

> Extraído e adaptado do README original (Julho 2025), expandido com contexto da AMH Data Platform.

## O que é o Intensicare

O Intensicare é uma plataforma de suporte à decisão clínica para unidades de terapia intensiva (UTI). Ele monitora continuamente sinais vitais e dados laboratoriais de pacientes, calcula scores de risco em tempo real (MEWS, SOFA, qSOFA, NEWS2), e entrega alertas contextualizados para equipes clínicas.

O Intensicare opera como **consumidor especializado da AMH Data Platform** — a infraestrutura de dados corporativa da Americas Health que provê ingestão, lakehouse, identidade longitudinal de pacientes (MPI) e interoperabilidade FHIR R4.

## Por que o Intensicare existe

Em UTIs, a deterioração clínica pode ocorrer em minutos. Sistemas de early warning tradicionais sofrem de:

- **Fadiga de alertas:** muitos falsos positivos dessensibilizam a equipe
- **Cálculo manual:** scores como MEWS são frequentemente calculados à mão, com atraso e erro
- **Dados fragmentados:** sinais vitais em um sistema, labs em outro, sem visão integrada
- **Falta de contexto:** alertas sem o histórico completo do paciente

O Intensicare resolve isso com scoring automatizado em tempo real, alimentado pelo lakehouse de dados clínicos da AMH.

## Público-alvo

| Persona | Necessidade principal |
|---------|----------------------|
| **Médico intensivista** | Visão consolidada de scores e tendências de todos os pacientes da UTI |
| **Enfermeiro de UTI** | Alertas acionáveis no ponto de cuidado, sem overload |
| **Coordenador de UTI** | Métricas de desempenho da unidade, tempo de resposta a alertas |
| **Equipe de resposta rápida** | Notificações mobile para deterioração aguda |
| **Gestor hospitalar** | Dashboards de qualidade clínica e ocupação |

## Funcionalidades-alvo (MVP)

1. **Leitura de sinais vitais** do Gold layer da AMH Data Platform (via Athena)
2. **Cálculo automatizado de scores clínicos:**
   - MEWS (Modified Early Warning Score)
   - NEWS2 (National Early Warning Score 2)
3. **Alertas baseados em thresholds** configuráveis por unidade/tenant
4. **Dashboard clínico web** com visão de leitos e scores
5. **Histórico de scores** por paciente, com tendências

## Funcionalidades-alvo (Pós-MVP)

6. SOFA e qSOFA scoring
7. WebSocket para alertas em tempo real
8. Integração com HAPI FHIR para contexto clínico enriquecido
9. Modelo preditivo de sepse (ML)
10. App mobile para equipes de resposta rápida
11. Gravação de scores de volta ao Gold layer para analytics corporativo

## Métricas de sucesso (a validar com hospital parceiro)

| Métrica | Alvo |
|---------|------|
| Tempo entre coleta de vitals e score disponível | < 30 segundos |
| Tempo entre score crítico e notificação | < 5 segundos |
| Taxa de adoção pela equipe clínica | > 80% em 3 meses |
| Redução de cálculos manuais de score | > 90% |
| Satisfação da equipe (NPS) | > 50 |

## O que o Intensicare NÃO é

- **Não é um sistema de EHR/Prontuário Eletrônico.** Ele consome dados de EHRs, não os substitui.
- **Não é uma plataforma de ingestão de dados.** A AMH Data Platform já faz isso.
- **Não é um dispositivo médico regulado (inicialmente).** O MVP é suporte à decisão — não toma decisões clínicas automaticamente.
- **Não substitui o julgamento clínico.** Scores são ferramentas de apoio, não diagnósticos.

## Contexto estratégico

O Intensicare é parte da estratégia "Operadora do Futuro" da Americas Health, que inclui:

- **AMH Data Platform:** fundação de dados (lakehouse, MPI, FHIR)
- **Agentes IA:** Tina (atendimento), Evah (enfermagem digital), Jair (regulação)
- **Maezo:** orquestrador de processos clínicos FHIR
- **Intensicare:** camada de inteligência clínica para ambiente hospitalar

---

*Adaptado do README original (Julho 2025) por Parreira, Junho 2026.*
