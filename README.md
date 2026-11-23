# Turnos EPS — Integración Continua, Grupo 10

Plataforma de asignación de turnos para una EPS: el paciente ingresa su
cédula y el sistema le asigna un código de turno (`A-001`, `A-002`, …).

Este repositorio cubre la **Entrega 1 (semana 3)** del proyecto *Proyecto
de software basado en herramientas de integración continua*: dos
contenedores Docker comunicados entre sí.

- Contenedor **web** (`turnos_web`): aplicación Flask con Python 3.12.
- Contenedor **db** (`turnos_db`): base de datos PostgreSQL 16.

La aplicación ya persistía los turnos en PostgreSQL. No se modificó el
código de `app/app.py`. La tabla `turnos` se crea sola al arrancar, así
que no hace falta un script SQL de inicialización.

## Cómo ejecutar con Docker

### Requisitos

- Docker Engine y Docker Compose v2 (el complemento `docker compose`).

### Arranque

Desde la raíz del repositorio:

```bash
# Opcional: ajustar usuario, contraseña, base de datos o puerto
cp .env.example .env

# Construir las imágenes y levantar los dos contenedores
docker compose up --build
```

Para dejarlos en segundo plano:

```bash
docker compose up --build -d
```

Cuando el servicio `web` esté en estado healthy, abrir en el navegador:

- Pedir un turno: <http://localhost:5000>
- Pantalla de turnos: <http://localhost:5000/turnos>
- Administración (pasar al siguiente turno): <http://localhost:5000/admin>

La cédula debe tener solo dígitos y entre 5 y 12 caracteres.

### Cómo se comunican los contenedores

Ambos se unen a la red bridge `turnos_red`, declarada en
`docker-compose.yml`. Dentro de esa red, el hostname del servicio de
base de datos es `db`.

La aplicación lee esas coordenadas de las variables de entorno
`DB_HOST`, `DB_USER`, `DB_PASSWORD` y `DB_NAME`. `DB_HOST` vale `db`,
así que Flask se conecta a PostgreSQL por el nombre del otro servicio,
sin exponer el puerto 5432 al computador anfitrión.

`web` espera a que el healthcheck de `db` (`pg_isready`) marque el
servicio como healthy antes de arrancar (`depends_on` con
`condition: service_healthy`). Los datos de PostgreSQL se guardan en el
volumen `datos_db`.

### Comprobar que un turno quedó en la base de datos

Con los contenedores en marcha:

```bash
# Asignar un turno de prueba (debe devolver un 302 hacia /?codigo=A-001)
curl -sS -D - -o /dev/null -X POST http://localhost:5000/pedir \
  -d "cedula=123456789"

# Ver el registro en el contenedor de PostgreSQL
docker compose exec db psql -U turnos -d turnos -c "SELECT * FROM turnos;"
```

Para ver el estado y los registros de ambos servicios:

```bash
docker compose ps
docker compose logs
```

### Detener

```bash
docker compose down
```

Para borrar también el volumen de la base de datos (se pierden los turnos
guardados):

```bash
docker compose down -v
```

## Entrega 2 (semana 5): integración continua con Jenkins

Jenkins actúa como gestor de operaciones: cada cambio en `main` dispara el
pipeline definido en el `Jenkinsfile` de la raíz.

| Etapa | Qué hace |
|---|---|
| Checkout | Descarga el commit desde GitHub. |
| Análisis estático y pruebas unitarias | `flake8` + `pytest` (9 pruebas en `tests/`, sin base de datos, con reporte JUnit). |
| Construir imágenes Docker | `docker compose build --pull`. |
| Desplegar entorno de prueba | Levanta `web` y `db` con nombres únicos por build (`docker-compose.ci.yml`) y espera a que estén healthy. |
| Prueba de humo (web ↔ db) | `scripts/smoke_test.sh`: HTTP 200, pedir turno (302 con código), fila en PostgreSQL, `/turnos` y `/admin`. |
| Post | Guarda logs y reportes como artefactos y baja los contenedores (`down -v`). |

### Levantar Jenkins

```bash
cd jenkins
cp .env.example .env          # cambiar JENKINS_ADMIN_PASSWORD y DOCKER_GID
stat -c %g /var/run/docker.sock   # valor para DOCKER_GID
docker compose up -d --build
```

Abrir <http://localhost:8080> e ingresar con el usuario de `.env`. La
configuración como código (`jenkins/casc/jenkins.yaml`) crea el usuario
administrador y el job `turnos-eps-ci`, que lee el `Jenkinsfile` de este
repositorio. Los plugins están en `jenkins/plugins.txt`.

### Ejecutar lo mismo sin Jenkins

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r app/requirements.txt -r requirements-dev.txt
flake8 app tests && pytest -q
export COMPOSE_PROJECT_NAME=turnos-ci-local COMPOSE_FILE=docker-compose.yml:docker-compose.ci.yml APP_PORT=5050
docker compose up -d --build --wait
./scripts/smoke_test.sh turnos-ci-local
docker compose down -v
```
