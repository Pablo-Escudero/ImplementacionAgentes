# Backend

API del agente RAG. Organización por responsabilidades:

| Carpeta | Responsabilidad |
|---|---|
| `app/controllers/` | Endpoints HTTP: validan la entrada y delegan en los servicios |
| `app/services/` | Lógica de negocio: usuarios, documentos, conversaciones |
| `app/agents/` | Grafo de LangGraph del agente |
| `app/vectorstore/` | Acceso a la base vectorial (pgvector) |

Archivos de la raíz de `app/`:

| Archivo | Contenido |
|---|---|
| `config.py` | Configuración tipada leída del `.env` o de variables de entorno |
| `database.py` | Motor y sesiones de SQLAlchemy; `init_db()` activa pgvector y crea las tablas |
| `models.py` | Tablas `users`, `documents`, `conversations` y `messages` |
| `main.py` | Aplicación FastAPI y registro de routers |
| `security.py` | Hash de contraseñas con bcrypt y creación y validación de JWT |
| `schemas.py` | Esquemas de entrada y salida (Pydantic) |
| `dependencies.py` | `get_current_user`: valida el token y devuelve el usuario |

Dentro de `app/`, `controllers/auth_controller.py` y `controllers/health_controller.py`
exponen los endpoints, y `services/auth_service.py` contiene el registro y la
autenticación. Las pruebas están en `tests/`.

Los fragmentos y embeddings de los documentos se guardan con PGVector de LangChain
(fase 3), con el id del documento en los metadatos.

Todos los endpoints, incluido `/health`, requerirán autenticación. Solo el registro y
el inicio de sesión son públicos.

Las instrucciones de ejecución están en el [README principal](../README.md).
