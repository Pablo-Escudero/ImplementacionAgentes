# Cyberpunk RAG Agent

Aplicacion web de tipo agente inteligente construida con FastAPI, LangChain y LangGraph. El agente responde preguntas en espanol e ingles sobre la franquicia Cyberpunk (Cyberpunk 2077, Phantom Liberty, Edgerunners, comics y juego de rol de mesa), fundamentando sus respuestas exclusivamente en una base de conocimiento vectorial local (PostgreSQL + pgvector) y utilizando un modelo de lenguaje local ejecutado con Ollama.

Integrantes: [Nombre Integrante 1], [Nombre Integrante 2]

## Arquitectura del Sistema

El flujo de la aplicacion es el siguiente:
1. Frontend (React) se comunica con el Backend (FastAPI).
2. El backend gestiona la autenticacion (JWT), la carga de documentos y el historial.
3. El Agente (LangGraph) procesa la pregunta, recupera contexto de la base vectorial, valida la informacion y genera una respuesta.
4. El Modelo Local (Ollama) ejecuta el LLM (qwen2.5:3b) y los embeddings (bge-m3).
5. La Base de Datos (PostgreSQL + pgvector) almacena los fragmentos vectorizados.

El diagrama detallado se encuentra en docs/arquitectura.png.

## Tecnologias Utilizadas

- Backend: Python 3.11, FastAPI, SQLAlchemy, PyJWT, Bcrypt.
- Agente: LangChain, LangGraph, Ollama (qwen2.5:3b para chat, bge-m3 para embeddings).
- Base de Datos: PostgreSQL 17 con extension pgvector (Docker).
- Despliegue: AWS (Backend), DuckDNS, Tunel SSH (para conectar con Ollama local).
- Frontend: [Mencionar tecnologia del frontend, ej. React / Next.js].

## Ejecucion Local

### Prerrequisitos
- Python 3.11
- Docker Desktop
- Ollama instalado y ejecutandose.
- Git

### Pasos

1. Clonar el repositorio:
   git clone https://github.com/Pablo-Escudero/ImplementacionAgentes.git
   cd ImplementacionAgentes

2. Configurar el entorno virtual e instalar dependencias:
   python -m venv .venv
   En Windows:
   .venv\Scripts\activate
   En Linux/Mac:
   source .venv/bin/activate
   
   pip install -r backend/requirements.txt

3. Descargar los modelos en Ollama:
   ollama pull qwen2.5:3b
   ollama pull bge-m3

4. Levantar la base de datos vectorial (PostgreSQL):
   docker-compose up -d
   Esto levantara el contenedor en el puerto 5434 (mapeado al 5432 interno).

5. Configurar las variables de entorno:
   Copia el archivo .env.example a .env en la raiz del proyecto y ajusta los valores si es necesario.
   cp .env.example .env

6. Cargar la base de conocimiento inicial (opcional si la BD ya tiene datos):
   cd backend
   python -m scripts.load_knowledge_base

7. Ejecutar el backend:
   cd backend
   python -m uvicorn app.main:app --reload --port 8001
   La API estara disponible en http://localhost:8001. La documentacion Swagger estara en /docs (si ENABLE_DOCS=True).

## Despliegue en la Nube

El backend esta desplegado en AWS y es accesible publicamente en:
URL del Backend: https://cyberpunk-api.duckdns.org

Nota sobre el despliegue:
Debido a que el modelo de lenguaje se ejecuta localmente (Ollama) por limitaciones de recursos en la capa gratuita de AWS, el backend en la nube se conecta a traves de un tunel SSH seguro al Ollama que corre en la maquina local del equipo. Por lo tanto, para que el backend publico funcione, el tunel debe estar activo.

### Variables de Entorno en Produccion (AWS)
Las variables configuradas en el servicio de AWS son las mismas que en .env.example, pero apuntando a la base de datos y al tunel correspondiente.

## Estrategias Anti-Alucinacion

El agente implementa cuatro capas de seguridad para evitar inventar informacion:
1. Filtro de Intencion (Blocklist + LLM): Valida si la pregunta pertenece al dominio de Cyberpunk antes de buscar en la base de datos.
2. Umbral de Similitud (grade_context): Solo se utilizan fragmentos recuperados con un score de similitud coseno mayor a 0.5.
3. Prompt Estricto: El modelo tiene prohibido usar conocimiento externo y debe responder con el marcador NO_INFO si el contexto no es suficiente.
4. Nodo de Rechazo Explicito: Si el modelo devuelve NO_INFO o el contexto no supera el umbral, el agente responde exactamente con: "No tengo suficiente informacion en mi base de conocimiento para responder esa pregunta."

## Estructura del Repositorio

proyecto-agente/
  backend/
    app/
      agents/          Grafo LangGraph, prompts e idioma
      controllers/     Endpoints de la API (auth, chat, docs)
      services/        Logica de negocio
      vectorstore/     Configuracion de pgvector
      config.py        Configuracion de variables de entorno
      models.py        Modelos SQLAlchemy
      main.py          Punto de entrada FastAPI
    scripts/           Scripts de carga y diagnostico
    requirements.txt
  frontend/            Codigo del frontend
  docs/
    arquitectura.png   Diagrama de arquitectura
    capturas/          Evidencias de funcionamiento
  docker-compose.yml   PostgreSQL + pgvector
  .env.example         Ejemplo de variables de entorno
  README.md

## Capturas de Pantalla

Asegurese de incluir imagenes en la carpeta docs/capturas/ y enlazarlas aqui:
- Inicio de sesion.
- Chat con respuesta fundamentada y fuentes.
- Rechazo de pregunta fuera de dominio.
- Carga de documento.
