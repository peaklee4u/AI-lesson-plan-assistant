import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import os
from typing import Optional, Dict, Any, List

class FirebaseService:
    def __init__(self, service_account_info: Optional[Dict[str, Any]] = None):
        """
        Initializes Firebase Admin SDK for Firestore only.
        """
        try:
            # Check if already initialized
            firebase_admin.get_app()
        except ValueError:
            # Not initialized, proceed with initialization
            if service_account_info:
                # Security Fix: Extra-aggressive cleaning for private_key
                if "private_key" in service_account_info:
                    pk = service_account_info["private_key"]
                    if isinstance(pk, str):
                        # 1. Remove Any trailing/leading whitespace or quotes
                        pk = pk.strip().strip("'").strip('"')
                        # 2. Convert literal "\n" strings to real newlines
                        pk = pk.replace("\\n", "\n")
                        # 3. Ensure it starts and ends correctly
                        if not pk.startswith("-----BEGIN PRIVATE KEY-----"):
                            pk = "-----BEGIN PRIVATE KEY-----\n" + pk
                        if not pk.endswith("-----END PRIVATE KEY-----"):
                            pk = pk + "\n-----END PRIVATE KEY-----"
                        
                        service_account_info["private_key"] = pk
                
                cred = credentials.Certificate(service_account_info)
            elif os.path.exists("firebase-key.json"):
                cred = credentials.Certificate("firebase-key.json")
            else:
                try:
                    cred = credentials.ApplicationDefault()
                except:
                    # Last resort fallback (usually for cloud environments)
                    firebase_admin.initialize_app()
                    self.db = firestore.client()
                    return
            
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()




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
