# Fila de Revisão Regulatória e Clínica — Intensicare

> **Legenda de status:** `DRAFT` → `PENDING_REVIEW` → `IN_PROGRESS` → `APPROVED`
>
> Atualizado em: 26 de junho de 2026

---

## 📋 Itens Regulatórios Obrigatórios (Pré-Produção)

| # | Artefato | Status | Responsável | Previsão | Notas |
|---|----------|--------|-------------|----------|-------|
| 1 | **ANVISA SaMD Classification** | DRAFT | Consultoria externa | Q3 2026 | Classificação preliminar: Classe II (risco similar III). Contratar consultoria especializada. |
| 2 | **LGPD RIPD (Relatório de Impacto)** | DRAFT | DPO / Time jurídico | Q3 2026 | Dados de saúde = sensíveis (Art. 11). Base legal: proteção da vida (inciso II, "g"). |
| 3 | **SBIS Certification Plan** | DRAFT | Arquiteto de sistemas | Q4 2026 | Certificação primária para interoperabilidade no Brasil. |
| 4 | **Clinical Validation Protocol** | DRAFT | Time clínico | Q3 2026 | Protocolo de validação para scores MEWS/NEWS2/SOFA/qSOFA contra gold-standard. |
| 5 | **Pentest Report** | DRAFT | Empresa externa | Q4 2026 | Teste de penetração externo antes do go-live. |
| 6 | **Intended Use Statement** | DRAFT | Diretor médico + time | Q3 2026 | Declaração de uso pretendido (obrigatório ANVISA para SaMD). |

---

## 🟢 Itens Técnicos (Pós-Implementação)

| # | Item | Status | Notas |
|---|------|--------|-------|
| T1 | **Tabela audit_trail** | IMPLEMENTADO | Trilha de auditoria imutável via trigger no banco. |
| T2 | **Idempotência de ingestão** | IMPLEMENTADO | Via `X-Idempotency-Key` (MSH-10). IdempotencyStore em memória (dev), Redis planejado (prod). |
| T3 | **Versionamento de algoritmos** | IMPLEMENTADO | Coluna `algorithm_version` em `clinical_score`. |
| T4 | **Criptografia em repouso** | PENDENTE | `pgcrypto` para PHI (nome, CPF, CNS) — não implementado ainda. |
| T5 | **Health check + Dead man's switch** | PARCIAL | `/health` implementado. Dead man's switch externo pendente. |
| T6 | **Retry com backoff** | PENDENTE | ARQ ou similar para notificações assíncronas. |
| T7 | **HTTPS/TLS em produção** | PENDENTE | Caddy planejado como reverse proxy com TLS automático. |
| T8 | **Keycloak/OAuth2** | PENDENTE | MVP usa JWT simples. Migrar para Keycloak na Fase 2. |

---

## 📊 Status do MVP (Fase 1)

| Funcionalidade | Status | Cobertura de Testes |
|---------------|--------|:---:|
| Ingestão HL7 v2 (MLLP Listener) | ✅ Funcional | ✅ |
| Cálculo MEWS | ✅ Funcional | ✅ |
| Cálculo NEWS2 | ✅ Funcional | ✅ |
| Cálculo SOFA | ✅ Funcional | ✅ |
| Cálculo qSOFA | ✅ Funcional | ✅ |
| Alertas via threshold config | ✅ Funcional | ✅ |
| Rate limiting (Redis) | ✅ Funcional | ✅ |
| Cooldown de alertas | ✅ Funcional | ✅ |
| Dashboard de leitos (API) | ✅ Funcional | ✅ |
| Dashboard de leitos (Frontend React) | ✅ Funcional | — |
| Autenticação JWT | ✅ Funcional | ✅ |
| WebSocket (alertas real-time) | ✅ Funcional | ✅ |
| Patient Detail (histórico 24h) | ✅ Funcional | ✅ |

---

## 🟡 Próximos Passos (Fase 2)

| Item | Prioridade |
|------|:----------:|
| Integração com HAPI FHIR (AMH Data Platform) | Alta |
| Prometheus metrics (`/metrics`) | Média |
| ARQ task queue para notificações assíncronas | Média |
| Web Push notifications (mobile) | Baixa |
| Gravação de scores no Gold layer (AMH) | Média |
| Grafana dashboards clínicos | Baixa |

---

## 🔴 Bloqueios Imediatos

1. **Consultoria ANVISA não contratada** — Bloqueia classificação formal do SaMD e registro.
2. **RIPD não elaborado** — Obrigatório para conformidade com LGPD antes de processar dados reais.
3. **`audit_trail` não implementado** — Invariante arquitetural #1; obrigatório antes de dados de pacientes reais.
4. **_Nenhum_ teste com dados reais de hospital** — Necessário piloto com 48h de tráfego HL7 real para validação clínica.

> **Atualizado pela última vez:** 26 de junho de 2026
