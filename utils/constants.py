# -*- coding: utf-8 -*-
"""
utils/constants.py — 상수 및 정규표현식 정의
"""

import re

# 이모지 및 비표준 특수문자를 매칭하는 정규표현식 (모듈 로드 시 1회 컴파일)
# 유니코드 블록 단위로 범위를 지정하여 이모지·제어문자·장식문자를 포괄합니다.
EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FFFF"  # Misc Symbols, Emoticons, Transport & Map, etc.
    "\U00002600-\U000027BF"  # Misc Symbols, Dingbats
    "\U0000200B-\U0000200F"  # Zero-width chars (ZWSP, ZWNJ, ZWJ, LRM, RLM)
    "\U0000FE00-\U0000FE0F"  # Variation Selectors (이모지 스타일 변환자)
    "\U0000231A-\U000023FF"  # Misc Technical Symbols (⌚⏰ 등)
    "\U00002B05-\U00002B55"  # Supplemental Arrows & Symbols
    "\U00003000-\U0000303F"  # CJK Symbols (전각 공백 등)
    "\U0000FFF0-\U0000FFFF"  # Specials block
    "]+",
    flags=re.UNICODE,
)

# 전화번호 컬럼 자동 감지에 사용할 키워드 목록
# 스마트스토어 주문서 기준: '수취인연락처1', '수취인연락처2', '주문자연락처' 등
PHONE_KEYWORDS = [
    "연락처", "전화", "핸드폰", "휴대폰", "휴대전화",
    "phone", "tel", "mobile",
]

# 성함/이름 컬럼 감지 키워드
# 스마트스토어 기준: '수취인명', '주문자명' 등
NAME_KEYWORDS = [
    "수취인", "이름", "성함", "주문자", "보내는분", "받는분", "name",
]

# 주소 컬럼 감지 키워드
# 스마트스토어 기준: '배송지', '합배송지', '주소' 등
ADDRESS_KEYWORDS = [
    "주소", "배송지", "합배송지", "address", "addr",
]

# NaN·빈값으로 판별할 문자열 집합 (frozenset으로 O(1) 탐색)
NULL_STRINGS = frozenset({"nan", "none", "null", "n/a", "-", ""})

ORDER_KEYWORDS = ["상품주문번호", "주문번호", "order"]

# 스마트스토어 엑셀 헤더 행 자동 탐색에 사용할 키워드
# 이 중 2개 이상이 한 행에 존재하면 해당 행을 헤더로 판정합니다.
HEADER_PROBE_KEYWORDS = [
    "상품주문번호", "주문번호", "수취인명", "수취인",
    "연락처", "배송지", "주소", "상품명", "택배사", "송장번호",
]
