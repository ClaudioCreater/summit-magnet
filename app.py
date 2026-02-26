# -*- coding: utf-8 -*-
"""
app.py — Summit Remover 무료 엑셀 데이터 정제기 (Lead Magnet)
================================================================
스마트스토어 셀러를 위한 무료 엑셀 데이터 정제 도구.
이모지 제거 · 전화번호 자동 포맷 · 공백 정리를 한 번의 클릭으로 처리합니다.

핵심 원칙: Zero-Storage
  → 고객의 주문 데이터를 서버 DB에 절대 저장하지 않고,
    메모리에서 처리 후 즉시 파기합니다.

[배포]  Streamlit Cloud — streamlit run app.py
[구조]
  app.py              ← 메인 진입점 (이 파일)
  utils/constants.py  ← 상수·정규표현식
  utils/cleaners.py   ← 이모지·전화번호·공백 정제 함수
  utils/detectors.py  ← 헤더 탐색·컬럼 자동 감지
  core/processor.py   ← 데이터프레임 정제 파이프라인·파일 I/O
  ui/components.py    ← Streamlit UI 렌더링 함수
"""

import time
import zipfile

import streamlit as st

from core.processor import clean_dataframe, to_excel_bytes
from ui.components import (
    inject_custom_css,
    render_changes_preview,
    render_cta,
    render_detected_columns,
    render_footer,
    render_header,
    render_privacy_notice,
    render_security_banner,
    render_stats,
    render_founder_story,
    setup_page_config,
)


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
        "물류 데이터 (스마트스토어 주문서) 업로드",
        type=["xlsx"],
        help="써밋로직 자동화를 위한 첫 단계입니다. 네이버 스마트스토어에서 다운로드한 주문 엑셀(.xlsx) 파일을 올려주세요.",
    )

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()

            st.info("📡 사장님의 엑셀 노가다를 끝내기 위한 데이터를, 안전하게 가져오고 있습니다.")

            with st.spinner("🔄 물류 데이터 수집 및 정제 준비 중입니다... (이모지·전화번호·공백 점검)"):
                t0 = time.time()
                cleaned_df, stats = clean_dataframe(file_bytes)
                elapsed = time.time() - t0

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
                f"✅ 정제 완료! ({elapsed:.1f}초) "
                f"{stats['total_rows']}개 행에서 총 "
                f"**{stats['total_changes']}건** 수정 — "
                f"이모지 {stats['emoji_removed']}건, "
                f"전화번호 {stats['phone_formatted']}건, "
                f"공백 {stats['whitespace_trimmed']}건"
            )

            # ── 중복 주문 감지 알림 ──
            if stats.get("duplicate_orders", 0) > 0:
                st.info(
                    f"📋 주문번호 기준 **{stats['duplicate_orders']}건**의 "
                    f"중복 행이 감지되었습니다. "
                    f"(데이터는 삭제하지 않고 그대로 유지합니다)"
                )

            # ── 통계 카드 (4장) ──
            render_stats(stats)

            # ── 변경 내역 before/after ──
            render_changes_preview(stats)

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
                <b>Summit Logic 자동화를 위한 물류 데이터를 업로드해 주세요</b><br>
                <small>xlsx 형식 지원 · 데이터 서버 저장 없음</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 하단 CTA + 개인정보 방침 + 창업자 스토리 + 푸터 ──
    st.markdown("---")
    render_cta()
    render_privacy_notice()
    render_founder_story()
    render_footer()


# ── 엔트리 포인트 ──
if __name__ == "__main__":
    main()
