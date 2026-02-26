# -*- coding: utf-8 -*-
"""
utils/cleaners.py — 데이터 정제 핵심 함수
  remove_emoji · format_phone_number · strip_whitespace
"""

import re
import unicodedata

import pandas as pd

from utils.constants import EMOJI_RE, NULL_STRINGS


def remove_emoji(text: str) -> str:
    """
    셀 값에서 이모지 및 비표준 특수문자를 제거합니다.

    처리 대상:
      - 이모지 (😊🎉📦🏠🚀 등)
      - Zero-width 문자 (ZWSP, ZWNJ, ZWJ — 복사/붙여넣기 시 혼입)
      - 제어문자 (탭 \\t, 줄바꿈 \\n, NULL \\x00 등)

    보존 대상:
      - 한글, 영문, 숫자, 기본 구두점(.,!?-()/ 등)

    Args:
        text: 정제할 원본 문자열

    Returns:
        이모지·제어문자가 제거되고 연속 공백이 압축된 문자열
    """
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    # 연속 공백을 단일 공백으로 압축
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def format_phone_number(raw: str) -> str:
    """
    전화번호를 '010-0000-0000' 형식으로 통일합니다.

    지원 입력 형식 및 변환 결과:
      01012345678        → 010-1234-5678  (숫자만 나열)
      010-1234-5678      → 010-1234-5678  (이미 올바른 형식)
      +82-10-1234-5678   → 010-1234-5678  (국제번호 → 국내 형식)
      010.1234.5678      → 010-1234-5678  (마침표 구분자)
      (010) 1234 5678    → 010-1234-5678  (괄호·공백 구분자)
      02-1234-5678       → 02-1234-5678   (서울 지역번호)
      nan / 빈값         → ""

    Args:
        raw: 정제할 원본 전화번호 문자열

    Returns:
        하이픈이 삽입된 표준 형식 전화번호, 또는 패턴 불일치 시 원본
    """
    if pd.isna(raw):
        return ""

    text = str(raw).strip()
    if text.lower() in NULL_STRINGS:
        return ""

    # 엑셀이 전화번호를 숫자로 저장한 경우 float 문자열 처리
    # "1012345678.0" 또는 "1.01234568E+09" → "1012345678"
    if "." in text or "e" in text.lower():
        try:
            num_val = float(text)
            if 1e7 < num_val < 1e12:
                text = str(int(num_val))
        except (ValueError, OverflowError):
            pass

    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return text

    # +82 국제전화 코드 → 0으로 치환 (예: 821012345678 → 01012345678)
    if digits.startswith("82") and 11 <= len(digits) <= 13:
        digits = "0" + digits[2:]

    # 엑셀이 앞자리 0을 날린 경우 복원
    # 휴대폰: 01012345678 → Excel 숫자 변환 → 1012345678 (10자리, "10"으로 시작)
    if len(digits) == 10 and digits[:2] in ("10", "11", "16", "17", "18", "19"):
        digits = "0" + digits
    # 서울: 0212345678 → 212345678 (9자리) / 021234567 → 21234567 (8자리)
    elif len(digits) in (8, 9) and digits.startswith("2"):
        digits = "0" + digits

    # 휴대폰 11자리: 010-XXXX-XXXX (3-4-4 분할)
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    # 서울 지역번호 02: 9자리(02-XXX-XXXX) 또는 10자리(02-XXXX-XXXX)
    if digits.startswith("02"):
        if len(digits) == 9:
            return f"02-{digits[2:5]}-{digits[5:]}"
        if len(digits) == 10:
            return f"02-{digits[2:6]}-{digits[6:]}"

    # 기타 지역번호 0XX: 10자리(0XX-XXX-XXXX) 또는 11자리(0XX-XXXX-XXXX)
    if digits.startswith("0") and len(digits) in (10, 11):
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    # 어떤 패턴에도 해당하지 않으면 원본 그대로 반환
    return text


def strip_whitespace(text: str) -> str:
    """
    문자열 앞뒤의 불필요한 공백을 제거하고,
    내부의 연속 공백을 단일 공백으로 압축합니다.

    스마트스토어 주문서에서 흔히 발생하는 케이스:
      "  홍길동  "     → "홍길동"
      "서울시  강남구" → "서울시 강남구"

    Args:
        text: 공백을 정리할 원본 문자열

    Returns:
        앞뒤 공백이 제거되고 내부 공백이 압축된 문자열
    """
    if pd.isna(text):
        return ""
    text = str(text).strip()
    return re.sub(r" {2,}", " ", text)
