# -*- coding: utf-8 -*-
"""
app.py — Summit Logic 무료 엑셀 데이터 정제기 (Lead Magnet)
================================================================
스마트스토어 셀러를 위한 무료 엑셀 데이터 정제 도구.
이모지 제거 · 전화번호 자동 포맷 · 공백 정리를 한 번의 클릭으로 처리합니다.

핵심 원칙: Zero-Storage
  → 고객의 주문 데이터를 서버 DB에 절대 저장하지 않고,
    메모리에서 처리 후 즉시 파기합니다.

[배포]  Streamlit Cloud — streamlit run app.py
[구조]  현재 단일 파일이지만, 각 섹션(1~7)은 독립 모듈로 분리 가능합니다.
        → constants / emoji_cleaner / phone_formatter / whitespace_cleaner
          column_detector / dataframe_processor / file_io
          ui_header / ui_stats / ui_cta / ui_styles / ui_security
          validators / analytics / app  (총 15개 모듈 확장 구조)
"""

import re
import zipfile
from io import BytesIO
from typing import List, Tuple

import pandas as pd
import streamlit as st


# ╔═══════════════════════════════════════════════════════════╗
# ║  1. CONSTANTS — 상수 정의                                ║
# ║  → 확장 시 constants.py 로 분리                          ║
# ╚═══════════════════════════════════════════════════════════╝

