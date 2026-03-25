import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io
import os
import re

# --- 1. 기본 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v12.0", layout="wide")

# 세션 데이터 초기화 (다중 경쟁사 대응)
states = ['brand_analysis', 'brand_insight', 'comp_list', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = [] if 'data' in key or 'list' in key else ""

# --- 2. 사이드바 (API 설정 및 단계 관리) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 (Thesis)", 
        "STEP 1.5. 경쟁사 Deep-Dive", 
        "STEP 2. 소비자 데이터 (Antithesis)", 
        "STEP 3. 변증법적 전략 도출 (Synthesis)"
    ])
    st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if len(st.session_state['comp_list']) > 0 else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 정반합(正反合) 분석 엔진 ---
def analyze_dialectics(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        # 스팸 필터링 및 정반합 로직 포함 프롬프트
        base_guide = "자기소개 금지. 광고 대행사의 '정반합 변증법'적 사고로 분석하세요. 광고/스팸성 게시물 데이터는 무시하고 실제 목소리만 필터링하세요."
        
        prompts = {
            "brand": f"{base_guide}\n[Thesis: 자사의 주장] 브랜드의 지향점과 이전 운영 인사이트를 대조하여 현재의 '자사 페르소나'를 정의하세요. 인사이트: {insight}",
            "comp": f"{base_guide}\n[Comparison] 지정된 경쟁사 브랜드들의 소구 워딩을 비교 매트릭스 형태로 정리하세요. 자사가 선점하지 못한 영역을 발굴하세요.",
            "consumer": f"{base_guide}\n[Antithesis: 현장의 반론] 소비자의 '날것의 불평'과 '막연한 불안'을 수집 데이터의 빈도수에 기반해 분석하세요. 전문 용어 대신 소비자의 언어를 사용하세요.",
            "synthesis": f"{base_guide}\n[Synthesis: 정반합 합치] 자사의 주장(정)과 소비자의 결핍/경쟁사의 점유(반)를 충돌시켜, 이를 모두 해소하는 '제3의 필승 전략'을 도출하세요."
        }
        
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:10000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 안정적인 PDF 생성 엔진 (None 방지) ---
def generate_master_pdf(export_list):
    pdf = FPDF()
    _ = pdf.set_auto_page_break(auto=True, margin=15)
    _ = pdf.add_page()
    
    f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
    has_font = os.path.exists(f_reg) and os.path.exists(f_bold)
    
    if has_font:
        _ = pdf.add_font('NG', '', f_reg); _ = pdf.add_font('NG', 'B', f_bold); _ = pdf.set_font('NG', size=11)
    else: _ = pdf.set_font("Arial", size=10)

    _ = pdf.set_text_color(0, 51, 102); _ = pdf.set_font('NG', 'B', 18) if has_font else _ = pdf.set_font("Arial", 'B', 14)
    _ = pdf.cell(0, 15, txt="The Hegelian Strategic Report", ln=True, align='C'); _ = pdf.ln(5)

    for title, body in export_list:
        if body:
            _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font('NG', 'B', 13) if has_font else _ = pdf.set_font("Arial", 'B', 11)
            _ = pdf.cell(0, 10, txt=f"> {title}", ln=True, fill=True); _ = pdf.ln(3)
            _ = pdf.set_font('NG', '', 10) if has_font else _ = pdf.set_font("Arial", size=10); _ = pdf.set_text_color(50, 50, 50)
            safe_text = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-').replace('|', ' ')
            _ = pdf.multi_cell(0, 7, txt=safe_text); _ = pdf.ln(8)
            
    return bytes(pdf.output())

# --- 5. 단계별 실행 로직 ---

if menu == "STEP 1. 자사 분석 (Thesis)":
    st.title("🏢 STEP 1. 자사 분석 및 운영 인사이트")
    u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 피드백 (이전에 안 통했던 소구 등)", value=st.session_state['brand_insight'])
    if st.button("분석 실행"):
        with st.spinner("자사 데이터 분석 중..."):
            st.session_state['brand_analysis'] = analyze_dialectics(u + "\n" + st.session_state['brand_insight'], "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 Deep-Dive":
    st.title("⚔️ STEP 1.5. 경쟁사 다중 비교 분석")
    st.info("비교하고 싶은 경쟁사 브랜드/제품명을 최대 3개까지 입력하세요.")
    c_names = st.text_input("경쟁사 명칭 (쉼표 구분)", placeholder="브랜드A, 브랜드B, 브랜드C")
    if st.button("경쟁사 정밀 탐색"):
        with st.spinner("경쟁사 소구점 매핑 중..."):
            comp_results = []
            for name in [n.strip() for n in c_names.split(",")]:
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{name} 특징 마케팅 소구점", "gl": "kr", "hl": "ko"}).json()
                comp_results.append(f"[{name} 정보]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])]))
            st.session_state['comp_list'] = c_names.split(",")
            st.session_state['comp_analysis'] = analyze_dialectics("\n".join(comp_results), "comp")
            _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 데이터 (Antithesis)":
    st.title("👥 STEP 2. 소비자 리얼 데이터 및 팩트 체크")
    kw = st.text_input("키워드")
    ex = st.text_input("제외 키워드", value="항공, 일본, 스팸, 광고")
    if st.button("멀티 채널 수집"):
        with st.spinner("대량 데이터 수집 및 광고 필터링 중..."):
            all_raw = []
            queries = [f"{kw} 후기", f"{kw} 단점", f"{kw} 실망", f"{kw} 추천"]
            for q in queries:
                res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{q} -{ex}", "num": 20, "gl": "kr", "hl": "ko"}).json()
                all_raw.extend([{'title': r.get('title'), 'body': r.get('snippet'), 'source': r.get('link')} for r in res.get('organic', [])])
            st.session_state['consumer_data'] = all_raw
            st.session_state['consumer_analysis'] = analyze_dialectics(str(all_raw), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.subheader("🔍 수집 원본 매핑 (Source Mapping)")
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 변증법적 전략 도출 (Synthesis)":
    st.title("🧠 STEP 3. 정반합 기반 최종 전략")
    if st.button("🚀 변증법적 통합 리포트 생성"):
        with st.spinner("인사이트 합성 중..."):
            data = f"자사(정):{st.session_state['brand_analysis']}\n경쟁사/소비자(반):{st.session_state['comp_analysis']}\n{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_dialectics(data, "synthesis", st.session_state['brand_insight'])
            _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        exp = [("BRAND(Thesis)", st.session_state['brand_analysis']), ("COMPETITOR", st.session_state['comp_analysis']),
               ("CONSUMER(Antithesis)", st.session_state['consumer_analysis']), ("STRATEGY(Synthesis)", st.session_state['final_report'])]
        st.download_button("📥 통합 리포트 PDF 다운로드 (One-Click)", data=generate_master_pdf(exp), file_name="Total_Strategy_Master.pdf", mime="application/pdf")
