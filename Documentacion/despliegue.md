# Despliegue

## Stack de produccion

- App: Django + Gunicorn (`web`).
- Reverse proxy: Nginx (`nginx`).
- DB: PostgreSQL (`db`).
- Cache/rate auxiliar: Redis (`redis`).
- Orquestacion: `docker-compose.production.yml`.

## Variables de entorno minimas

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL` o (`DB_NAME`, `DB_USER`, `DB_PASSWORD` segun compose)
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS`

## Flujo recomendado

1. Construir imagen:
```bash
docker-compose -f docker-compose.production.yml build
```
2. Levantar servicios:
```bash
docker-compose -f docker-compose.production.yml up -d
```
3. Ejecutar migraciones:
```bash
docker-compose -f docker-compose.production.yml exec web python manage.py migrate
```
4. Crear superusuario:
```bash
docker-compose -f docker-compose.production.yml exec web python manage.py createsuperuser
```

## Endpoints expuestos

- Publico: Nginx `80/443`.
- Interno: servicio `web` en `8000` solo expuesto a la red docker (`expose`, no `ports`).

## Seguridad de despliegue ya implementada

- TLS 1.2/1.3 en Nginx.
- Redireccion HTTP -> HTTPS.
- Security headers en Nginx.
- Rate limiting por endpoint y global en Nginx.
- `SECURE_SSL_REDIRECT`, HSTS, CSP y cookies seguras en settings de produccion.

## Verificaciones post-deploy

- `GET /api/auth/me/` responde `401` sin token.
- `POST /api/auth/login/` aplica `429` al exceder limite.
- Logs activos en volumen `log_files`.
- `collectstatic` completado.
