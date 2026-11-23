"""Pruebas unitarias de la app de turnos.

No necesitan PostgreSQL: la conexión se reemplaza por un doble de prueba
(mock), así Jenkins puede ejecutarlas en segundos antes de construir las
imágenes. La prueba con la base de datos real la hace scripts/smoke_test.sh.
"""
from unittest import mock

import pytest

import app as turnos


@pytest.fixture
def cliente():
    turnos.app.config["TESTING"] = True
    with turnos.app.test_client() as c:
        yield c


def conexion_falsa(filas):
    """Devuelve una conexión simulada cuyo cursor entrega `filas` en orden."""
    cur = mock.MagicMock()
    cur.fetchone.side_effect = filas
    con = mock.MagicMock()
    con.cursor.return_value.__enter__.return_value = cur
    return con, cur


def test_codigo_formatea_con_tres_digitos():
    assert turnos.codigo(1) == "A-001"
    assert turnos.codigo(42) == "A-042"
    assert turnos.codigo(1234) == "A-1234"


def test_inicio_muestra_formulario(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "Pedir turno" in r.get_data(as_text=True)


@pytest.mark.parametrize("cedula", ["", "abc123", "1234", "1234567890123", "12 345"])
def test_cedula_invalida_no_toca_la_base(cliente, cedula):
    with mock.patch.object(turnos, "conectar") as conectar:
        r = cliente.post("/pedir", data={"cedula": cedula})
    assert r.status_code == 302
    assert "mensaje=" in r.headers["Location"]
    conectar.assert_not_called()


def test_cedula_nueva_recibe_turno(cliente):
    con, cur = conexion_falsa([None, (7,)])
    with mock.patch.object(turnos, "conectar", return_value=con):
        r = cliente.post("/pedir", data={"cedula": "123456789"})
    assert r.status_code == 302
    assert "codigo=A-007" in r.headers["Location"]
    assert "mensaje" not in r.headers["Location"]
    sql = [c.args[0] for c in cur.execute.call_args_list]
    assert any("INSERT INTO turnos" in s for s in sql)


def test_cedula_con_turno_activo_reutiliza_codigo(cliente):
    con, cur = conexion_falsa([(3,)])
    with mock.patch.object(turnos, "conectar", return_value=con):
        r = cliente.post("/pedir", data={"cedula": "123456789"})
    assert "codigo=A-003" in r.headers["Location"]
    assert "mensaje=" in r.headers["Location"]
    sql = [c.args[0] for c in cur.execute.call_args_list]
    assert not any("INSERT" in s for s in sql)
