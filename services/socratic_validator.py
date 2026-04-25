import re
from typing import Tuple, List

FORBIDDEN_PATTERNS = [
    r"수정하시(?:는 것이|기 바랍니다|세요)",
    r"추가하(?:시기|세요|십시오)",
    r"다음과 같이 (?:바꾸|작성하)",
    r"^(?:첫째|둘째|1\.|2\.)",  # 정답형 나열식 응답
    r"제공해 드립니다",
    r"추천합니다",
    r"~을 하세요",
    r"~을 추가하세요"
]

def validate_socratic_response(response_text: str) -> Tuple[bool, List[str]]:
    """
    Validates if the Stage 4 response follows Socratic rules.
    
    Returns:
        (is_valid, violations): List of violation descriptions.
    """
    violations = []
    
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, response_text):
            violations.append(f"금지 패턴 감지: {pattern}")
            
    if "?" not in response_text:
        violations.append("질문 부호 부재 (소크라테스식 질문이 아님)")
        
    return len(violations) == 0, violations
