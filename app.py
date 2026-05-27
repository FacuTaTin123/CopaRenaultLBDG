from flask import *
from firebase_config import db

aplicacion = Flask(__name__)

aplicacion.secret_key = "copa_renault"

# =====================================================
# CREAR ADMIN AUTOMÁTICO
# =====================================================

admin = db.collection("usuarios") \
    .where("usuario", "==", "admin") \
    .get()

if len(admin) == 0:

    db.collection("usuarios").add({

        "usuario": "admin",
        "password": "1234",
        "rol": "admin"
    })

# =====================================================
# DATOS VISUALES
# =====================================================

fixtures_grupos = [
    {
        "deporte": "Futbol",
        "grupos": [
            {
                "nombre": "Grupo A",
                "equipos": [
                    "4A",
                    "4B",
                    "5A",
                    "5B"
                ]
            },
            {
                "nombre": "Grupo B",
                "equipos": [
                    "6A",
                    "6B",
                    "7A",
                    "7B"
                ]
            }
        ]
    }
]

tablas_posiciones = []

# =====================================================
# USUARIO GLOBAL
# =====================================================

@aplicacion.context_processor
def variables_globales():

    return {

        "usuario_actual": session.get("usuario"),
        "es_admin": session.get("es_admin", False)
    }

# =====================================================
# INICIO
# =====================================================

@aplicacion.route("/")
def index():

    return render_template("index.html")

# =====================================================
# REGISTRO
# =====================================================

@aplicacion.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        existe = db.collection("usuarios") \
            .where("usuario", "==", usuario) \
            .get()

        if len(existe) > 0:

            flash("Ese usuario ya existe")

            return redirect("/registro")

        db.collection("usuarios").add({

            "usuario": usuario,
            "password": password,
            "rol": "usuario"
        })

        flash("Cuenta creada")

        return redirect("/login")

    return render_template("registro.html")

# =====================================================
# LOGIN
# =====================================================

@aplicacion.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        usuarios = db.collection("usuarios") \
            .where("usuario", "==", usuario) \
            .where("password", "==", password) \
            .get()

        if len(usuarios) > 0:

            datos_usuario = usuarios[0].to_dict()

            session.clear()

            session["usuario"] = datos_usuario["usuario"]
            session["rol"] = datos_usuario["rol"]

            if datos_usuario["rol"] == "admin":

                session["es_admin"] = True

            else:

                session["es_admin"] = False

            flash("Bienvenido")

            return redirect("/fixture")

        flash("Usuario o contraseña incorrectos")

        return redirect("/login")

    return render_template("login.html")

# =====================================================
# LOGOUT
# =====================================================

@aplicacion.route("/logout")
def logout():

    session.clear()

    flash("Sesion cerrada")

    return redirect("/")

# =====================================================
# FIXTURE
# =====================================================

@aplicacion.route("/fixture")
def fixture():

    partidos = []

    documentos = db.collection("partidos").get()

    for doc in documentos:

        partido = doc.to_dict()

        partido["id"] = doc.id

        partidos.append(partido)

    return render_template(

        "fixture.html",

        partidos=partidos,

        fixtures_grupos=fixtures_grupos,

        tablas_posiciones=tablas_posiciones
    )

# =====================================================
# CREAR PARTIDO
# =====================================================

@aplicacion.route("/crear_partido", methods=["POST"])
def crear_partido():

    if session.get("es_admin") != True:

        flash("No tenes permisos")

        return redirect("/fixture")

    equipo1 = request.form["equipo1"]
    equipo2 = request.form["equipo2"]

    deporte = request.form["deporte"]
    rama = request.form["rama"]

    horario = request.form["horario"]

    db.collection("partidos").add({

        "equipo1": equipo1,
        "equipo2": equipo2,

        "deporte": deporte,
        "rama": rama,

        "horario": horario,

        "goles1": None,
        "goles2": None
    })

    flash("Partido creado")

    return redirect("/fixture")

# =====================================================
# RESULTADO
# =====================================================

@aplicacion.route("/resultado/<id>", methods=["POST"])
def resultado(id):

    if session.get("es_admin") != True:

        flash("No tenes permisos")

        return redirect("/fixture")

    goles1 = int(request.form["goles1"])
    goles2 = int(request.form["goles2"])

    db.collection("partidos").document(id).update({

        "goles1": goles1,
        "goles2": goles2
    })

    flash("Resultado guardado")

    return redirect("/fixture")

# =====================================================
# ELIMINAR PARTIDO
# =====================================================

@aplicacion.route("/eliminar_partido/<partido_id>", methods=["POST"])
def eliminar_partido(partido_id):

    if session.get("es_admin") != True:

        flash("No tenes permisos")

        return redirect("/fixture")

    db.collection("partidos").document(partido_id).delete()

    flash("Partido eliminado")

    return redirect("/fixture")

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    aplicacion.run(debug=True)