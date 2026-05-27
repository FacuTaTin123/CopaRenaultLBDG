import firebase_admin

from firebase_admin import credentials
from firebase_admin import firestore

credenciales = credentials.Certificate("firebase.json")

firebase_admin.initialize_app(credenciales)

db = firestore.client()