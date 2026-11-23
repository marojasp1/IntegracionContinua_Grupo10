#!/usr/bin/env bash
# Prueba de humo contra los contenedores reales (web + db) ya levantados.
# Uso: scripts/smoke_test.sh [nombre-proyecto-compose]
# Se ejecuta dentro de los contenedores con "docker compose exec", así
# funciona igual en un portátil que dentro de Jenkins.
set -euo pipefail
PROYECTO="${1:-${COMPOSE_PROJECT_NAME:-turnos}}"
DC="docker compose -p ${PROYECTO}"
CEDULA="9$(date +%s | tail -c 9)"   # cédula de prueba única por ejecución

echo "== 1. Estado de los servicios"
${DC} ps

echo "== 2. La app responde HTTP 200 en /"
${DC} exec -T web python - <<'PY'
import urllib.request
r = urllib.request.urlopen("http://127.0.0.1:5000/", timeout=5)
assert r.status == 200, r.status
print("OK / ->", r.status)
PY

echo "== 3. Pedir un turno con la cédula ${CEDULA} (debe redirigir con código)"
${DC} exec -T -e CEDULA="${CEDULA}" web python - <<'PY'
import os, urllib.parse, urllib.request
class SinRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None
op = urllib.request.build_opener(SinRedir)
datos = urllib.parse.urlencode({"cedula": os.environ["CEDULA"]}).encode()
try:
    op.open("http://127.0.0.1:5000/pedir", data=datos, timeout=5)
    raise SystemExit("Se esperaba una redirección 302")
except urllib.error.HTTPError as e:
    assert e.code == 302, e.code
    loc = e.headers["Location"]
    assert "codigo=A-" in loc, loc
    print("OK /pedir -> 302", loc)
PY

echo "== 4. El turno quedó guardado en PostgreSQL (comunicación web -> db)"
FILAS=$(${DC} exec -T db psql -U turnos -d turnos -tAc \
  "SELECT count(*) FROM turnos WHERE cedula='${CEDULA}';")
echo "Filas para ${CEDULA}: ${FILAS}"
[ "${FILAS}" = "1" ] || { echo "FALLO: se esperaba 1 fila"; exit 1; }

echo "== 5. Pantalla de turnos y administración responden"
${DC} exec -T web python -c "import urllib.request as u; [print('OK', p, u.urlopen('http://127.0.0.1:5000'+p, timeout=5).status) for p in ('/turnos','/admin')]"

echo "PRUEBA DE HUMO SUPERADA"
