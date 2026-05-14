import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_feedback():
    if os.path.exists("firebase-key.json"):
        cred = credentials.Certificate("firebase-key.json")
        try:
            firebase_admin.initialize_app(cred)
        except:
            pass
    db = firestore.client()
    session_id = "41558dd5-05b9-46b9-ad8b-ebb9268c8adc"
    
    feedback_ref = db.collection("sessions").document(session_id).collection("feedback").stream()
    print("Feedback in session:")
    for fb in feedback_ref:
        print(f"- {fb.to_dict().keys()}")

if __name__ == "__main__":
    check_feedback()
