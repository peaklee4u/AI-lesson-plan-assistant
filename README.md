# Google Antigravity: 생성형 AI 기반 수업설계 Assistant

본 프로젝트는 예비 과학교사가 1차 수업지도안을 업로드하면, 루브릭과 교수학습이론에 기반하여 스스로 반성하고 수정할 수 있도록 돕는 AI 코칭 시스템입니다.

## 🎯 주요 기능
- **1단계: 로그인 및 업로드**: 학번/성명 입력 및 지도안 PDF 업로드
- **2단계: 구조화된 피드백**: `gemini-3.1-pro`를 이용한 영역별 강점/약점 분석 (정답 미제공)
- **3단계: 학생 주도 Q&A**: 학생의 질문에만 답변하는 보조자 모드
- **4단계: AI 주도 소크라테스 대화**: 미해결 쟁점을 AI가 먼저 제기하여 심층 성찰 유도
- **영속 저장**: 모든 대화 로그와 토큰 사용량을 Firebase Firestore에 저장하여 질적 분석 지원

## 🚀 시작하기

### 1. 필수 라이브러리 설치
```bash
pip install streamlit google-genai pdfplumber firebase-admin pydantic python-dotenv
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 다음 정보를 입력하세요:
- `GEMINI_API_KEY`: Google AI Studio에서 발급받은 API 키

### 3. Firebase 설정
- Firebase 프로젝트를 생성하고 Firestore, Storage를 활성화하세요.
- 서비스 계정 키(JSON)를 발급받아 환경 설정에 연동하세요.

### 4. 앱 실행
```bash
streamlit run app.py
```

## 💰 비용 및 성능 최적화 (Context Caching)
본 앱은 Gemini 3의 **Context Caching** 기능을 사용합니다. 수업 루브릭(`checklist.md`)과 교수학습모형 문헌을 캐시에 저장하여, 매 질문마다 수천 토큰의 참조 데이터를 다시 보내지 않도록 설계되었습니다. 이를 통해 약 90% 이상의 프롬프트 비용을 절감할 수 있습니다.

> [!IMPORTANT]
> **Gemini 3.1 Pro** 모델은 무료 티어가 없으므로 유료 결제가 활성화된 API 키가 필요합니다.

## 📂 프로젝트 구조
- `app.py`: 메인 어플리케이션 로직
- `services/`: Gemini, Firebase, PDF 파서 등 핵심 엔진
- `ref/`: 루브릭 및 교수학습모형 참조 문서
- `prompts/`: 단계별 시스템 프롬프트 (연구자가 직접 수정 가능)
- `docs/`: 데이터 스키마 및 품질 검증 가이드
