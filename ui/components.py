# -*- coding: utf-8 -*-
"""
ui/components.py — Streamlit UI 구성요소
  페이지 설정 · CSS · 헤더 · 보안 배너 · 통계 · CTA · 개인정보 · 푸터
"""

import pandas as pd
import streamlit as st


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


def render_changes_preview(stats: dict):
    """변경 내역 before/after 미리보기를 표시합니다."""
    changes = stats.get("changes_preview", [])
    total = stats.get("total_changes", 0)
    if not changes:
        return
    label = f"🔎 변경 내역 상세 — 총 {total}건"
    if len(changes) < total:
        label += f" 중 상위 {len(changes)}건 표시"
    with st.expander(label, expanded=False):
        st.dataframe(
            pd.DataFrame(changes),
            use_container_width=True,
            hide_index=True,
        )


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
               href="https://summitlogic.streamlit.app"
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
