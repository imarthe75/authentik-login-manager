# 🌌 Contexto del Agente Residente (CONTEXT.md)

Este framework está diseñado para levantar agentes autónomos que coexisten en el host local de forma segura y autorregulada.

## 🎯 Propósito
El propósito del Agente Residente es servir como un operador inteligente con continuidad y memoria permanente entre sesiones. No es un script stateless que se destruye tras ejecutarse; es una entidad cognitiva que lee su historial, aprende de sus fallas pasadas (a través de la memoria semántica en Postgres) y optimiza sus respuestas gracias a la caché semántica (Valkey).

## 🛠️ Tecnologías Enlazadas
- **ECC (Embedded Cognitive Control):** Diseñado para mantener el control interno y verificación del agente antes y después de cada acción en el código.
- **LangGraph & Valkey:** Orquestación de flujos de trabajo asíncronos y persistencia del grafo de estados en memoria de corto plazo de Valkey.
- **Valkey Semantic Cache:** Caché inteligente basada en similitud de embeddings para entregar respuestas ultra-rápidas a consultas repetitivas de LLMs.
- **Postgres pgvector:** Memoria semántica persistente en disco local.
- **MCP (Model Context Protocol):** La pasarela segura para interactuar con herramientas del sistema operativo.
