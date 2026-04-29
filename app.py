from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = "cambiar-esta-clave"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///copa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    es_admin = db.Column(db.Boolean, default=False, nullable=False)

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)


class Partido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo_local = db.Column(db.String(50), nullable=False)
    equipo_visitante = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.String(50), nullable=False)
    goles_local = db.Column(db.Integer, nullable=True)
    goles_visitante = db.Column(db.Integer, nullable=True)


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

        if Usuario.query.filter_by(usuario=usuario).first():
            flash("Ese usuario ya existe.", "error")
            return render_template("registro.html")

        es_primer_usuario = Usuario.query.count() == 0
        nuevo_usuario = Usuario(
            usuario=usuario,
            password_hash=generate_password_hash(password),
            es_admin=es_primer_usuario,
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Cuenta creada. Ya podes iniciar sesion.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        usuario_db = Usuario.query.filter_by(usuario=usuario).first()

        if not usuario_db or not usuario_db.verificar_password(password):
            flash("Usuario o contrasena incorrectos.", "error")
            return render_template("login.html")

        session.clear()
        session["usuario_id"] = usuario_db.id
        session["usuario"] = usuario_db.usuario
        session["es_admin"] = usuario_db.es_admin

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
    partidos = Partido.query.order_by(Partido.fecha.asc(), Partido.id.asc()).all()
    return render_template("fixture.html", partidos=partidos)


@app.route("/admin/crear_partido", methods=["GET", "POST"])
@admin_requerido
def crear_partido():
    if request.method == "POST":
        partido = Partido(
            equipo_local=request.form.get("equipo_local", "").strip(),
            equipo_visitante=request.form.get("equipo_visitante", "").strip(),
            fecha=request.form.get("fecha", "").strip(),
        )

        if not partido.equipo_local or not partido.equipo_visitante or not partido.fecha:
            flash("Completa los equipos y la fecha.", "error")
            return render_template("partido_form.html", partido=partido, accion="Crear")

        db.session.add(partido)
        db.session.commit()
        flash("Partido creado.", "success")
        return redirect(url_for("fixture"))

    return render_template("partido_form.html", partido=None, accion="Crear")


@app.route("/admin/editar_partido/<int:partido_id>", methods=["GET", "POST"])
@admin_requerido
def editar_partido(partido_id):
    partido = Partido.query.get_or_404(partido_id)

    if request.method == "POST":
        partido.equipo_local = request.form.get("equipo_local", "").strip()
        partido.equipo_visitante = request.form.get("equipo_visitante", "").strip()
        partido.fecha = request.form.get("fecha", "").strip()
        partido.goles_local = convertir_gol(request.form.get("goles_local"))
        partido.goles_visitante = convertir_gol(request.form.get("goles_visitante"))

        if not partido.equipo_local or not partido.equipo_visitante or not partido.fecha:
            flash("Completa los equipos y la fecha.", "error")
            return render_template("partido_form.html", partido=partido, accion="Editar")

        db.session.commit()
        flash("Partido actualizado.", "success")
        return redirect(url_for("fixture"))

    return render_template("partido_form.html", partido=partido, accion="Editar")


@app.route("/admin/eliminar_partido/<int:partido_id>", methods=["POST"])
@admin_requerido
def eliminar_partido(partido_id):
    partido = Partido.query.get_or_404(partido_id)
    db.session.delete(partido)
    db.session.commit()
    flash("Partido eliminado.", "success")
    return redirect(url_for("fixture"))


def convertir_gol(valor):
    if valor is None or valor.strip() == "":
        return None
    return int(valor)


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Base de datos inicializada.")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
