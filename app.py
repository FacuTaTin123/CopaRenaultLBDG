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
                "equipos": ["4A", "4B", "5A", "5B"]
            },
            {
                "nombre": "Grupo B",
                "equipos": ["6A", "6B", "7A", "7B"]
            }
        ]
    }
]

def armar_tabla_posiciones(partidos):
    equipos = {}

    for partido in partidos:
        equipo1 = partido.get("equipo1")
        equipo2 = partido.get("equipo2")

        if not equipo1 or not equipo2:
            continue

        for equipo in (equipo1, equipo2):
            equipos.setdefault(equipo, {
                "equipo": equipo,
                "pj": 0,
                "g": 0,
                "e": 0,
                "p": 0,
                "gf": 0,
                "gc": 0,
                "pts": 0
            })

        goles1 = partido.get("goles1")
        goles2 = partido.get("goles2")

        if goles1 is None or goles2 is None:
            continue

        goles1 = int(goles1)
        goles2 = int(goles2)

        equipos[equipo1]["pj"] += 1
        equipos[equipo2]["pj"] += 1
        equipos[equipo1]["gf"] += goles1
        equipos[equipo1]["gc"] += goles2
        equipos[equipo2]["gf"] += goles2
        equipos[equipo2]["gc"] += goles1

        if goles1 > goles2:
            equipos[equipo1]["g"] += 1
            equipos[equipo2]["p"] += 1
            equipos[equipo1]["pts"] += 3
        elif goles2 > goles1:
            equipos[equipo2]["g"] += 1
            equipos[equipo1]["p"] += 1
            equipos[equipo2]["pts"] += 3
        else:
            equipos[equipo1]["e"] += 1
            equipos[equipo2]["e"] += 1
            equipos[equipo1]["pts"] += 1
            equipos[equipo2]["pts"] += 1

    return sorted(
        equipos.values(),
        key=lambda equipo: (
            equipo["pts"],
            equipo["gf"] - equipo["gc"],
            equipo["gf"],
            equipo["equipo"]
        ),
        reverse=True
    )

# =====================================================
# CONTEXTO GLOBAL
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
            .where("usuario", "==", usuario).get()

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

            datos = usuarios[0].to_dict()

            session.clear()

            session["usuario"] = datos["usuario"]
            session["rol"] = datos["rol"]
            session["es_admin"] = (datos["rol"] == "admin")

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

    docs = db.collection("partidos").get()

    for doc in docs:
        p = doc.to_dict()
        p["id"] = doc.id
        partidos.append(p)

    return render_template(
        "fixture.html",
        partidos=partidos,
        fixtures_grupos=fixtures_grupos,
        tabla_posiciones=armar_tabla_posiciones(partidos)
    )

# =====================================================
# CREAR PARTIDO
# =====================================================

@aplicacion.route("/crear_partido", methods=["POST"])
def crear_partido():

    if not session.get("es_admin"):
        flash("No tenes permisos")
        return redirect("/fixture")

    db.collection("partidos").add({
        "equipo1": request.form["equipo1"],
        "equipo2": request.form["equipo2"],
        "deporte": request.form["deporte"],
        "categoria": request.form["categoria"],
        "rama": request.form["rama"],
        "cancha": request.form["cancha"],
        "horario": request.form["horario"],
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

    if not session.get("es_admin"):
        flash("No tenes permisos")
        return redirect("/fixture")

    db.collection("partidos").document(id).update({
        "goles1": int(request.form["goles1"]),
        "goles2": int(request.form["goles2"])
    })

    flash("Resultado guardado")
    return redirect("/fixture")

# =====================================================
# ELIMINAR PARTIDO
# =====================================================

@aplicacion.route("/eliminar_partido/<id>", methods=["POST"])
def eliminar_partido(id):

    if not session.get("es_admin"):
        flash("No tenes permisos")
        return redirect("/fixture")

    db.collection("partidos").document(id).delete()

    flash("Partido eliminado")
    return redirect("/fixture")

# =====================================================
# 🍔 CANTINA - VER PRODUCTOS
# =====================================================

@aplicacion.route("/cantina")
def cantina():

    productos = []

    docs = db.collection("cantina").get()

    for doc in docs:
        p = doc.to_dict()
        p["id"] = doc.id
        productos.append(p)

    return render_template("cantina.html", productos=productos)

# =====================================================
# 🍔 CANTINA - AGREGAR PRODUCTO (ADMIN)
# =====================================================

@aplicacion.route("/cantina/agregar", methods=["POST"])
def agregar_producto():

    if not session.get("es_admin"):
        flash("No tenes permisos")
        return redirect("/cantina")

    db.collection("cantina").add({
        "nombre": request.form["nombre"],
        "precio": int(request.form["precio"])
    })

    flash("Producto agregado")
    return redirect("/cantina")

# =====================================================
# 🍔 CANTINA - ELIMINAR PRODUCTO (ADMIN)
# =====================================================

@aplicacion.route("/cantina/eliminar/<id>", methods=["POST"])
def eliminar_producto(id):

    if not session.get("es_admin"):
        flash("No tenes permisos")
        return redirect("/cantina")

    db.collection("cantina").document(id).delete()

    flash("Producto eliminado")
    return redirect("/cantina")

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    aplicacion.run(debug=True)
