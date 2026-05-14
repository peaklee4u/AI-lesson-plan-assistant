import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

# Set encoding for Windows terminal
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    sessions = db.collection("sessions").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(1).stream()
    
    for session in sessions:
        data = session.to_dict()
        print(f"Session ID: {session.id}")
        print(f"Current Stage: {data.get('currentStage')}")
        
        # Check for messages
        messages = db.collection("sessions").document(session.id).collection("messages").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
        print("\nLatest Messages:")
        for msg in messages:
            m = msg.to_dict()
            print(f"- Role: {m.get('role')}, Stage: {m.get('stage')}, Content: {str(m.get('content'))[:100]}...")

if __name__ == "__main__":
    get_latest_session()
