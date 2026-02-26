# -*- coding: utf-8 -*-
"""
core/processor.py — 데이터프레임 일괄 정제 및 파일 I/O
  clean_dataframe · to_excel_bytes
"""

from io import BytesIO
from typing import Tuple

import pandas as pd
import streamlit as st

from utils.cleaners import format_phone_number, remove_emoji, strip_whitespace
from utils.detectors import (
    detect_address_columns,
    detect_name_columns,
    detect_order_columns,
    detect_phone_columns,
    find_header_row,
)


@st.cache_data(show_spinner=False)
def clean_dataframe(
    file_bytes: bytes, sheet_name: int = 0
) -> Tuple[pd.DataFrame, dict]:
    """
    업로드된 엑셀 파일의 바이트를 받아 전체 정제 파이프라인을 실행합니다.

    처리 순서:
      Step 0. 헤더 행 자동 탐색 (스마트스토어 안내 문구 행 스킵)
      Step 1. 모든 셀 → 이모지·비표준 특수문자 제거
      Step 2. 전화번호 컬럼 자동 감지 → 하이픈 포맷(010-0000-0000) 적용
      Step 3. 성함 컬럼 → 앞뒤 공백 제거
      Step 4. 주소 컬럼 → 앞뒤 공백 제거

    @st.cache_data 적용:
      동일한 file_bytes 해시가 입력되면 캐시된 결과를 즉시 반환합니다.
      업로드 파일이 변경되지 않는 한 재처리하지 않아 자원 효율성이 높아집니다.

    Args:
        file_bytes:  업로드된 엑셀 파일의 바이트 데이터
        sheet_name:  읽을 시트 인덱스 (기본값: 첫 번째 시트)

    Returns:
        Tuple[pd.DataFrame, dict]:
          - 정제가 완료된 DataFrame (원본 컬럼 구조 유지)
          - 처리 통계 딕셔너리 (행 수, 컬럼 수, 각 정제 항목별 처리 건수)

    Raises:
        ValueError: 데이터가 비어있는 경우
    """
    # ── Step 0: 헤더 행 자동 탐색 ──
    header_row = find_header_row(file_bytes)

    df = pd.read_excel(
        BytesIO(file_bytes),
        sheet_name=sheet_name,
        header=header_row,
        dtype=str,
    )
    df = df.fillna("")

    # 빈 행·헤더 잔재 제거: 모든 셀이 비어있는 행 삭제
    df = df[~df.apply(lambda r: all(v.strip() == "" for v in r), axis=1)]
    df = df.reset_index(drop=True)

    if len(df) == 0:
        raise ValueError(
            "업로드한 파일에 데이터가 없습니다.\n"
            "엑셀 파일에 주문 데이터가 포함되어 있는지 확인해 주세요."
        )

    original_df = df.copy()

    stats = {
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "header_row_detected": header_row,
        "emoji_removed": 0,
        "phone_formatted": 0,
        "whitespace_trimmed": 0,
        "phone_columns": [],
        "name_columns": [],
        "address_columns": [],
    }

    # ── Step 1: 모든 셀에서 이모지·비표준 특수문자 제거 ──
    for col in df.columns:
        before = df[col].copy()
        df[col] = df[col].apply(remove_emoji)
        stats["emoji_removed"] += int((before != df[col]).sum())

    # ── Step 2: 전화번호 컬럼 감지 → 하이픈 포맷 적용 ──
    phone_cols = detect_phone_columns(df)
    stats["phone_columns"] = phone_cols
    for col in phone_cols:
        before = df[col].copy()
        df[col] = df[col].apply(format_phone_number)
        stats["phone_formatted"] += int((before != df[col]).sum())

    # ── Step 3: 성함 컬럼 공백 정리 ──
    name_cols = detect_name_columns(df)
    stats["name_columns"] = name_cols
    for col in name_cols:
        before = df[col].copy()
        df[col] = df[col].apply(strip_whitespace)
        stats["whitespace_trimmed"] += int((before != df[col]).sum())

    # ── Step 4: 주소 컬럼 공백 정리 ──
    address_cols = detect_address_columns(df)
    stats["address_columns"] = address_cols
    for col in address_cols:
        before = df[col].copy()
        df[col] = df[col].apply(strip_whitespace)
        stats["whitespace_trimmed"] += int((before != df[col]).sum())

    # ── Step 5: 주문번호 중복 감지 (삭제하지 않고 정보만 제공) ──
    order_cols = detect_order_columns(df)
    stats["order_columns"] = order_cols
    duplicate_count = 0
    if order_cols:
        duplicate_count = int(df[order_cols[0]].duplicated().sum())
    stats["duplicate_orders"] = duplicate_count

    # ── Step 6: 변경 내역 생성 (before/after 비교, 최대 50건) ──
    changes: list = []
    total_changes = 0
    for col in df.columns:
        mask = original_df[col] != df[col]
        total_changes += int(mask.sum())
        if len(changes) < 50:
            for idx in df.index[mask]:
                if len(changes) >= 50:
                    break
                changes.append({
                    "행": idx + 1,
                    "컬럼": col,
                    "변경 전": original_df.at[idx, col],
                    "변경 후": df.at[idx, col],
                })
    stats["changes_preview"] = changes
    stats["total_changes"] = total_changes

    return df, stats


def to_excel_bytes(
    df: pd.DataFrame, sheet_name: str = "정제완료"
) -> bytes:
    """
    DataFrame을 .xlsx 바이트로 변환합니다.

    openpyxl 엔진을 사용하며, 원본 컬럼 구조(컬럼명·순서)를
    그대로 유지합니다. 인덱스는 포함하지 않습니다.

    Args:
        df:         변환할 DataFrame
        sheet_name: 시트 이름 (기본값: "정제완료")

    Returns:
        .xlsx 형식의 바이트 데이터 (st.download_button의 data 인자로 사용)
    """
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()
