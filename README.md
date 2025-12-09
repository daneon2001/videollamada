# Videollamada Python

Servicio FastAPI + Socket.IO para telemedicina con colas de espera, asignación de médicos y métricas.

## Requisitos

- Python 3.11+
- PostgreSQL accesible según variables en `.env`
- Entorno virtual activado (`python -m venv .venv && .venv\Scripts\activate`)

Instala dependencias:

```bash
pip install -r requirements.txt
```

## Migraciones (Alembic)

1. Configura tu `.env` (usuario, password, host, DB).
2. Ejecuta:

```bash
alembic upgrade head
```

Esto crea todas las tablas (`users`, `rooms`, `calls`, `participants`) y enums requeridos.

### Crear nuevas migraciones

```bash
alembic revision --autogenerate -m "mensaje descriptivo"
alembic upgrade head
```

Alembic usa `app.db.DATABASE_URL`, por lo que toma los valores de `.env`.

## Seeders

Para crear usuarios iniciales (doctor/paciente demo) ejecuta:

```bash
python scripts/seed_initial_data.py
```

Variables opcionales (puedes definirlas en `.env` o antes de ejecutar):

- `DEFAULT_DOCTOR_EMAIL` / `DEFAULT_DOCTOR_PASSWORD` / `DEFAULT_DOCTOR_NAME`
- `DEFAULT_PATIENT_EMAIL` / `DEFAULT_PATIENT_PASSWORD` / `DEFAULT_PATIENT_NAME`

Si los usuarios ya existen, el script los omite.

## Desarrollo local

```bash
scripts\run_dev.bat
```

Sirve la API en `http://127.0.0.1:8100` (ajusta `public/config.js` o tus variables front-end para apuntar a la misma base URL).

## Scripts útiles

- `scripts/run_dev.bat`: levanta uvicorn con autoreload.
- `scripts/seed_initial_data.py`: crea usuarios base.
- `scripts/migrate.bat` (opcional, crea uno si lo necesitas) o usa `alembic` directamente.

## Verificación rápida

- `GET /health` para comprobar servicio.
- `POST /auth/register` para registrar usuarios adicionales.
- `POST /auth/token` para obtener bearer token.
- `GET /calls/waiting` (doctor) y `POST /calls/request` (paciente) para flujo de videollamada.
