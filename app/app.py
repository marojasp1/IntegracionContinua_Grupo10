import os
import time

import psycopg2
from flask import Flask, redirect, render_template_string, request, url_for

app = Flask(__name__)

# ---------- Base de datos ----------


def conectar():
    """Abre una conexión con PostgreSQL. 'db' es el nombre del servicio
    en docker-compose.yml: así un contenedor encuentra al otro."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        user=os.environ.get("DB_USER", "turnos"),
        password=os.environ.get("DB_PASSWORD", "turnos123"),
        dbname=os.environ.get("DB_NAME", "turnos"),
    )


def iniciar_tabla():
    """Crea la tabla de turnos si todavía no existe."""
    con = None
    for _ in range(10):
        try:
            con = conectar()
            break
        except psycopg2.OperationalError:
            time.sleep(2)
    if con is None:
        raise RuntimeError("No se pudo conectar a la base de datos")
    with con, con.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS turnos (
                id SERIAL PRIMARY KEY,
                cedula VARCHAR(15) NOT NULL,
                estado VARCHAR(12) NOT NULL DEFAULT 'esperando',
                creado TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
    con.close()


def codigo(id_turno):
    """Convierte el id en el código del ficho: 1 -> A-001."""
    return f"A-{id_turno:03d}"


# ---------- Páginas ----------

ESTILO = (
    "body{font-family:Arial,sans-serif;max-width:480px;margin:40px auto;"
    "padding:0 16px;text-align:center}"
    "input,button{font-size:18px;padding:10px;margin:6px}"
    ".ficho{font-size:48px;font-weight:bold;color:#0b6e4f}"
    ".aviso{color:#b00020}"
)


def pagina(cuerpo, **datos):
    html = (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Turnos EPS</title><style>" + ESTILO + "</style></head>"
        "<body><h1>Turnos EPS</h1>" + cuerpo + "</body></html>"
    )
    return render_template_string(html, **datos)


INICIO = """
<form method="post" action="/pedir">
  <input name="cedula" placeholder="Número de cédula" inputmode="numeric" required>
  <button>Pedir turno</button>
</form>
{% if mensaje %}<p class="aviso">{{ mensaje }}</p>{% endif %}
{% if codigo %}<p>Tu turno es</p><p class="ficho">{{ codigo }}</p>{% endif %}
<p><a href="/turnos">Ver pantalla de turnos</a></p>
"""

TURNOS = """
<h2>Atendiendo</h2>
<p class="ficho">{{ atendiendo or '—' }}</p>
<h2>En espera</h2>
{% if esperando %}
  <ul style="list-style:none;padding:0;font-size:24px">
  {% for t in esperando %}<li>{{ t }}</li>{% endfor %}
  </ul>
{% else %}<p>No hay turnos en espera.</p>{% endif %}
<script>setTimeout(function(){ location.reload(); }, 5000);</script>
"""

ADMIN = """
<h2>Administración</h2>
<p>Atendiendo: <b>{{ atendiendo or '—' }}</b></p>
<p>En espera: <b>{{ en_espera }}</b></p>
<form method="post" action="/siguiente"><button>Siguiente ⏭️</button></form>
<p><a href="/turnos">Ver pantalla de turnos</a></p>
"""


@app.route("/")
def inicio():
    return pagina(
        INICIO,
        mensaje=request.args.get("mensaje"),
        codigo=request.args.get("codigo"),
    )


@app.route("/pedir", methods=["POST"])
def pedir():
    cedula = request.form.get("cedula", "").strip()
    if not cedula.isdigit() or not 5 <= len(cedula) <= 12:
        return redirect(
            url_for("inicio", mensaje="Escribe una cédula válida (solo números).")
        )

    con = conectar()
    with con, con.cursor() as cur:
        # Una cédula no puede tener dos turnos activos al mismo tiempo
        cur.execute(
            "SELECT id FROM turnos WHERE cedula = %s "
            "AND estado IN ('esperando', 'atendiendo')",
            (cedula,),
        )
        existente = cur.fetchone()
        if existente:
            id_turno, es_nuevo = existente[0], False
        else:
            cur.execute(
                "INSERT INTO turnos (cedula) VALUES (%s) RETURNING id", (cedula,)
            )
            id_turno, es_nuevo = cur.fetchone()[0], True
    con.close()

    mensaje = None if es_nuevo else "Ya tenías un turno activo."
    return redirect(url_for("inicio", codigo=codigo(id_turno), mensaje=mensaje))


def estado_actual():
    """Devuelve (código del turno en atención, lista de códigos en espera)."""
    con = conectar()
    with con, con.cursor() as cur:
        cur.execute(
            "SELECT id FROM turnos WHERE estado = 'atendiendo' "
            "ORDER BY id DESC LIMIT 1"
        )
        fila = cur.fetchone()
        atendiendo = codigo(fila[0]) if fila else None
        cur.execute("SELECT id FROM turnos WHERE estado = 'esperando' ORDER BY id")
        esperando = [codigo(f[0]) for f in cur.fetchall()]
    con.close()
    return atendiendo, esperando


@app.route("/turnos")
def turnos():
    atendiendo, esperando = estado_actual()
    return pagina(TURNOS, atendiendo=atendiendo, esperando=esperando)


@app.route("/admin")
def admin():
    atendiendo, esperando = estado_actual()
    return pagina(ADMIN, atendiendo=atendiendo, en_espera=len(esperando))


@app.route("/siguiente", methods=["POST"])
def siguiente():
    con = conectar()
    with con, con.cursor() as cur:
        # El turno que estaba en atención termina...
        cur.execute(
            "UPDATE turnos SET estado = 'finalizado' WHERE estado = 'atendiendo'"
        )
        # ...y el más antiguo de la fila pasa a atención
        cur.execute(
            """
            UPDATE turnos SET estado = 'atendiendo'
            WHERE id = (
                SELECT id FROM turnos WHERE estado = 'esperando'
                ORDER BY id LIMIT 1
            )
            """
        )
    con.close()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    iniciar_tabla()
    app.run(host="0.0.0.0", port=5000)