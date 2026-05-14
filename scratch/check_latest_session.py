import firebase_admin
from firebase_admin import credentials, firestore
import os

def get_latest_session():
    if os.path.exists("firebase-key.json"):
        cred = credentials.Certificate("firebase-key.json")
        try:
            firebase_admin.initialize_app(cred)
        except:
            pass
    else:
        print("firebase-key.json not found")
        return

    db = firestore.client()
    # Get the latest session based on timestamp if possible, or just the first one
    sessions = db.collection("sessions").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(1).stream()
    
    for session in sessions:
        print(f"Session ID: {session.id}")
        print(f"Data: {session.to_dict()}")
        
        # Check for messages in this session
        messages = db.collection("sessions").document(session.id).collection("messages").order_by("timestamp").stream()
        print("\nMessages:")
        for msg in messages:
            print(f"- {msg.to_dict()}")

if __name__ == "__main__":
    get_latest_session()
