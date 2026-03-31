# OWASP Top 10 2025 — Checklist para DRF

## A01 — Broken Access Control (riesgo #1)
- [ ] `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` — nunca AllowAny por defecto
- [ ] Verificar ownership en cada endpoint (el usuario solo accede a sus datos)
- [ ] UUID como PKs — evita enumeración de objetos
- [ ] `read_only_fields` para is_admin, is_staff, is_superuser en todos los serializers
- [ ] django-guardian para permisos a nivel de objeto cuando se necesite

## A02 — Security Misconfiguration (riesgo #2)
- [ ] `DEBUG=False` en producción
- [ ] `python manage.py check --deploy` sin warnings críticos
- [ ] Browsable API desactivada (solo JSONRenderer)
- [ ] CORS con lista blanca estricta
- [ ] Todos los headers de seguridad configurados

## A03 — Cryptographic Failures
- [ ] HTTPS forzado en toda la comunicación
- [ ] Contraseñas hasheadas con PBKDF2/Argon2 (Django por defecto)
- [ ] SECRET_KEY de mínimo 50 chars aleatorios
- [ ] JWT_SECRET_KEY separado del SECRET_KEY
- [ ] Campos sensibles encriptados en DB si aplica (django-secured-fields)

## A04 — Insecure Design
- [ ] Throttling por scope en endpoints críticos
- [ ] Rate limiting en Nginx como primera capa
- [ ] django-axes o django-defender activo
- [ ] Honeypots configurados

## A05 — Injection (SQL, XSS, etc.)
- [ ] Usar siempre el ORM de Django — nunca raw() o cursor.execute() con input de usuario
- [ ] Validación explícita en cada campo de cada serializer
- [ ] Nunca eval(), exec() con datos del usuario
- [ ] CSP headers configurados

## A06 — Vulnerable Components
- [ ] `safety check` en CI/CD para detectar dependencias vulnerables
- [ ] `pip list --outdated` revisado periódicamente
- [ ] Imágenes Docker escaneadas con Trivy

## A07 — Identification and Authentication Failures
- [ ] JWT con vida corta (15 min access, 7 días refresh)
- [ ] Rotación de refresh tokens activada
- [ ] Blacklist de tokens al logout
- [ ] django-axes/defender activo
- [ ] Política de contraseñas configurada (AUTH_PASSWORD_VALIDATORS)

## A08 — Software and Data Integrity
- [ ] Dependencias con versiones fijadas en requirements.txt
- [ ] No cargar código de fuentes externas no verificadas

## A09 — Security Logging and Monitoring Failures
- [ ] Logging de intentos fallidos de login
- [ ] Logging de accesos a honeypots
- [ ] SensitiveDataFilter activo — logs sin tokens ni passwords
- [ ] Sentry configurado para errores de producción
- [ ] Alertas por número anormal de errores 401/403

## A10 — Server-Side Request Forgery (SSRF)
- [ ] No hacer requests a URLs proporcionadas por el usuario
- [ ] Validar y sanitizar cualquier URL que Django necesite consultar
- [ ] Whitelist de dominios si se necesita consumir APIs externas
