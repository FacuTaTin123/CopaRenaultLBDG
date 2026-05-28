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
# HELPER: ARMAR TABLAS
# =====================================================

def armar_tablas(partidos):

    tablas = {}

    for partido in partidos:

        deporte = partido.get("deporte", "Sin deporte")
        categoria = partido.get("categoria", "Sin categoria")
        tipo = partido.get("tipo", "Sin tipo")
        grupo = partido.get("grupo", "Sin grupo")

        clave = f"{deporte}-{categoria}-{tipo}-{grupo}"

        if clave not in tablas:

            tablas[clave] = {
                "info": {
                    "deporte": deporte,
                    "categoria": categoria,
                    "tipo": tipo,
                    "grupo": grupo
                },
                "equipos": {}
            }

        tabla = tablas[clave]["equipos"]

        equipo1 = partido["equipo1"]
        equipo2 = partido["equipo2"]

        if equipo1 not in tabla:
            tabla[equipo1] = {"nombre": equipo1, "puntos": 0,'gf':0,'gc':0,'dg':0, "g": 0, "e": 0, "p": 0}

        if equipo2 not in tabla:
            tabla[equipo2] = {"nombre": equipo2, "puntos": 0,'gf':0,'gc':0,'dg':0, "g": 0, "e": 0, "p": 0}

        if partido["goles1"] is not None and partido["goles2"] is not None:

            goles1 = partido["goles1"]
            goles2 = partido["goles2"]

            tabla[equipo1]["gf"] += goles1
            tabla[equipo1]["gc"] += goles2
            tabla[equipo2]["gf"] += goles2
            tabla[equipo2]["gc"] += goles1

            tabla[equipo1]["dg"] = tabla[equipo1]["gf"] - tabla[equipo1]["gc"]
            tabla[equipo2]["dg"] = tabla[equipo2]["gf"] - tabla[equipo2]["gc"]

            if goles1 > goles2:
                tabla[equipo1]["puntos"] += 3
                tabla[equipo1]["g"] += 1
                tabla[equipo2]["p"] += 1
            elif goles2 > goles1:
                tabla[equipo2]["puntos"] += 3
                tabla[equipo2]["g"] += 1
                tabla[equipo1]["p"] += 1
            else:
                tabla[equipo1]["puntos"] += 1
                tabla[equipo2]["puntos"] += 1
                tabla[equipo1]["e"] += 1
                tabla[equipo2]["e"] += 1

    tablas_finales = []

    for clave, datos in tablas.items():

        equipos_ordenados = sorted(
            datos["equipos"].values(),
            key=lambda x: (x["puntos"], x["dg"], x["gf"]),
            reverse=True
        )

        tablas_finales.append({
            "info": datos["info"],
            "equipos": equipos_ordenados
        })

    return tablas_finales

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

    tablas_finales = armar_tablas(partidos)

    return render_template(
        "fixture.html",
        partidos=partidos,
        tablas=tablas_finales
    )

# =====================================================
# TABLAS
# =====================================================

@aplicacion.route("/tablas")
def tablas():

    partidos = []

    documentos = db.collection("partidos").get()

    for doc in documentos:
        partido = doc.to_dict()
        partido["id"] = doc.id
        partidos.append(partido)

    tablas_finales = armar_tablas(partidos)

    return render_template(
        "tablas.html",
        tablas=tablas_finales
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
    categoria = request.form["categoria"]
    tipo = request.form["tipo"]
    cancha = request.form["cancha"]
    grupo = request.form.get("grupo")
    horario = request.form["horario"]

    db.collection("partidos").add({
        "equipo1": equipo1,
        "equipo2": equipo2,
        "deporte": deporte,
        "categoria": categoria,
        "tipo": tipo,
        "cancha": cancha,
        "grupo": grupo,
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
# CANTINA - VER PRODUCTOS
# =====================================================

@aplicacion.route("/cantina")
def cantina():

    productos = []

    docs = db.collection("cantina").get()

    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        productos.append(item)

    return render_template("cantina.html", productos=productos)

# =====================================================
# AGREGAR PRODUCTO (ADMIN)
# =====================================================

@aplicacion.route("/cantina/agregar", methods=["POST"])
def agregar_producto():

    if not session.get("es_admin"):
        flash("No tenes permisos")
        return redirect("/cantina")

    nombre = request.form["nombre"]
    precio = request.form["precio"]

    db.collection("cantina").add({
        "nombre": nombre,
        "precio": int(precio)
    })

    flash("Producto agregado correctamente")
    return redirect("/cantina")

# =====================================================
# ELIMINAR PRODUCTO (ADMIN)
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