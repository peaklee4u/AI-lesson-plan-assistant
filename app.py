import streamlit as st
import os
import json
from dotenv import load_dotenv
from google.genai import types
from services.firebase_client import FirebaseService
from services.gemini_client import GeminiService
from services.pdf_parser import extract_text_from_pdf

# Load environment variables
load_dotenv()

st.set_page_config(page_title="과학 수업설계 AI Assistant", layout="wide")

# Environment Config (Local vs Cloud)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.getenv("GEMINI_API_KEY")

# Initialize Services
if 'firebase' not in st.session_state:
    service_account_info = None
    
    # 1. New Approach: Read entire JSON as a single string
    if "FIREBASE_SERVICE_ACCOUNT_JSON" in st.secrets:
        try:
            service_account_info = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_JSON"])
        except Exception as e:
            st.error(f"Firebase JSON parsing error: {e}")
    
    # 2. Fallback to old approach if needed
    elif "firebase_service_account" in st.secrets:
        service_account_info = dict(st.secrets["firebase_service_account"])
    
    st.session_state.firebase = FirebaseService(service_account_info)


if 'gemini' not in st.session_state:
    st.session_state.gemini = GeminiService(api_key=api_key)

# Initialize Session State
if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'student_id' not in st.session_state:
    st.session_state.student_id = ""

def next_stage():
    st.session_state.stage += 1
    st.rerun()

# --- Helpers ---
def is_multi_question(text: str) -> bool:
    if text.count("?") >= 2:
        return True
    connectors = ["그리고", "또한", "또", "그런데"]
    if any(c in text for c in connectors) and "?" in text:
        return True
    return False


# --- UI Header ---
st.title("🧪 생성형 AI 기반 수업설계 Assistant")
st.markdown("---")

# --- Stage 1: Login & Upload ---
if st.session_state.stage == 1:
    st.header("1단계: 정보 입력 및 지도안 업로드")
    
    col1, col2 = st.columns(2)
    with col1:
        student_id = st.text_input("학번 (숫자)", placeholder="예: 202412345")
        student_name = st.text_input("성명")
        
    with col2:
        pedagogy_models = [
            "발견학습", "3단계 순환학습", "5E", "POE", "발생학습", 
            "개념변화모형", "STAD", "Jigsaw1", "Jigsaw2", "GI", "기타"
        ]
        selected_model = st.selectbox("교수학습모형 선택", pedagogy_models)
        
    uploaded_file = st.file_uploader("1차 수업지도안 PDF 업로드", type="pdf")
    
    if st.button("AI 코칭 시작하기", type="primary"):
        if not student_id or not student_name or not uploaded_file:
            st.error("모든 정보를 입력하고 PDF를 업로드해주세요.")
        else:
            with st.spinner("지도안을 분석 중입니다..."):
                # 1. Create Firebase Session
                session_id = st.session_state.firebase.create_session(student_id, student_name, selected_model)
                st.session_state.session_id = session_id
                st.session_state.student_id = student_id
                
                # 2. Extract Text from PDF (Immediately without storage upload)
                extracted_text = extract_text_from_pdf(uploaded_file)
                
                # 3. Create Context Caches
                # Filename mapping based on user input
                model_map = {
                    "발견학습": "DiscoveryLearning.md",
                    "3단계순환학습": "LearningCycle.md",
                    "5E": "5E.md",
                    "POE": "POE.md",
                    "발생학습(생성학습)": "GenerativeLearning.md",
                    "개념변화모형": "ConceptualChange.md",
                    "STAD": "STAD.md",
                    "Jigsaw1": "Jigsaw1.md",
                    "Jigsaw2": "Jigsaw2.md",
                    "GI": "GI.md"
                }
                
                model_filename = model_map.get(selected_model)
                pedagogy_path = f"ref/{model_filename}" if model_filename else None
                
                pro_cache = st.session_state.gemini.create_context_cache(
                    model_name=st.session_state.gemini.pro_model,
                    checklist_path="ref/checklist.md",
                    pedagogy_path=pedagogy_path
                )

                
                flash_cache = st.session_state.gemini.create_context_cache(
                    model_name=st.session_state.gemini.flash_model,
                    checklist_path="ref/checklist.md",
                    pedagogy_path=pedagogy_path
                )
                
                # 4. Update Firestore (lessonPlanUrl field removed)
                st.session_state.firebase.update_session(session_id, {
                    'extractedText': extracted_text,
                    'proCacheName': pro_cache.name,
                    'flashCacheName': flash_cache.name,
                    'currentStage': 2
                })
                
                st.session_state.pro_cache_name = pro_cache.name
                st.session_state.flash_cache_name = flash_cache.name
                st.session_state.extracted_text = extracted_text

                
                next_stage()

