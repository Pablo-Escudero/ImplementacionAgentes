# Despliegue del backend en AWS EC2

Arquitectura: el navegador llama a `https://<dominio>` (Caddy, HTTPS automático) → backend FastAPI →
PostgreSQL + pgvector en el mismo servidor. El modelo (Ollama) corre en el PC del autor y el servidor
lo alcanza por una red privada de **Tailscale**; no se expone ningún puerto de Ollama a internet.

```
Navegador ──HTTPS──> EC2 (Caddy :443) ──> backend :8000 ──> db (pgvector)
                                              │
                                              └──Tailscale (100.x.x.x:11434)──> Ollama en el PC
```

Comandos de las partes A y D: PowerShell en Windows. Partes B: consola web de AWS. Parte C: SSH al servidor (Ubuntu).

## Parte A. En tu PC

### A1. Tailscale
1. Instala Tailscale (tailscale.com/download) e inicia sesión con tu cuenta de Google o GitHub.
2. Anota la IP de tu PC (empieza por `100.`):
   ```powershell
   tailscale ip -4
   ```

### A2. Que Ollama acepte conexiones desde Tailscale
```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")
```
Cierra Ollama (icono de la bandeja → Quit) y ábrelo de nuevo. Comprueba que escucha en todas las interfaces:
```powershell
netstat -ano | findstr 11434
```
Debe aparecer `0.0.0.0:11434` en estado LISTENING.

### A3. Firewall de Windows: solo la red de Tailscale
PowerShell **como administrador**:
```powershell
New-NetFirewallRule -DisplayName "Ollama via Tailscale" -Direction Inbound -Protocol TCP -LocalPort 11434 -RemoteAddress 100.64.0.0/10 -Action Allow -Profile Any
```
Si Windows pregunta por `ollama.exe` al reiniciarlo, no marques "redes públicas".

### A4. Copia de la base de conocimiento (con tu base local encendida)
Desde la raíz del repo:
```powershell
docker compose exec -T db sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists --no-owner --no-privileges | gzip > /tmp/kb.sql.gz'
docker compose cp db:/tmp/kb.sql.gz $HOME\Downloads\kb.sql.gz
(Get-Item $HOME\Downloads\kb.sql.gz).Length
```
El tamaño debe ser de varios MB. Se guarda en Descargas, **fuera del repo**: contiene tu usuario y su hash de contraseña. No lo subas a GitHub.

## Parte B. Consola de AWS

### B1. Lanzar la instancia (EC2 → Launch instance)
- Nombre: `cyberpunk-backend`
- Imagen: **Ubuntu Server 24.04 LTS** (x86_64)
- Tipo: **t3.small** (2 GB de RAM). Si tu plan no la deja elegir, avísame.
- Key pair: *Create new key pair*, RSA, `.pem`. Se descarga una vez; guárdala.
- Network settings → *Edit* → grupo de seguridad nuevo con:
  - SSH (22): origen **My IP**
  - HTTP (80): Anywhere
  - HTTPS (443): Anywhere
- Almacenamiento: **20 GiB** gp3.

Si tu IP cambia (otra red), edita la regla de SSH del grupo de seguridad.

### B2. IP elástica
EC2 → *Elastic IPs* → *Allocate Elastic IP address* → *Associate* a la instancia. Anota la IP.

### B3. Subdominio en DuckDNS
1. Entra a duckdns.org con tu cuenta y crea un subdominio (por ejemplo `cyberpunk-api`).
2. En el campo *current ip* pon la IP elástica y pulsa *update ip*.
3. Comprueba: `nslookup cyberpunk-api.duckdns.org` debe devolver esa IP.

## Parte C. En el servidor

### C1. Entrar por SSH
Windows exige permisos estrictos sobre la `.pem`:
```powershell
icacls $HOME\Downloads\TU-CLAVE.pem /inheritance:r
icacls $HOME\Downloads\TU-CLAVE.pem /grant:r "$($env:USERNAME):R"
ssh -i $HOME\Downloads\TU-CLAVE.pem ubuntu@IP-ELASTICA
```

### C2. Swap, Docker y Tailscale
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
`tailscale up` imprime una URL: ábrela en tu PC e inicia sesión con **la misma cuenta** de Tailscale.
Luego `exit` y vuelve a entrar por SSH para que aplique el grupo `docker`.

