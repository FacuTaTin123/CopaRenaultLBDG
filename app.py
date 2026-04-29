from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "clave"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///copa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/contacto")
def contacto():
    return render_template("contacto.html")

@app.route("/base")
def nashe():
    return render_template("base.html")

@app.route("/registro")
def registro():
    return render_template("registro.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/fixture")
def fixture():
    partidos = Partido.query.all()
    return render_template("fixture.html", partidos=partidos)

if __name__ == "__main__":
    app.run(debug=True)
    
    
class Partido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo_local = db.Column(db.String(50))
    equipo_visitante = db.Column(db.String(50))
    fecha = db.Column(db.String(50))
    goles_local = db.Column(db.Integer, nullable=True)
    goles_visitante = db.Column(db.Integer, nullable=True)
    
from app import Partido, db, app

with app.app_context():
    p = Partido(
        equipo_local="Equipo A",
        equipo_visitante="Equipo B",
        fecha="2026-05-01"
    )
    db.session.add(p)
    db.session.commit()