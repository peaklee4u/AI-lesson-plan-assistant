import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

def list_collections():
    if os.path.exists("firebase-key.json"):
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred)
    else:
        print("firebase-key.json not found")
        return

    db = firestore.client()
    collections = db.collections()
    print("Collections in Firestore:")
    for col in collections:
        print(f"- {col.id}")

if __name__ == "__main__":
    list_collections()