# 이모지 및 비표준 특수문자를 매칭하는 정규표현식 (모듈 로드 시 1회 컴파일)
# 유니코드 블록 단위로 범위를 지정하여 이모지·제어문자·장식문자를 포괄합니다.
_EMOJI_RE = re.compile(
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
_PHONE_KEYWORDS = [
    "연락처", "전화", "핸드폰", "휴대폰", "휴대전화",
    "phone", "tel", "mobile",
]

# 성함/이름 컬럼 감지 키워드
# 스마트스토어 기준: '수취인명', '주문자명' 등
_NAME_KEYWORDS = [
    "수취인", "이름", "성함", "주문자", "보내는분", "받는분", "name",
]

# 주소 컬럼 감지 키워드
# 스마트스토어 기준: '배송지', '합배송지', '주소' 등
_ADDRESS_KEYWORDS = [
    "주소", "배송지", "합배송지", "address", "addr",
]

# NaN·빈값으로 판별할 문자열 집합 (frozenset으로 O(1) 탐색)
_NULL_STRINGS = frozenset({"nan", "none", "null", "n/a", "-", ""})

# 스마트스토어 엑셀 헤더 행 자동 탐색에 사용할 키워드
# 이 중 2개 이상이 한 행에 존재하면 해당 행을 헤더로 판정합니다.
_HEADER_PROBE_KEYWORDS = [
    "상품주문번호", "주문번호", "수취인명", "수취인",
    "연락처", "배송지", "주소", "상품명", "택배사", "송장번호",
]


# ╔═══════════════════════════════════════════════════════════╗
# ║  1-B. HEADER DETECTION — 헤더 행 자동 탐색               ║
# ║  → 확장 시 validators.py 로 분리                         ║
# ╚═══════════════════════════════════════════════════════════╝

def _find_header_row(file_bytes: bytes, max_scan: int = 20) -> int:
    """
    스마트스토어 엑셀의 실제 헤더 행 위치를 자동 탐색합니다.

    스마트스토어 주문서에는 상단에 "아래 항목을 변경/삭제하지 마세요" 등의
    안내 문구가 1~2행 삽입되어 있어, 단순히 header=0으로 읽으면
    안내 문구가 컬럼명이 되어 모든 키워드 기반 감지가 실패합니다.

    탐색 로직:
      1. header=None으로 원시 데이터 최대 max_scan행 읽기
      2. 각 행에서 _HEADER_PROBE_KEYWORDS와 정확 일치하는 셀 개수 카운트
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
            1 for kw in _HEADER_PROBE_KEYWORDS if cells.eq(kw).any()
        )
        if matches >= 2:
            return int(idx)

    return 0


# ╔═══════════════════════════════════════════════════════════╗
# ║  2. DATA CLEANING — 데이터 정제 핵심 함수                ║
# ║  → 확장 시 emoji_cleaner / phone_formatter /             ║
# ║    whitespace_cleaner 로 각각 분리                       ║
# ╚═══════════════════════════════════════════════════════════╝

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
    text = _EMOJI_RE.sub("", text)
    # 탭·줄바꿈 등 ASCII 제어문자 → 공백 치환
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
    if text.lower() in _NULL_STRINGS:
        return ""

    # 숫자만 추출
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return text

    # +82 국제전화 코드 → 0으로 치환 (예: 821012345678 → 01012345678)
    if digits.startswith("82") and 11 <= len(digits) <= 13:
        digits = "0" + digits[2:]

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


# ╔═══════════════════════════════════════════════════════════╗
# ║  3. COLUMN DETECTION — 컬럼 자동 감지                    ║
# ║  → 확장 시 column_detector.py 로 분리                    ║
# ╚═══════════════════════════════════════════════════════════╝

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
    return _detect_columns_by_keywords(df.columns.tolist(), _PHONE_KEYWORDS)


def detect_name_columns(df: pd.DataFrame) -> List[str]:
    """성함/이름 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    return _detect_columns_by_keywords(df.columns.tolist(), _NAME_KEYWORDS)


def detect_address_columns(df: pd.DataFrame) -> List[str]:
    """주소/배송지 관련 컬럼을 키워드 기반으로 자동 감지합니다."""
    return _detect_columns_by_keywords(df.columns.tolist(), _ADDRESS_KEYWORDS)


# ╔═══════════════════════════════════════════════════════════╗
# ║  4. DATAFRAME PROCESSING — 데이터프레임 일괄 정제        ║
# ║  → 확장 시 dataframe_processor.py 로 분리                ║
# ╚═══════════════════════════════════════════════════════════╝

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
    header_row = _find_header_row(file_bytes)

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

    return df, stats


# ╔═══════════════════════════════════════════════════════════╗
# ║  5. FILE I/O — 파일 입출력                               ║
# ║  → 확장 시 file_io.py 로 분리                            ║
# ╚═══════════════════════════════════════════════════════════╝

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


# ╔═══════════════════════════════════════════════════════════╗
# ║  6. UI COMPONENTS — Streamlit UI 구성요소                ║
# ║  → 확장 시 ui_header / ui_stats / ui_cta / ui_styles /  ║
# ║    ui_security 등으로 분리                               ║
# ╚═══════════════════════════════════════════════════════════╝

def setup_page_config():
    """Streamlit 페이지 메타 설정 (탭 제목, 아이콘, 레이아웃)."""
    st.set_page_config(
        page_title="무료 엑셀 정제기 | Summit Remover",
        page_icon="📦",
        layout="centered",
    )


def inject_custom_css():
    """
    앱 전체에 적용되는 커스텀 CSS를 주입합니다.
    Google Material 디자인 컬러 팔레트와 Noto Sans KR 폰트를 기반으로
    깔끔한 SaaS 스타일 UI를 구성합니다.
    """
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap');

            .main { background-color: #ffffff; }
            body  { font-family: 'Noto Sans KR', sans-serif; }

            /* ── 히어로 헤더 ── */
            .hero-header {
                text-align: center;
                padding: 40px 0 20px;
            }
            .hero-header h1 {
                font-size: 2.2rem;
                font-weight: 900;
                color: #1a1a2e;
                margin-bottom: 8px;
                line-height: 1.4;
            }
            .hero-header .accent { color: #1a73e8; }
            .hero-header p {
                font-size: 1rem;
                color: #5f6368;
                line-height: 1.7;
            }

            /* ── 통계 카드 그리드 ── */
            .stat-grid {
                display: flex;
                gap: 12px;
                margin: 16px 0;
                flex-wrap: wrap;
            }
            .stat-card {
                flex: 1;
                min-width: 120px;
                background: #f8f9fa;
                border: 1px solid #e8eaed;
                border-radius: 12px;
                padding: 18px 14px;
                text-align: center;
            }
            .stat-card .num {
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 4px;
            }
            .stat-card .label {
                font-size: 0.82rem;
                color: #5f6368;
            }
            .stat-emoji  .num { color: #ea4335; }
            .stat-phone  .num { color: #1a73e8; }
            .stat-space  .num { color: #34a853; }
            .stat-total  .num { color: #202124; }

            /* ── CTA 배너 (하단 마케팅 영역) ── */
            .cta-box {
                background: linear-gradient(135deg, #1a73e8, #174ea6);
                border-radius: 16px;
                padding: 32px 24px;
                text-align: center;
                margin: 32px 0 16px;
            }
            .cta-box h3 {
                color: #ffffff;
                font-size: 1.15rem;
                font-weight: 700;
                margin-bottom: 8px;
                line-height: 1.6;
            }
            .cta-box p {
                color: #d2e3fc;
                font-size: 0.9rem;
                line-height: 1.6;
                margin-bottom: 16px;
            }
            .cta-box .highlight {
                color: #fbbc04;
                font-weight: 700;
                font-size: 1.3rem;
            }
            .cta-btn {
                display: inline-block;
                background: #ffffff;
                color: #1a73e8;
                font-weight: 700;
                font-size: 1rem;
                padding: 12px 36px;
                border-radius: 28px;
                text-decoration: none;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .cta-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }

            /* ── Zero-Storage 보안 카드 ── */
            .zero-storage-card {
                background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
                border: 1px solid #c8e6c9;
                border-radius: 16px;
                padding: 28px 24px;
                margin: 8px 0 8px;
            }
            .zero-storage-card .zs-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #1b5e20;
                margin-bottom: 16px;
                text-align: center;
            }
            .trust-flow {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 8px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            .trust-step {
                background: #ffffff;
                border: 1px solid #c8e6c9;
                border-radius: 12px;
                padding: 16px 14px;
                text-align: center;
                min-width: 130px;
                flex: 1;
                max-width: 180px;
            }
            .trust-step .step-icon {
                font-size: 1.8rem;
                margin-bottom: 6px;
            }
            .trust-step .step-label {
                font-size: 0.78rem;
                font-weight: 600;
                color: #2e7d32;
            }
            .trust-step .step-desc {
                font-size: 0.7rem;
                color: #5f6368;
                margin-top: 2px;
            }
            .trust-arrow {
                font-size: 1.3rem;
                color: #81c784;
                font-weight: 700;
            }
            .zs-badges {
                display: flex;
                justify-content: center;
                gap: 24px;
                margin-top: 16px;
                flex-wrap: wrap;
            }
            .zs-badge {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 0.78rem;
                color: #2e7d32;
                font-weight: 600;
            }

            /* ── 업로드 대기 플레이스홀더 ── */
            .upload-placeholder {
                background: #f8f9fa;
                border: 1px dashed #dadce0;
                border-radius: 12px;
                padding: 40px;
                text-align: center;
                color: #5f6368;
                margin: 20px 0;
            }

            /* ── 다운로드 버튼 강조 ── */
            div[data-testid="stDownloadButton"] button {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 24px;
                padding: 12px 32px;
                font-size: 1rem;
                font-weight: 600;
                width: 100%;
                cursor: pointer;
                transition: background 0.2s;
            }
            div[data-testid="stDownloadButton"] button:hover {
                background-color: #1558b0;
            }

            /* ── 푸터 ── */
            .footer {
                text-align: center;
                color: #bdc1c6;
                font-size: 0.78rem;
                padding: 24px 0 12px;
            }

            /* ── 모바일 반응형 ── */
            @media (max-width: 640px) {
                .hero-header h1 { font-size: 1.5rem; }
                .stat-grid { flex-direction: column; }
                .stat-card { min-width: 100%; }
                .stat-card .num { font-size: 1.4rem; }
                .trust-flow { flex-direction: column; gap: 4px; }
                .trust-arrow { transform: rotate(90deg); }
                .trust-step { max-width: 100%; min-width: 100%; }
                .zs-badges { flex-direction: column; gap: 8px; align-items: center; }
                .cta-box { padding: 24px 16px; }
                .cta-box .highlight { font-size: 1.1rem; }
                .cta-btn { padding: 10px 24px; font-size: 0.9rem; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """앱 최상단 히어로 헤더를 렌더링합니다."""
    st.markdown(
        """
        <div class="hero-header">
            <h1>
                📦 <span class="accent">송장 에러 1초 해결</span>:<br>
                무료 엑셀 정제기
            </h1>
            <p>
                스마트스토어 주문서의 이모지, 전화번호 오류, 불필요한 공백을<br>
                한 번의 클릭으로 깨끗하게 정리합니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_security_banner():
    """
    Zero-Storage 철학을 시각적으로 강조하는 보안 신뢰 컴포넌트를 렌더링합니다.

    구성 요소:
      1. st.warning 배너 — 핵심 메시지 (스크롤 중에도 눈에 띄는 노란색)
      2. Zero-Storage 카드 — 데이터 흐름 3단계 시각화
         (업로드 → 메모리 처리 → 즉시 파기)
      3. 신뢰 배지 — DB 없음 / HTTPS 암호화 / 제3자 미제공
    """
    st.warning(
        "🛡️ **Zero-Storage 보안 원칙:** "
        "저희는 고객 데이터를 서버에 **절대 저장하지 않습니다.** "
        "모든 데이터는 메모리(RAM)에서 처리 후 즉시 파기됩니다."
    )
    st.markdown(
        """
        <div class="zero-storage-card">
            <div class="zs-title">🔐 데이터는 이렇게 처리됩니다</div>
            <div class="trust-flow">
                <div class="trust-step">
                    <div class="step-icon">📤</div>
                    <div class="step-label">1. 파일 업로드</div>
                    <div class="step-desc">HTTPS 암호화 전송</div>
                </div>
                <div class="trust-arrow">→</div>
                <div class="trust-step">
                    <div class="step-icon">⚡</div>
                    <div class="step-label">2. 메모리 처리</div>
                    <div class="step-desc">RAM에서만 정제</div>
                </div>
                <div class="trust-arrow">→</div>
                <div class="trust-step">
                    <div class="step-icon">🗑️</div>
                    <div class="step-label">3. 즉시 파기</div>
                    <div class="step-desc">처리 후 완전 삭제</div>
                </div>
            </div>
            <div class="zs-badges">
                <div class="zs-badge">🚫 DB 저장 없음</div>
                <div class="zs-badge">🔒 HTTPS 암호화</div>
                <div class="zs-badge">👤 제3자 미제공</div>
                <div class="zs-badge">📋 로그 기록 없음</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stats(stats: dict):
    """
    데이터 정제 결과 통계를 시각적 카드 4장으로 표시합니다.
    (전체 행 수 / 이모지 제거 건수 / 전화번호 포맷 건수 / 공백 정리 건수)
    """
    st.markdown(
        f"""
        <div class="stat-grid">
            <div class="stat-card stat-total">
                <div class="num">{stats['total_rows']}</div>
                <div class="label">전체 행 수</div>
            </div>
            <div class="stat-card stat-emoji">
                <div class="num">{stats['emoji_removed']}</div>
                <div class="label">🧹 이모지 제거</div>
            </div>
            <div class="stat-card stat-phone">
                <div class="num">{stats['phone_formatted']}</div>
                <div class="label">📞 전화번호 포맷</div>
            </div>
            <div class="stat-card stat-space">
                <div class="num">{stats['whitespace_trimmed']}</div>
                <div class="label">✂️ 공백 정리</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detected_columns(stats: dict):
    """
    자동 감지된 전화번호·성함·주소 컬럼 목록을
    3열 레이아웃으로 펼쳐 보여줍니다.
    셀러가 올바른 컬럼이 감지되었는지 확인할 수 있습니다.
    """
    with st.expander("🔍 자동 감지된 컬럼 확인", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📞 전화번호 컬럼**")
            if stats["phone_columns"]:
                for c in stats["phone_columns"]:
                    st.caption(f"✅ {c}")
            else:
                st.caption("감지된 컬럼 없음")
        with col2:
            st.markdown("**👤 성함 컬럼**")
            if stats["name_columns"]:
                for c in stats["name_columns"]:
                    st.caption(f"✅ {c}")
            else:
                st.caption("감지된 컬럼 없음")
        with col3:
            st.markdown("**📍 주소 컬럼**")
            if stats["address_columns"]:
                for c in stats["address_columns"]:
                    st.caption(f"✅ {c}")
            else:
                st.caption("감지된 컬럼 없음")


def render_cta():
    """
    하단 마케팅 CTA(Call-To-Action) 영역을 렌더링합니다.
    써밋로직 본 제품으로의 전환을 유도하는 핵심 마케팅 메시지입니다.
    """
    st.markdown(
        """
        <div class="cta-box">
            <h3>아직도 합배송을 수동으로 하시나요?</h3>
            <p>
                써밋로직 V3.1로<br>
                <span class="highlight">매달 27만 원</span>의 배송비를 아끼세요!
            </p>
            <a class="cta-btn"
               href="https://summit-logic-main.streamlit.app"
               target="_blank">
                🚀 써밋로직 V3.1 바로가기
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_privacy_notice():
    """
    CTA 아래, 푸터 위에 배치되는 개인정보 보호 상세 안내 섹션.
    법적 신뢰감을 주는 공식적 어조로 작성되었습니다.
    """
    with st.expander("🔒 개인정보 처리 방침 상세", expanded=False):
        st.markdown(
            """
            **Summit Remover 데이터 처리 원칙**

            | 항목 | 내용 |
            |------|------|
            | **서버 저장** | 업로드된 파일은 어떠한 서버·DB에도 저장되지 않습니다 |
            | **처리 방식** | 모든 데이터는 서버 메모리(RAM)에서만 처리됩니다 |
            | **즉시 파기** | 정제 완료 즉시 메모리에서 완전히 삭제됩니다 |
            | **전송 보안** | 모든 통신은 TLS/HTTPS로 암호화됩니다 |
            | **제3자 제공** | 개인정보를 외부에 제공하거나 판매하지 않습니다 |
            | **로그 기록** | 업로드 파일의 내용을 로그로 기록하지 않습니다 |
            """
        )


def render_footer():
    """앱 최하단 푸터를 렌더링합니다. Zero-Storage 원칙을 다시 한번 명시합니다."""
    st.markdown(
        """
        <div class="footer">
            Summit Remover &nbsp;|&nbsp;
            summit-remover.com<br>
            Zero-Storage 원칙: 업로드된 파일은 서버에 저장되지 않으며
            처리 즉시 메모리에서 삭제됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ╔═══════════════════════════════════════════════════════════╗
# ║  7. MAIN — 앱 진입점                                     ║
# ║  → Streamlit 실행 흐름을 제어하는 최상위 함수            ║
# ╚═══════════════════════════════════════════════════════════╝

def main():
    """
    Streamlit 앱 메인 실행 함수.

    실행 흐름:
      1. 페이지 설정 → CSS 주입 → 헤더/보안 배너 렌더링
      2. 파일 업로드 대기
      3. 업로드 감지 시 → clean_dataframe() 파이프라인 실행
      4. 통계·미리보기·다운로드 버튼 표시
      5. 하단 CTA + 푸터 렌더링
    """
    setup_page_config()
    inject_custom_css()
    render_header()
    render_security_banner()

    st.markdown("---")

    # ── 파일 업로드 위젯 ──
    uploaded_file = st.file_uploader(
        "스마트스토어 주문서 (Excel) 업로드",
        type=["xlsx"],
        help="네이버 스마트스토어에서 다운로드한 주문 엑셀(.xlsx) 파일을 올려주세요.",
    )

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()

            with st.spinner("🔄 데이터를 정제하고 있습니다..."):
                cleaned_df, stats = clean_dataframe(file_bytes)

            # ── 헤더 행 탐색 결과 안내 (0이 아닌 경우만 표시) ──
            if stats.get("header_row_detected", 0) > 0:
                st.info(
                    f"📌 엑셀 상단의 안내 문구를 감지하여 "
                    f"**{stats['header_row_detected'] + 1}행**을 "
                    f"컬럼 헤더로 사용했습니다."
                )

            # ── 컬럼 미감지 경고 ──
            no_phone = len(stats["phone_columns"]) == 0
            no_name = len(stats["name_columns"]) == 0
            no_addr = len(stats["address_columns"]) == 0
            if no_phone and no_name and no_addr:
                st.warning(
                    "⚠️ 전화번호·성함·주소 컬럼을 자동 감지하지 못했습니다. "
                    "이모지 제거만 수행되었습니다. "
                    "스마트스토어에서 다운로드한 원본 엑셀 파일인지 확인해 주세요."
                )
            elif no_phone:
                st.warning(
                    "⚠️ 전화번호 컬럼을 감지하지 못했습니다. "
                    "전화번호 포맷 정제가 생략되었습니다."
                )

            # ── 처리 완료 메시지 ──
            st.success(
                f"✅ 정제 완료! "
                f"{stats['total_rows']}개 행에서 "
                f"이모지 {stats['emoji_removed']}건, "
                f"전화번호 {stats['phone_formatted']}건, "
                f"공백 {stats['whitespace_trimmed']}건을 처리했습니다."
            )

            # ── 통계 카드 (4장) ──
            render_stats(stats)

            # ── 자동 감지 컬럼 확인 (접이식) ──
            render_detected_columns(stats)

            # ── 정제 결과 미리보기 ──
            with st.expander("📋 정제 결과 미리보기", expanded=True):
                st.dataframe(cleaned_df, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── 다운로드 버튼 ──
            excel_bytes = to_excel_bytes(cleaned_df)
            original_name = uploaded_file.name.rsplit(".", 1)[0]
            st.download_button(
                label="⬇️  정제된 엑셀 파일 다운로드",
                data=excel_bytes,
                file_name=f"{original_name}_정제완료.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        except ValueError as ve:
            st.error(f"⚠️ {ve}")
        except zipfile.BadZipFile:
            st.error(
                "⚠️ 이 파일을 열 수 없습니다.\n\n"
                "**가능한 원인:**\n"
                "- 비밀번호로 보호된 엑셀 파일\n"
                "- 손상된 파일\n"
                "- .xlsx가 아닌 다른 형식의 파일\n\n"
                "스마트스토어에서 다시 다운로드하거나, "
                "엑셀에서 열어 **다른 이름으로 저장**한 뒤 다시 업로드해 주세요."
            )
        except Exception as e:
            st.error(f"⚠️ 파일 처리 중 오류가 발생했습니다: {e}")
            with st.expander("오류 상세"):
                st.exception(e)

    else:
        # 파일 미업로드 상태 — 안내 플레이스홀더
        st.markdown(
            """
            <div class="upload-placeholder">
                <span style="font-size:2.5rem;">📂</span><br><br>
                <b>스마트스토어 주문서 엑셀 파일을 업로드해 주세요</b><br>
                <small>xlsx 형식 지원 · 데이터 서버 저장 없음</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 하단 CTA + 개인정보 방침 + 푸터 ──
    st.markdown("---")
    render_cta()
    render_privacy_notice()
    render_footer()


# ── 엔트리 포인트 ──
if __name__ == "__main__":
    main()
