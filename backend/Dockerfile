FROM python:3.12.16-slim

WORKDIR /app

# Install system dependencies needed for compiling certain packages or postgres checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ejecutar como usuario sin privilegios (evita que un RCE en el proceso
# obtenga root dentro del contenedor). UID/GID 1000 para que coincida con el
# propietario del volumen bind-mounted del host (compose.yml monta
# ../core-casmarts/data/authentik/custom-templates, propiedad de un usuario
# host con uid/gid 1000) — necesario para que /deploy pueda escribir flow.html.
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --home /app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