# --- Stage 2: AI Feedback ---
elif st.session_state.stage == 2:
    st.header("2단계: AI 분석 및 피드백")
    
    if "feedback" not in st.session_state:
        with st.spinner("AI가 피드백을 생성하고 있습니다..."):
            feedback = st.session_state.gemini.generate_feedback_stage2(
                st.session_state.extracted_text, 
                st.session_state.pro_cache_name
            )
            st.session_state.feedback = feedback
            st.session_state.firebase.save_feedback(st.session_state.session_id, feedback)

    feedback = st.session_state.feedback
    
    if "error" in feedback:
        st.error(f"오류가 발생했습니다: {feedback['error']}")
    else:
        st.success("✅ 분석이 완료되었습니다.")
        
        tab1, tab2, tab3 = st.tabs(["🌟 강점", "⚠️ 개선 필요 요소", "📝 종합 코멘트"])
        
        with tab1:
            for s in feedback.get("strengths", []):
                st.write(f"- {s}")
        
        with tab2:
            weaknesses = feedback.get("weaknesses_categorized", {})
            for cat, items in weaknesses.items():
                with st.expander(f"**[{cat}]**"):
                    for item in items:
                        st.write(f"- {item}")
            
            missing = feedback.get("missing_elements", [])
            if missing:
                st.error("**누락된 요소**")
                for m in missing:
                    st.write(f"- {m}")
                    
        with tab3:
            st.info(feedback.get("overall_summary", "코멘트가 없습니다."))

    if st.button("다음 단계로 (3단계: 자유 질의응답)", type="primary"):
        st.session_state.firebase.update_session(st.session_state.session_id, {'currentStage': 3})
        next_stage()

# --- Stage 3: Student-led Interaction ---

elif st.session_state.stage == 3:
    st.header("3단계: 자유 질의응답")
    st.info("AI 분석 결과에 대해 궁금한 점을 자유롭게 질문해 보세요. AI는 여러분의 질문에만 답변합니다.")
    
    if "messages_stage3" not in st.session_state:
        st.session_state.messages_stage3 = []

    # Display Chat History
    for msg in st.session_state.messages_stage3:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        # 1. Display Student Message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages_stage3.append({"role": "user", "content": prompt})
        
        # 2. Multi-question Heuristic or Gemini Call
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                # Check for multiple questions

                if is_multi_question(prompt):
                    response_text = "한 번에 하나의 질문에 집중해 보시겠어요? 어떤 것부터 다룰까요? 하나씩 질문해 주시면 차근차근 답변해 드릴게요."
                    model_display = "system"
                else:
                    # Prepare history
                    history = [
                        types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])])
                        for m in st.session_state.messages_stage3[:-1]
                    ]
                    
                    response_text = st.session_state.gemini.chat_stage3(
                        prompt, history, st.session_state.flash_cache_name
                    )
                    model_display = "gemini-3.1-flash-lite"
                
                st.markdown(response_text)
                st.session_state.messages_stage3.append({"role": "assistant", "content": response_text})
                
                # 3. Save to Firestore
                st.session_state.firebase.save_message(st.session_state.session_id, "student", 3, prompt, model_display, {})
                st.session_state.firebase.save_message(st.session_state.session_id, "ai", 3, response_text, model_display, st.session_state.gemini.last_usage if model_display != "system" else {})


    st.markdown("---")
    if st.button("3단계 종료 및 다음 단계로", type="secondary"):
        st.session_state.firebase.update_session(st.session_state.session_id, {'currentStage': 4})
        next_stage()

