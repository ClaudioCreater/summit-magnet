# -*- coding: utf-8 -*-
"""
utils/detectors.py — 헤더 행 탐색 및 컬럼 자동 감지

전화번호·성함·주소 컬럼이 서로 중복 매핑되지 않도록
상호 배제(Mutual Exclusion) 로직을 포함합니다.
"""

from io import BytesIO
from typing import Dict, List

import pandas as pd
import re

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


def _keyword_score(col_name: str, keywords: List[str]) -> float:
    """컬럼명에 키워드가 포함되어 있는지 여부를 0.0~1.0 스코어로 반환합니다."""
    col_lower = str(col_name).lower()
    return 1.0 if any(kw.lower() in col_lower for kw in keywords) else 0.0


PHONE_PREFIXES = ("010", "011", "016", "017", "018", "019")


def _phone_content_score(series: pd.Series) -> float:
    """
    전화번호 패턴 일치율을 0.0~1.0 스코어로 계산합니다.

    규칙:
      - 값에서 숫자만 추출
      - 10~11자리이며 010/011/016/017/018/019 등으로 시작하면 '전화번호'로 간주
    """
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0.0
    sample = values.head(100)
    total = len(sample)
    if total == 0:
        return 0.0

    matches = 0
    for v in sample:
        digits = re.sub(r"[^0-9]", "", v)
        if len(digits) in (10, 11) and digits.startswith(PHONE_PREFIXES):
            matches += 1
    return matches / total


def _name_content_score(series: pd.Series) -> float:
    """
    '성함' 컬럼일 가능성을 0.0~1.0 스코어로 계산합니다.

    규칙:
      - 숫자가 포함되지 않고
      - 길이가 2~5자인 셀 비율을 사용
    """
    values = series.dropna().astype(str).str.strip()
    if values.empty:
        return 0.0
    sample = values.head(100)
    total = len(sample)
    if total == 0:
        return 0.0

    matches = 0
    for v in sample:
        if any(ch.isdigit() for ch in v):
            continue
        length = len(v)
        if 2 <= length <= 5:
            matches += 1
    return matches / total


def _classify_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    각 컬럼을 phone / name / address 중 하나로 분류합니다.

    - 하나의 컬럼은 최대 1개 역할만 가질 수 있습니다. (상호 배제)
    - 스코어 구성:
        phone_score   = 0.6 * 전화번호 패턴 일치율 + 0.4 * 전화번호 키워드 스코어
        name_score    = 0.6 * 성함 패턴 일치율   + 0.4 * 성함 키워드 스코어
        address_score = 1.0 * 주소 키워드 스코어 (내용 기반 분석은 생략)
    - 충돌 시 우선순위:
        1) 더 높은 스코어
        2) 스코어 동률이면 phone > name > address
    """
    role_map: Dict[str, str] = {}

    for col in df.columns:
        series = df[col]

        phone_score = 0.6 * _phone_content_score(series) + 0.4 * _keyword_score(
            col, PHONE_KEYWORDS
        )
        name_score = 0.6 * _name_content_score(series) + 0.4 * _keyword_score(
            col, NAME_KEYWORDS
        )
        address_score = 1.0 * _keyword_score(col, ADDRESS_KEYWORDS)

        scores = {
            "phone": phone_score,
            "name": name_score,
            "address": address_score,
        }

        # 가장 높은 스코어를 가진 역할 선택
        max_score = max(scores.values())
        if max_score <= 0.0:
            # 어떤 역할에도 설득력 있는 스코어가 없으면 분류하지 않음
            continue

        # 전화번호 > 성함 > 주소 우선순위로 동점 처리
        if scores["phone"] == max_score:
            role = "phone"
        elif scores["name"] == max_score:
            role = "name"
        else:
            role = "address"

        role_map[col] = role

    return role_map


def detect_phone_columns(df: pd.DataFrame) -> List[str]:
    """
    전화번호 컬럼을 감지합니다.

    - 전화번호 패턴 + 키워드 기반 스코어를 사용
    - 한 번 전화번호로 분류된 컬럼은 성함/주소에서 자동 제외됩니다.
    """
    role_map = _classify_columns(df)
    return [col for col, role in role_map.items() if role == "phone"]


def detect_name_columns(df: pd.DataFrame) -> List[str]:
    """
    성함 컬럼을 감지합니다.

    - 전화번호/주소와 상호 배제
    - 이름 길이(2~5자)·숫자 포함 여부 기반 스코어를 사용
    """
    role_map = _classify_columns(df)
    return [col for col, role in role_map.items() if role == "name"]


def detect_address_columns(df: pd.DataFrame) -> List[str]:
    """
    주소/배송지 컬럼을 감지합니다.

    - 전화번호/성함과 상호 배제
    - 현재는 컬럼명 키워드 기반으로만 스코어링
    """
    role_map = _classify_columns(df)
    return [col for col, role in role_map.items() if role == "address"]


def detect_order_columns(df: pd.DataFrame) -> List[str]:
    """주문번호 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    columns = df.columns.tolist()
    matched: List[str] = []
    for col in columns:
        col_lower = str(col).lower()
        if any(kw.lower() in col_lower for kw in ORDER_KEYWORDS):
            matched.append(col)
    return matched
