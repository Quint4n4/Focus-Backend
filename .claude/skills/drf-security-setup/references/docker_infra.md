# Docker e Infraestructura Segura — Referencia Completa

## docker-compose.prod.yml — Configuración completa

```yaml
version: '3.9'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: .env.production
    environment:
      - DEBUG=0
      - DJANGO_SETTINGS_MODULE=config.settings.production
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application
             --bind 0.0.0.0:8000
             --workers 4
             --timeout 120
             --access-logfile -
             --error-logfile -"
    expose:
      - "8000"          # Solo expone a la red interna, no al host
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:1.25-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_volume:/staticfiles:ro
      - media_volume:/mediafiles:ro
    depends_on:
      - web
    networks:
      - app-network

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file: .env.production
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data/
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    # SIN 'ports:' — la DB NO está accesible desde el exterior
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --save 60 1000
    volumes:
      - redis_data:/data
    # SIN 'ports:' — Redis NO expuesto al exterior
    networks:
      - app-network

networks:
  app-network:
    driver: bridge    # Red privada aislada

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

## Nginx — Configuración segura con SSL

```nginx
# nginx/nginx.conf
upstream django {
    server web:8000;
}

# Redirigir HTTP → HTTPS
server {
    listen 80;
    server_name api.tudominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.tudominio.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Protocolos seguros (TLS 1.2 y 1.3 únicamente)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDH+AESGCM:ECDH+AES256:ECDH+AES128:!DH:!ECDSA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Headers de seguridad
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Ocultar versión de nginx
    server_tokens off;

    # Rate limiting a nivel nginx (primera línea de defensa)
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_req zone=api burst=20 nodelay;

    client_max_body_size 10M;
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;

    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_connect_timeout 10s;
        proxy_read_timeout 30s;
    }

    location /static/ {
        alias /staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Bloquear acceso a archivos sensibles
    location ~ /\. {
        deny all;
    }

    location ~ \.(env|git|sql|log)$ {
        deny all;
    }
}
```

## Dockerfile seguro

```dockerfile
# Dockerfile
FROM python:3.12-slim AS base

# Usuario no-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Instalar dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements/production.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r production.txt

# Copiar código
COPY --chown=appuser:appuser . .

# Cambiar al usuario no-root
USER appuser

# Puerto
EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

## .gitignore crítico

```gitignore
# Secretos — NUNCA en git
.env
.env.*
!.env.example
*.pem
*.key
ssl/
secrets/

# Python
__pycache__/
*.py[cod]
*.so
.Python
venv/
.venv/

# Django
*.log
local_settings.py
db.sqlite3
staticfiles/
mediafiles/
```
