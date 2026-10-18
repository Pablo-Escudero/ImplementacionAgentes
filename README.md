# Agente RAG sobre Cyberpunk 2077

Backend de un agente inteligente que responde preguntas sobre la franquicia
Cyberpunk 2077 (videojuego, Phantom Liberty, Edgerunners y material relacionado)
a partir de una base de conocimiento propia almacenada en una base de datos vectorial.

El agente se construye con **LangChain** y **LangGraph**, usa un modelo de lenguaje
**local con Ollama** y responde únicamente con la información recuperada de la base
vectorial. Cuando no hay contexto suficiente, rechaza la pregunta de forma explícita.

> Estado: **fase 2** (autenticación con JWT). Las demás fases se
> documentan aquí a medida que se completan.

## Estructura

```
implementacionAgentes/
├── backend/
│   ├── app/
│   │   ├── agents/        # grafo de LangGraph
│   │   ├── controllers/   # endpoints de la API
│   │   ├── services/      # lógica de negocio
│   │   └── vectorstore/   # acceso a pgvector
│   ├── requirements.txt
│   └── README.md
├── docs/                  # diagrama de arquitectura y capturas
├── docker-compose.yml     # PostgreSQL + pgvector
├── .env.example
└── README.md
```

La carpeta `frontend/` la desarrolla otra parte del equipo y se agregará al repo después.

## Requisitos

- Python 3.11 o superior
- Docker Desktop
- Ollama (modelos `qwen2.5:3b` y `bge-m3`)

## Ejecución local (Windows, PowerShell)

1. Crear el entorno virtual e instalar dependencias:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r backend/requirements.txt
   ```

2. Crear la configuración local:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edita `.env` y cambia al menos `JWT_SECRET`.

3. Levantar la base de datos:

   ```powershell
   docker compose up -d
   ```

   La base queda en `localhost:5433` (el puerto 5433 evita chocar con un PostgreSQL
   local instalado en el 5432).

4. Instalar los modelos locales con Ollama:

   ```powershell
   ollama pull qwen2.5:3b
   ollama pull bge-m3
   ```

5. Arrancar el backend (con el entorno virtual activo):

   ```powershell
   cd backend
   uvicorn app.main:app --reload
   ```

   Al arrancar, la app activa la extensión `vector` y crea las tablas `users`,
   `documents`, `conversations` y `messages` si no existen.

## Autenticación

La API usa tokens JWT (Bearer). Solo `POST /auth/register` y `POST /auth/login` son
públicos; el resto de endpoints, incluido `GET /health`, exigen un token válido.

| Endpoint | Acceso | Descripción |
|---|---|---|
| `POST /auth/register` | Público | Crea un usuario (`email` y `password` de 8 a 72 bytes) |
| `POST /auth/login` | Público | Formulario OAuth2 (`username` = correo, `password`); devuelve el token |
| `GET /auth/me` | Token | Datos del usuario autenticado |
| `GET /health` | Token | Estado del servicio y de la base de datos |

El token dura `ACCESS_TOKEN_EXPIRE_MINUTES` (60 por defecto). Para cerrar sesión, el
cliente descarta el token. Con `ENABLE_DOCS=true`, Swagger queda en
`http://127.0.0.1:8000/docs` (botón **Authorize** para probar con un usuario).

## Pruebas

```powershell
cd backend
python -m pytest
```

## Plan de trabajo

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Esqueleto del repo, configuración y base de datos | Hecha |
| 1 | Configuración, conexión y tablas | Hecha |
| 2 | Autenticación (registro, login, JWT) | Hecha |
| 3 | Vectorstore, carga y procesamiento de documentos | Pendiente |
| 4 | Agente LangGraph | Pendiente |
| 5 | Endpoints de chat e historial | Pendiente |
| 6 | Carga inicial de la base de conocimiento | Pendiente |
| 7 | Docker del backend y despliegue en AWS | Pendiente |
| 8 | Pruebas, README completo y diagrama de arquitectura | Pendiente |