### C3. Comprobar que el servidor llega a tu Ollama (con tu PC encendido)
```bash
curl -s http://IP-TAILSCALE-DE-TU-PC:11434/api/tags
```
Debe listar `qwen2.5:3b` y `bge-m3`. Si no responde:
- Sin respuesta: Tailscale desconectado en el PC, Ollama sin reiniciar tras A2, o regla de firewall (A3).
- `403` o *forbidden*: Ollama rechaza el encabezado Host. Usa el plan B de abajo.

### C4. Código y configuración
```bash
git clone https://github.com/Pablo-Escudero/ImplementacionAgentes.git
cd ImplementacionAgentes
cp deploy/env.production.example .env
python3 -c "import secrets; print('PG_PASSWORD=' + secrets.token_hex(24))"
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
nano .env
```
En `.env` pega las dos líneas generadas y ajusta `DOMAIN` (tu subdominio completo) y `OLLAMA_BASE_URL`
(`http://100.x.y.z:11434` con la IP de Tailscale de tu PC). Deja `ENABLE_DOCS=false` y `CORS_ORIGINS=` vacío por ahora.
Guarda con Ctrl+O, Enter, Ctrl+X.

### C5. Restaurar la base de conocimiento
En tu PC, copia el dump al servidor:
```powershell
scp -i $HOME\Downloads\TU-CLAVE.pem $HOME\Downloads\kb.sql.gz ubuntu@IP-ELASTICA:~/
```
En el servidor:
```bash
docker compose -f docker-compose.prod.yml up -d --build db
gunzip -c ~/kb.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d cyberpunk_agent -v ON_ERROR_STOP=1 -q
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d cyberpunk_agent -c "SELECT (SELECT count(*) FROM documents) AS documentos, (SELECT count(*) FROM langchain_pg_embedding) AS fragmentos;"
```
Esperado: unos 79-80 documentos y al menos 1719 fragmentos.

### C6. Levantar todo
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=40 backend caddy
```
El primer build tarda unos minutos. Caddy pide el certificado cuando llega la primera petición por HTTPS.

## Parte D. Verificación (desde tu PC)
Cambia `SUB` por tu subdominio completo.
```powershell
curl.exe -i https://SUB/health        # esperado: 401 (protegido)
curl.exe -i https://SUB/docs          # esperado: 404 (Swagger apagado)
$t = curl.exe -s -X POST https://SUB/auth/login -d "username=pabloescuderov12@gmail.com&password=TU_CLAVE" | ConvertFrom-Json
$h = @{ Authorization = "Bearer $($t.access_token)" }
$b = [Text.Encoding]::UTF8.GetBytes('{"question":"¿Quién es Johnny Silverhand?"}')
Invoke-RestMethod -Method Post -Uri https://SUB/chat -Headers $h -ContentType "application/json; charset=utf-8" -Body $b
$b = [Text.Encoding]::UTF8.GetBytes('{"question":"What is the capital of France?"}')
Invoke-RestMethod -Method Post -Uri https://SUB/chat -Headers $h -ContentType "application/json; charset=utf-8" -Body $b
```
Esperado: la primera responde con fuentes (`answered: True`) y la segunda rechaza (`answered: False`).

## Operación

- **Antes de la sustentación:** PC encendido y sin suspensión, Tailscale conectado, Ollama abierto. Haz una pregunta de calentamiento: la primera carga de los modelos es lenta.
- **Poner CORS cuando tengas la URL del front:** edita `CORS_ORIGINS` en `.env` y ejecuta `docker compose -f docker-compose.prod.yml up -d --force-recreate backend`.
- **Actualizar el código:** `git pull && docker compose -f docker-compose.prod.yml up -d --build backend`.
- **Ver consumo de memoria:** `docker stats --no-stream`.
- **Error 502 en `/chat`:** el backend no alcanza Ollama (PC apagado, Tailscale caído o Ollama cerrado).
- **Caddy no obtiene certificado:** revisa `docker compose -f docker-compose.prod.yml logs caddy`. Causas típicas: el dominio aún no apunta a la IP elástica, o los puertos 80/443 no están abiertos en el grupo de seguridad.

## Plan B: Ollama por túnel de Cloudflare (si Tailscale falla)
En tu PC (con `cloudflared` instalado):
```powershell
cloudflared tunnel --url http://localhost:11434 --http-host-header="localhost:11434"
```
Copia la URL `https://....trycloudflare.com` que imprime y ponla en `OLLAMA_BASE_URL` del `.env` del servidor; luego
`docker compose -f docker-compose.prod.yml up -d --force-recreate backend`. Esa URL es pública y cambia cada vez que
reinicias el túnel.