# --- Stage 4: AI-led Socratic Interaction ---
elif st.session_state.stage == 4:
    st.header("4단계: AI 주도 심층 성찰")
    st.info("이제 AI가 지도안의 핵심 쟁점에 대해 질문을 던집니다. 정답을 찾기보다 자신의 설계 의도를 깊이 있게 고민해 보세요.")

    # 1. Initialize Topic Queue
    if "topic_queue" not in st.session_state:
        with st.spinner("미해결 쟁점을 분석하여 질문 목록을 생성하고 있습니다..."):
            # Prepare data for queue generation
            logs = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages_stage3])
            
            # Use safe string representation of feedback to avoid Sentinel errors
            feedback_str = str(st.session_state.feedback)
            
            queue_data = st.session_state.gemini.generate_topic_queue(
                st.session_state.extracted_text,
                feedback_str,
                logs,
                st.session_state.flash_cache_name
            )
            st.session_state.topic_queue = queue_data.get("untreated_elements", [])

            st.session_state.firebase.save_topic_queue(st.session_state.session_id, st.session_state.topic_queue)
            st.session_state.current_topic_index = 0
            st.session_state.topic_turn_count = 0
            st.session_state.messages_stage4 = []

    # --- Stage 4 Top: Show Roadmap ---
    with st.expander("📌 오늘 우리가 함께 다룰 성찰 쟁점 확인하기", expanded=True):
        st.write("AI가 지도안과 이전 대화를 분석하여 도출한 핵심 쟁점입니다. 하나씩 깊이 있게 고민해 봅시다.")
        for i, topic in enumerate(st.session_state.topic_queue):
            is_current = (i == st.session_state.current_topic_index)
            icon = "➡️" if is_current else ("✅" if i < st.session_state.current_topic_index else "⚪")
            color = "blue" if is_current else "gray"
            st.markdown(f"{icon} **{i+1}. {topic['element']}**")
            if is_current:
                st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;💡 분석 근거: {topic['rationale']}")
    st.markdown("---")

    if not st.session_state.topic_queue or st.session_state.current_topic_index >= len(st.session_state.topic_queue):
        st.success("🎉 모든 쟁점에 대한 논의가 완료되었습니다! 수고하셨습니다.")
        if st.button("세션 종료 및 결과 요약 보기"):
            next_stage() # Move to final summary (Stage 5)
    else:
        current_topic = st.session_state.topic_queue[st.session_state.current_topic_index]
        st.subheader(f"🚩 현재 쟁점: {current_topic['element']}")
        
        # Initial Question from AI (if starting new topic)
        if not st.session_state.messages_stage4:
            first_q = f"'{current_topic['element']}'에 대해 먼저 이야기를 나눠보고 싶습니다. {current_topic['rationale']}와 관련하여, {current_topic['element']}를 지도안에 어떻게 반영하고자 하셨는지 설명해 주실 수 있나요?"
            st.session_state.messages_stage4.append({"role": "assistant", "content": first_q})
            st.session_state.firebase.save_message(
                st.session_state.session_id, "ai", 4, first_q, "system_seed", {}, current_topic['element']
            )

        # Display Chat
        for msg in st.session_state.messages_stage4:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # If it's the start of a topic, AI asks the first question
        if st.session_state.topic_turn_count == 0 and not st.session_state.messages_stage4:
            first_q = current_topic['socratic_prompt_seed']
            with st.chat_message("assistant"):
                st.markdown(first_q)
            st.session_state.messages_stage4.append({"role": "assistant", "content": first_q})
            st.session_state.firebase.save_message(
                st.session_state.session_id, "ai", 4, first_q, "system_seed", {}, current_topic['element']
            )

        # 쟁점별 대화 종료 여부를 세션 스테이트로 관리
        if "topic_is_finished" not in st.session_state:
            st.session_state.topic_is_finished = False

        # 4단계 대화 로직
        # AI가 스스로 대화의 완결성을 판단(is_finished: True)하면 전환 버튼이 나타납니다.
        if st.session_state.topic_is_finished:
            st.info(f"✨ '{current_topic['element']}' 항목에 대한 대화를 마쳤습니다. 다음 과정으로 이동하시겠습니까?")
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("다음 쟁점으로 넘어가기", type="primary", use_container_width=True):
                    st.session_state.current_topic_index += 1
                    st.session_state.topic_is_finished = False
                    st.session_state.messages_stage4 = []
                    st.rerun()
            with col2:
                if st.button("대화 조기 종료", use_container_width=True):
                    next_stage()
        else:
            if prompt := st.chat_input("답변을 입력하세요..."):
                # 1. 학생 응답 표시
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages_stage4.append({"role": "user", "content": prompt})
                st.session_state.topic_turn_count += 1
                
                # 2. Gemini 호출
                with st.chat_message("assistant"):
                    with st.spinner("생각 중..."):
                        history = [
                            types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])])
                            for m in st.session_state.messages_stage4[:-1]
                        ]
                        
                        # AI에게 현재 턴 정보를 주어 종료 판단을 돕게 함
                        context_msg = f"[현재 대화 턴: {st.session_state.topic_turn_count}회]\n{prompt}"
                        
                        # Gemini의 유연한 응답 (최대 1회 재시도)
                        for attempt in range(2):
                            response_json = st.session_state.gemini.socratic_chat_stage4(
                                context_msg, history, st.session_state.flash_cache_name
                            )
                            # 종료 상태가 아닐 때만 소크라테스식 질문 검증
                            ai_is_finished = response_json.get('is_finished', False)
                            ai_text = response_json.get('question', '').strip()

                            if not ai_is_finished:
                                from services.socratic_validator import validate_socratic_response
                                is_valid, violations = validate_socratic_response(ai_text)
                                if is_valid: break
                                # 피드백과 함께 다시 시도
                                context_msg = f"{prompt}\n\n(시스템 경고: 질문이 원칙을 위반함. 다시 질문하세요.)"
                            else:
                                break
                        
                        # AI 판단 업데이트 및 안전장치
                        if ai_is_finished and ("?" in ai_text or ai_text.endswith("?")):
                            st.session_state.topic_is_finished = False
                        else:
                            st.session_state.topic_is_finished = ai_is_finished
                        
                        st.markdown(ai_text)
                        st.session_state.messages_stage4.append({"role": "assistant", "content": ai_text})
                        
                        # 3. Firestore 저장
                        st.session_state.firebase.save_message(
                            st.session_state.session_id, "student", 4, prompt, "gemini-3.1-flash-lite", {}, current_topic['element']
                        )
                        st.session_state.firebase.save_message(
                            st.session_state.session_id, "ai", 4, ai_text, "gemini-3.1-flash-lite", 
                            {"rationale": response_json.get("pedagogical_rationale"), "isFinished": st.session_state.topic_is_finished, "turn": st.session_state.topic_turn_count}, 
                            current_topic['element']
                        )
                        st.rerun()





    # 모든 쟁점이 끝났는지 확인
    if st.session_state.current_topic_index >= len(st.session_state.topic_queue):
        st.success("🎉 모든 핵심 쟁점에 대한 성찰을 마쳤습니다!")
        if st.button("최종 확인 및 종료", type="primary", use_container_width=True):
            next_stage()


# --- Stage 5: Summary & Exit ---
elif st.session_state.stage == 5:
    st.header("🏁 모든 과정을 마쳤습니다")
    st.balloons()
    st.success("작성하신 상호작용 데이터는 연구용으로 소중하게 활용될 예정입니다. 감사합니다.")
    st.markdown("""
    ### 다음 단계:
    1. AI와 나눈 대화를 바탕으로 수업지도안을 수정해 보세요.
    2. 수정된 지도안은 별도로 제출해 주시기 바랍니다.
    """)
    if st.button("처음으로 돌아가기"):
        st.session_state.clear()
        st.rerun()


