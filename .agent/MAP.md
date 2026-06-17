# 🗺️ Mapeo del Framework (MAP.md)

Este documento define la estructura y dependencias de la infraestructura del framework.

## 📂 Estructura de Directorios

```
resident-agent-framework/
├── .agent/
│   ├── AGENT.md        # Leyes y reglas del agente
│   ├── CONTEXT.md      # Propósito y tecnologías enlazadas
│   ├── MAP.md          # Este mapa técnico
│   ├── STATE.md        # Estado actual y bitácora del agente
│   └── HEURISTICS.md   # Heurística cognitiva y toma de decisiones por IA
├── DECISIONS/
│   ├── 0001-genesis.md            # ADR de decisiones arquitectónicas iniciales
│   └── 0002-heuristics-mandate.md # ADR de adopción obligatoria de heurísticas
├── memory/
│   ├── semantic_cache.py          # Lógica de caché semántica con Valkey
│   ├── long_term_memory.py        # Lógica de embeddings con pgvector en Postgres
│   └── agent_state.py             # Grafo de memoria interactiva (LangGraph)
├── skills/
│   └── example_mcp_skill.py       # Plantilla de herramientas MCP integradas
├── docker-compose.yml             # Orquestación de infraestructura local
├── HEURISTICAS_MASTER_GUIDE.md    # Guía Maestra de Heurísticas (Teoría y Práctica)
├── README.md                      # Guía de inicio rápido para desarrolladores
```

## 🔋 Recursos del Host y Puertos

| Servicio | Puerto Interno | Puerto Host | Volumen Local | Propósito |
| :--- | :---: | :---: | :--- | :--- |
| **Valkey** | `6379` | `6379` | `./data/valkey` | Memoria de corto plazo y caché semántica |
| **PostgreSQL** | `5432` | `5432` | `./data/postgres` | Memoria semántica de largo plazo (pgvector) |
