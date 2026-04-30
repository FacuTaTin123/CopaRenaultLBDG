import os
from functools import wraps

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = "cambiar-esta-clave"

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD") or "Dinosaurio123$",
    "database": os.getenv("MYSQL_DATABASE", "copa_renault"),
}


def conectar_db(usar_base=True):
    config = DB_CONFIG.copy()
    if not usar_base:
        config.pop("database")
    return mysql.connector.connect(**config)


def ejecutar_consulta(sql, parametros=None, traer_uno=False, traer_todos=False):
    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)

    try:
        cursor.execute(sql, parametros or ())

        if traer_uno:
            return cursor.fetchone()
        if traer_todos:
            return cursor.fetchall()

        conexion.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conexion.close()


def admin_requerido(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("es_admin"):
            flash("Necesitas iniciar sesion como administrador.", "error")
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


@app.context_processor
def agregar_usuario_actual():
    return {"usuario_actual": session.get("usuario")}


@app.errorhandler(Error)
def manejar_error_mysql(error):
    return (
        "Error al conectar con MySQL. Revisa que la base 'copa_renault' exista "
        f"y que los datos de conexion sean correctos. Detalle: {error}",
        500,
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/contacto")
def contacto():
    return render_template("contacto.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if not usuario or not password:
            flash("Completa usuario y contrasena.", "error")
            return render_template("registro.html")

        usuario_existente = ejecutar_consulta(
            "SELECT id FROM usuario WHERE usuario = %s",
            (usuario,),
            traer_uno=True,
        )
        if usuario_existente:
            flash("Ese usuario ya existe.", "error")
            return render_template("registro.html")

        cantidad_usuarios = ejecutar_consulta(
            "SELECT COUNT(*) AS cantidad FROM usuario",
            traer_uno=True,
        )
        es_primer_usuario = cantidad_usuarios["cantidad"] == 0

        ejecutar_consulta(
            """
            INSERT INTO usuario (usuario, password_hash, es_admin)
            VALUES (%s, %s, %s)
            """,
            (usuario, generate_password_hash(password), es_primer_usuario),
        )

        flash("Cuenta creada. Ya podes iniciar sesion.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        usuario_db = ejecutar_consulta(
            "SELECT * FROM usuario WHERE usuario = %s",
            (usuario,),
            traer_uno=True,
        )

        if not usuario_db or not check_password_hash(usuario_db["password_hash"], password):
            flash("Usuario o contrasena incorrectos.", "error")
            return render_template("login.html")

        session.clear()
        session["usuario_id"] = usuario_db["id"]
        session["usuario"] = usuario_db["usuario"]
        session["es_admin"] = bool(usuario_db["es_admin"])

        flash("Sesion iniciada correctamente.", "success")
        return redirect(url_for("fixture"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada.", "success")
    return redirect(url_for("index"))


@app.route("/fixture")
def fixture():
    partidos = ejecutar_consulta(
        "SELECT * FROM partido ORDER BY horario ASC, id ASC",
        traer_todos=True,
    )
    fixtures_grupos = armar_fixtures_grupos(partidos)
    return render_template(
        "fixture.html",
        partidos=partidos,
        fixtures_grupos=fixtures_grupos,
    )


@app.route("/admin/crear_partido", methods=["GET", "POST"])
@admin_requerido
def crear_partido():
    if request.method == "POST":
        partido = {
            "equipo1": request.form.get("equipo1", "").strip(),
            "equipo2": request.form.get("equipo2", "").strip(),
            "deporte": request.form.get("deporte", "").strip(),
            "rama": request.form.get("rama", "").strip(),
            "horario": request.form.get("horario", "").strip(),
        }

        if not datos_partido_completos(partido):
            flash("Completa los equipos, deporte, rama y horario.", "error")
            return render_template("partido_form.html", partido=partido, accion="Crear")

        ejecutar_consulta(
            """
            INSERT INTO partido (equipo1, equipo2, deporte, rama, horario)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                partido["equipo1"],
                partido["equipo2"],
                partido["deporte"],
                partido["rama"],
                partido["horario"],
            ),
        )

        flash("Partido creado.", "success")
        return redirect(url_for("fixture"))

    return render_template("partido_form.html", partido=None, accion="Crear")


@app.route("/admin/editar_partido/<int:partido_id>", methods=["GET", "POST"])
@admin_requerido
def editar_partido(partido_id):
    partido = buscar_partido_o_404(partido_id)

    if request.method == "POST":
        partido = {
            "id": partido_id,
            "equipo1": request.form.get("equipo1", "").strip(),
            "equipo2": request.form.get("equipo2", "").strip(),
            "deporte": request.form.get("deporte", "").strip(),
            "rama": request.form.get("rama", "").strip(),
            "horario": request.form.get("horario", "").strip(),
            "goles_equipo1": convertir_gol(request.form.get("goles_equipo1")),
            "goles_equipo2": convertir_gol(request.form.get("goles_equipo2")),
        }

        if not datos_partido_completos(partido):
            flash("Completa los equipos, deporte, rama y horario.", "error")
            return render_template("partido_form.html", partido=partido, accion="Editar")

        ejecutar_consulta(
            """
            UPDATE partido
            SET equipo1 = %s,
                equipo2 = %s,
                deporte = %s,
                rama = %s,
                horario = %s,
                goles_equipo1 = %s,
                goles_equipo2 = %s
            WHERE id = %s
            """,
            (
                partido["equipo1"],
                partido["equipo2"],
                partido["deporte"],
                partido["rama"],
                partido["horario"],
                partido["goles_equipo1"],
                partido["goles_equipo2"],
                partido_id,
            ),
        )

        flash("Partido actualizado.", "success")
        return redirect(url_for("fixture"))

    return render_template("partido_form.html", partido=partido, accion="Editar")


@app.route("/admin/eliminar_partido/<int:partido_id>", methods=["POST"])
@admin_requerido
def eliminar_partido(partido_id):
    buscar_partido_o_404(partido_id)
    ejecutar_consulta("DELETE FROM partido WHERE id = %s", (partido_id,))
    flash("Partido eliminado.", "success")
    return redirect(url_for("fixture"))


def buscar_partido_o_404(partido_id):
    partido = ejecutar_consulta(
        "SELECT * FROM partido WHERE id = %s",
        (partido_id,),
        traer_uno=True,
    )
    if not partido:
        abort(404)
    return partido


def armar_fixtures_grupos(partidos):
    deportes = ["Futbol", "Voley", "Basquet"]
    return [
        {
            "deporte": deporte,
            "grupos": armar_grupos(
                [partido for partido in partidos if partido["deporte"] == deporte]
            ),
        }
        for deporte in deportes
    ]


def armar_grupos(partidos):
    equipos = []

    for partido in partidos:
        for nombre_equipo in (partido["equipo1"], partido["equipo2"]):
            if nombre_equipo and nombre_equipo not in equipos:
                equipos.append(nombre_equipo)

    for numero in range(len(equipos) + 1, 17):
        equipos.append(f"EQUIPO {numero}")

    return [
        {"nombre": f"GRUPO {numero}", "equipos": equipos[inicio : inicio + 4]}
        for numero, inicio in enumerate(range(0, 16, 4), start=1)
    ]


def datos_partido_completos(partido):
    return (
        partido["equipo1"]
        and partido["equipo2"]
        and partido["deporte"]
        and partido["rama"]
        and partido["horario"]
    )


def convertir_gol(valor):
    if valor is None or valor.strip() == "":
        return None
    return int(valor)


@app.cli.command("init-db")
def init_db():
    ruta_schema = os.path.join(app.root_path, "schema.sql")
    with open(ruta_schema, encoding="utf-8") as archivo:
        sql = archivo.read()

    conexion = conectar_db(usar_base=False)
    cursor = conexion.cursor()

    try:
        for consulta in sql.split(";"):
            if consulta.strip():
                cursor.execute(consulta)
        conexion.commit()
        print("Base de datos inicializada.")
    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    app.run(debug=True)
