# -*- coding: utf-8 -*-
"""
utils/detectors.py — 헤더 행 탐색 및 컬럼 자동 감지
"""

from io import BytesIO
from typing import List

import pandas as pd

from utils.constants import (
    ADDRESS_KEYWORDS,
    HEADER_PROBE_KEYWORDS,
    NAME_KEYWORDS,
    ORDER_KEYWORDS,
    PHONE_KEYWORDS,
)


def find_header_row(file_bytes: bytes, max_scan: int = 20) -> int:
    """
    스마트스토어 엑셀의 실제 헤더 행 위치를 자동 탐색합니다.

    스마트스토어 주문서에는 상단에 "아래 항목을 변경/삭제하지 마세요" 등의
    안내 문구가 1~2행 삽입되어 있어, 단순히 header=0으로 읽으면
    안내 문구가 컬럼명이 되어 모든 키워드 기반 감지가 실패합니다.

    탐색 로직:
      1. header=None으로 원시 데이터 최대 max_scan행 읽기
      2. 각 행에서 HEADER_PROBE_KEYWORDS와 정확 일치하는 셀 개수 카운트
      3. 2개 이상 일치하는 첫 번째 행을 헤더로 판정
      4. 키워드 불일치 시 0 반환 (일반 엑셀 파일 호환)

    Args:
        file_bytes: 엑셀 파일 바이트
        max_scan:   탐색할 최대 행 수 (기본 20행, 성능 보호)

    Returns:
        헤더 행의 0-based 인덱스
    """
    try:
        df_raw = pd.read_excel(
            BytesIO(file_bytes), header=None, dtype=str, nrows=max_scan
        )
    except Exception:
        return 0

    for idx, row in df_raw.iterrows():
        cells = row.astype(str).str.strip()
        matches = sum(
            1 for kw in HEADER_PROBE_KEYWORDS if cells.eq(kw).any()
        )
        if matches >= 2:
            return int(idx)

    return 0


def _detect_columns_by_keywords(
    columns: List[str], keywords: List[str]
) -> List[str]:
    """
    DataFrame 컬럼명 리스트에서 특정 키워드가 포함된 컬럼을 찾습니다.

    대소문자를 무시하고 부분 일치(substring match)로 검색합니다.
    예) 키워드="연락처" → "수취인연락처1", "주문자연락처" 모두 매칭

    Args:
        columns:  DataFrame.columns를 리스트로 변환한 값
        keywords: 매칭할 키워드 목록

    Returns:
        키워드가 포함된 컬럼명 리스트 (순서 유지)
    """
    matched = []
    for col in columns:
        col_lower = str(col).lower()
        if any(kw.lower() in col_lower for kw in keywords):
            matched.append(col)
    return matched


def detect_phone_columns(df: pd.DataFrame) -> List[str]:
    """전화번호 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    return _detect_columns_by_keywords(df.columns.tolist(), PHONE_KEYWORDS)


def detect_name_columns(df: pd.DataFrame) -> List[str]:
    """성함/이름 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    return _detect_columns_by_keywords(df.columns.tolist(), NAME_KEYWORDS)


def detect_address_columns(df: pd.DataFrame) -> List[str]:
    """주소/배송지 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    return _detect_columns_by_keywords(df.columns.tolist(), ADDRESS_KEYWORDS)


def detect_order_columns(df: pd.DataFrame) -> List[str]:
    """주문번호 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    return _detect_columns_by_keywords(df.columns.tolist(), ORDER_KEYWORDS)
