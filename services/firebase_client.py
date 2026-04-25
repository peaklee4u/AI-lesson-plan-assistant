import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import os
from typing import Optional, Dict, Any, List

from google.cloud import firestore as google_firestore

class FirebaseService:
    def __init__(self, service_account_info: Optional[Dict[str, Any]] = None):
        """
        Initializes Firebase Admin SDK and Firestore Client.
        """
        # 1. Clean start: Delete existing app to avoid stale config in Streamlit
        try:
            existing_app = firebase_admin.get_app()
            firebase_admin.delete_app(existing_app)
        except ValueError:
            pass

        # 2. Extract configuration
        project_id = None
        cred = None

        if service_account_info:
            # Aggressive cleaning for private_key
            if "private_key" in service_account_info:
                pk = service_account_info["private_key"]
                if isinstance(pk, str):
                    pk = pk.strip().replace("\\n", "\n")
                    pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
                    pk = "-----BEGIN PRIVATE KEY-----\n" + pk + "\n-----END PRIVATE KEY-----\n"
                    service_account_info["private_key"] = pk
            
            project_id = service_account_info.get("project_id")
            cred = credentials.Certificate(service_account_info)
        elif os.path.exists("firebase-key.json"):
            import json
            with open("firebase-key.json") as f:
                conf = json.load(f)
                project_id = conf.get("project_id")
            cred = credentials.Certificate("firebase-key.json")

        # 3. Initialize Firebase Admin and then Direct Firestore Client
        if cred:
            firebase_admin.initialize_app(cred, {"projectId": project_id})
            # IMPORTANT: Use the raw Client from google-cloud-firestore to be immune to env var issues
            self.db = google_firestore.Client(
                project=project_id,
                credentials=cred.get_credential()
            )
        else:
            firebase_admin.initialize_app()
            self.db = google_firestore.Client()









    def create_session(self, student_id: str, name: str, pedagogy_model: str) -> str:
        """
        Creates a new session document in Firestore.
        """
        session_id = str(uuid.uuid4())
        session_ref = self.db.collection('sessions').document(session_id)
        session_ref.set({
            'studentId': student_id,
            'name': name,
            'pedagogyModel': pedagogy_model,
            'currentStage': 1,
            'createdAt': firestore.SERVER_TIMESTAMP,
            'stageTimestamps': {
                'stage1': datetime.now()
            }
        })
        return session_id

    def update_session(self, session_id: str, data: Dict[str, Any]):
        """
        Updates session document.
        """
        self.db.collection('sessions').document(session_id).update(data)

    def save_feedback(self, session_id: str, feedback_data: Dict[str, Any]):
        """
        Saves Stage 2 feedback to subcollection.
        """
        feedback_ref = self.db.collection('sessions').document(session_id).collection('feedback').document()
        feedback_data['generatedAt'] = firestore.SERVER_TIMESTAMP
        feedback_ref.set(feedback_data)

    def save_message(self, session_id: str, role: str, stage: int, content: str, model_used: str, usage: Dict[str, Any], topic_id: Optional[str] = None):
        """
        Saves a message to Firestore.
        """
        message_ref = self.db.collection('sessions').document(session_id).collection('messages').document()
        message_data = {
            'role': role,
            'stage': stage,
            'content': content,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'modelUsed': model_used,
            'inputTokens': usage.get('input_tokens', 0),
            'outputTokens': usage.get('output_tokens', 0),
            'cachedTokens': usage.get('cached_tokens', 0)
        }
        if topic_id:
            message_data['currentTopicId'] = topic_id
        message_ref.set(message_data)

    def save_topic_queue(self, session_id: str, topics: List[Dict[str, Any]]):
        """
        Saves topic queue to Firestore.
        """
        batch = self.db.batch()
        for topic in topics:
            topic_id = str(uuid.uuid4())
            topic_ref = self.db.collection('sessions').document(session_id).collection('topicQueue').document(topic_id)
            topic['status'] = 'pending'
            batch.set(topic_ref, topic)
        batch.commit()
