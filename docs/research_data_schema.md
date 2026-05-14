# 연구 데이터 추출 및 분석 스키마

본 문서는 `sessions` 컬렉션의 데이터를 바탕으로 연구자가 분석할 수 있는 주요 변인과 데이터 구조를 설명합니다.

## 1. 세션 메타데이터 (`/sessions/{sessionId}`)
- `studentId`: 학번 (분석 대상자 식별)
- `pedagogyModel`: 선택된 교수학습모형 (비교 분석용)
- `lessonPlanUrl`: 1차 지도안 PDF 링크
- `currentStage`: 최종 도달 단계 (이탈 여부 확인)
- `stageTimestamps`: 각 단계별 소요 시간 (열중도 분석)

## 2. 2단계 피드백 데이터 (`/sessions/{sessionId}/feedback/`)
- `weaknessesCategorized`: AI가 지적한 영역별 약점 (지도안의 초기 결함 영역 분석)
- `overallSummary`: AI의 종합 평 (학습자의 사전 상태 진단)

## 3. 대화 로그 분석 (`/sessions/{sessionId}/messages/`)
이 서브컬렉션은 질적 코딩의 핵심 데이터입니다.
- `role`: "student" (학습자) vs "ai" (시스템)
- `stage`: 3(학생 주도) vs 4(AI 주도) - **AI 주도성 변화** 분석의 핵심 변인
- `content`: 발화 내용
- `modelUsed`: 사용된 Gemini 모델 버전
- `currentTopicId`: (4단계 전용) 현재 논의 중인 교수-학습 쟁점
- `inputTokens`/`outputTokens`: 대화 양(Volume) 분석
- `cachedTokens`: 비용 효율성 데이터

## 4. 소크라테스 쟁점 큐 (`/sessions/{sessionId}/topicQueue/`)
- `element`: AI가 포착한 미해결 쟁점 명칭
- `rationale`: 해당 쟁점을 왜 다루어야 하는지에 대한 AI의 판단 근거 (연구자의 판단과 비교 가능)

## 5. 데이터 추출 방법
Firebase Console에서 JSON/CSV 형태로 내보내거나, Python Admin SDK를 사용하여 Pandas DataFrame으로 변환하여 분석할 수 있습니다.
