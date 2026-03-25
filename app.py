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

# --- 1. 기본 설정 ---
_ = st.set_page_config(page_title="GapFinder AI v12.2", layout="wide")

states = ['brand_analysis', 'brand_insight', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = [] if 'data' in key else ""

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    _ = st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 자사 분석 (Thesis)", "STEP 1.5. 경쟁사 Deep-Dive", "STEP 2. 소비자 데이터 (Antithesis)", "STEP 3. 변증법적 전략 도출 (Synthesis)"])

# --- 3. 유틸리티 (텍스트 추출 및 분석) ---

def extract_text_from_files(files):
    """PDF, PPTX, XLSX 파일에서 텍스트를 추출합니다."""
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"):
                    text += "\n".join([p.extract_text() for p in PdfReader(f).pages if p.extract_text()])
                elif f.name.endswith(".pptx"):
                    prs = Presentation(f)
                    text += "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
                elif f.name.endswith(".xlsx"):
                    text += pd.read_excel(f).to_string()
            except Exception as e:
                text += f"\n[파일 읽기 실패: {f.name}]"
    return text

def analyze_dialectics(content, target_type, insight=""):
    try:
        client = genai.Client(api_key=gemini_key)
        base_guide = "자기소개 금지. 광고 대행사의 '정반합' 관점으로 분석하세요. 스팸성 데이터는 무시하세요."
        prompts = {
            "brand": f"{base_guide}\n[Thesis] 자사 페르소나와 운영 인사이트 분석. 인사이트: {insight}",
            "comp": f"{base_guide}\n[Comparison] 경쟁사들의 소구점을 매트릭스로 비교 분석하세요. 업로드된 파일이 있다면 그 내용을 최우선 반영하세요.",
            "consumer": f"{base_guide}\n[Antithesis] 소비자 페인포인트 분석.",
            "synthesis": f"{base_guide}\n[Synthesis] 정반합 필승 전략 도출. 인사이트: {insight}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:10000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 단계별 로직 ---

if menu == "STEP 1. 자사 분석 (Thesis)":
    st.title("🏢 자사 분석 및 운영 인사이트")
    u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 피드백", value=st.session_state['brand_insight'])
    if st.button("자사 분석 실행"):
        with st.spinner("분석 중..."):
            st.session_state['brand_analysis'] = analyze_dialectics(u + "\n" + st.session_state['brand_insight'], "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 Deep-Dive":
    st.title("⚔️ STEP 1.5. 경쟁사 다중 비교 분석")
    st.markdown("경쟁사 명칭을 검색하거나, 내부 분석 자료(PDF 등)를 업로드하여 깊이를 더하세요.")
    
    # [복구 및 추가] 경쟁사 파일 업로더
    c_names = st.text_input("경쟁사 명칭 (쉼표 구분)", placeholder="브랜드A, 브랜드B")
    c_files = st.file_uploader("경쟁사 관련 자료 업로드 (PDF, PPTX, XLSX)", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    
    if st.button("경쟁사 정밀 분석 시작"):
        if not gemini_key or not serper_key: st.error("API 키를 확인하세요."); st.stop()
        with st.spinner("경쟁사 데이터를 수집 및 분석 중..."):
            all_comp_data = ""
            # 1. 파일에서 데이터 추출
            if c_files:
                all_comp_data += "[업로드된 내부 분석 자료]\n" + extract_text_from_files(c_files) + "\n\n"
            
            # 2. 검색 엔진 데이터 추출
            if c_names:
                for name in [n.strip() for n in c_names.split(",")]:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, 
                                        json={"q": f"{name} 특징 마케팅 소구점", "gl": "kr", "hl": "ko"}).json()
                    all_comp_data += f"[{name} 웹 검색 정보]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])]) + "\n\n"
            
            if all_comp_data:
                st.session_state['comp_analysis'] = analyze_dialectics(all_comp_data, "comp")
                _ = st.rerun()
            else: st.warning("경쟁사 명칭을 입력하거나 파일을 업로드해주세요.")
            
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

# [STEP 2 & 3 로직은 이전과 동일하되 None 방어 유지]
elif menu == "STEP 2. 소비자 데이터 (Antithesis)":
    st.title("👥 소비자 리얼 데이터 분석")
    kw = st.text_input("키워드")
    if st.button("데이터 수집"):
        with st.spinner("수집 중..."):
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": kw + " 단점 후기", "num": 20, "gl": "kr", "hl": "ko"}).json()
            all_raw = [{'title': r.get('title'), 'body': r.get('snippet'), 'link': r.get('link')} for r in res.get('organic', [])]
            st.session_state['consumer_data'] = all_raw
            st.session_state['consumer_analysis'] = analyze_dialectics(str(all_raw), "consumer")
            _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 변증법적 전략 도출 (Synthesis)":
    st.title("🧠 정반합 기반 최종 전략")
    if st.button("🚀 필승 전략 도출"):
        with st.spinner("인사이트 합성 중..."):
            data = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_dialectics(data, "synthesis", st.session_state['brand_insight'])
            _ = st.rerun()
    if st.session_state['final_report']: st.markdown(st.session_state['final_report'])
