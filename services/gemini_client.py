import os
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import json

class GeminiService:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.pro_model = "gemini-3.1-pro-preview"
        self.flash_model = "gemini-3.1-flash-lite-preview"

    def load_prompt(self, filename: str) -> str:
        with open(f"prompts/{filename}", "r", encoding="utf-8") as f:
            return f.read()

    def create_context_cache(self, model_name: str, checklist_path: str, pedagogy_path: Optional[str] = None):
        """
        Creates a Context Cache for the specified model with the rubric and pedagogy docs.
        """
        with open(checklist_path, "r", encoding="utf-8") as f:
            checklist_content = f.read()
        
        pedagogy_content = ""
        if pedagogy_path:
            with open(pedagogy_path, "r", encoding="utf-8") as f:
                pedagogy_content = f.read()
        else:
            pedagogy_content = "특정 교수학습모형이 선택되지 않았습니다. 일반 교수설계 원리를 적용하세요."

        cached_content = [
            types.Content(role="user", parts=[
                types.Part(text=f"# 평가 체크리스트\n{checklist_content}\n\n# 교수학습모형\n{pedagogy_content}")
            ])
        ]

        cache = self.client.caches.create(
            model=model_name,
            config=types.CreateCachedContentConfig(
                contents=cached_content,
                ttl="3600s"
            )
        )
        return cache

    def generate_feedback_stage2(self, plan_text: str, cache_name: str) -> Dict[str, Any]:
        """
        Stage 2: Feedback using Gemini Pro with Context Cache.
        """
        instruction = self.load_prompt("stage2_feedback.txt")
        combined_prompt = f"[SYSTEM INSTRUCTION]\n{instruction}\n\n[TASK]\n다음 1차 수업지도안을 분석하세요:\n\n{plan_text}"
        
        response = self.client.models.generate_content(
            model=self.pro_model,
            contents=[combined_prompt],
            config=types.GenerateContentConfig(
                cached_content=cache_name,
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        
        usage = response.usage_metadata
        # Usage metadata for Firestore logging
        self.last_usage = {
            "input_tokens": usage.prompt_token_count,
            "output_tokens": usage.candidates_token_count,
            "cached_tokens": usage.cached_content_token_count
        }
        
        try:
            return json.loads(response.text)
        except:
            return {"error": "Failed to parse AI response", "raw": response.text}

    def chat_stage3(self, message: str, history: List[types.Content], cache_name: str) -> str:
        """
        Stage 3: Student-led chat using Flash-Lite.
        """
        instruction = self.load_prompt("stage3_student_led.txt")
        # Injects instruction to the current turn's message for Cache compatibility
        combined_message = f"[SYSTEM PROTOCOL: PASSIVE Q&A]\n{instruction}\n\n[STUDENT QUESTION]\n{message}"
        
        # Build contents
        contents = history + [types.Content(role="user", parts=[types.Part(text=combined_message)])]
        
        response = self.client.models.generate_content(
            model=self.flash_model,
            contents=contents,
            config=types.GenerateContentConfig(
                cached_content=cache_name,
                temperature=0.7
            )
        )
        
        usage = response.usage_metadata
        self.last_usage = {
            "input_tokens": usage.prompt_token_count,
            "output_tokens": usage.candidates_token_count,
            "cached_tokens": usage.cached_content_token_count
        }
        
        return response.text

    def generate_topic_queue(self, plan_text: str, feedback: str, logs: str, cache_name: str) -> Dict[str, Any]:
        """
        Stage 4: Topic Queue generation using Flash-Lite.
        """
        instruction = self.load_prompt("stage4_topic_queue.txt")
        combined_prompt = f"[SYSTEM INSTRUCTION]\n{instruction}\n\n[CONTEXT]\n[1차 지도안]\n{plan_text}\n\n[2단계 피드백]\n{feedback}\n\n[3단계 대화 로그]\n{logs}"
        
        response = self.client.models.generate_content(
            model=self.flash_model,
            contents=[combined_prompt],
            config=types.GenerateContentConfig(
                cached_content=cache_name,
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        return json.loads(response.text)

    def socratic_chat_stage4(self, message: str, history: List[types.Content], cache_name: str) -> Dict[str, Any]:
        """
        Stage 4: Socratic chat using Flash-Lite.
        Returns a JSON with:
        - "question": AI's response or next question
        - "is_finished": Boolean, true if the topic is sufficiently discussed
        - "pedagogical_rationale": Why AI chose this response
        """
        instruction = self.load_prompt("stage4_socratic.txt")
        combined_message = f"[SYSTEM PROTOCOL: SOCRATIC COACHING]\n{instruction}\n\n[STUDENT INPUT]\n{message}"
        
        contents = history + [types.Content(role="user", parts=[types.Part(text=combined_message)])]
        
        response = self.client.models.generate_content(
            model=self.flash_model,
            contents=contents,
            config=types.GenerateContentConfig(
                cached_content=cache_name,
                response_mime_type="application/json",
                # Note: Defining a specific schema helps ensure is_finished is always present
                response_schema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "is_finished": {"type": "boolean"},
                        "pedagogical_rationale": {"type": "string"}
                    },
                    "required": ["question", "is_finished"]
                },
                temperature=0.8
            )
        )
        
        usage = response.usage_metadata
        self.last_usage = {
            "input_tokens": usage.prompt_token_count,
            "output_tokens": usage.candidates_token_count,
            "cached_tokens": usage.cached_content_token_count
        }
        
        return json.loads(response.text)

