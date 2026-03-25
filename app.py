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

# --- 1. 페이지 설정 및 세션 초기화 ---
_ = st.set_page_config(page_title="GapFinder AI v20.0", layout="wide")

# 사이드바 체크 표시를 위한 상태 관리
states = ['brand_analysis', 'brand_insight', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key else []
if 'brand_insight' not in st.session_state:
    st.session_state['brand_insight'] = ""

# --- 2. 사이드바 (API 설정 및 ✅ 현황) ---
with st.sidebar:
    st.header("🔑 서비스 설정")
    gemini_key = st.text_input("Gemini API Key", type="password")
    serper_key = st.text_input("Serper API Key", type="password")
    _ = st.divider()
    menu = st.radio("전략 단계", [
        "1단계. 브랜드 분석 (Thesis)", 
        "2단계. 경쟁사 분석 (Competitor)", 
        "3단계. 소비자 분석 (Antithesis)", 
        "4단계. 통합 전략 및 PDF (Synthesis)"
    ])
    _ = st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 브랜드 분석: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사 분석: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자 분석: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 유틸리티 함수 (텍스트 추출 및 AI 분석) ---

def extract_content(files=None, url=""):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"): text += "\n".join([p.extract_text() for p in PdfReader(f).pages if p.extract_text()])
                elif f.name.endswith(".pptx"): text += "\n".join([s.text for slide in Presentation(f).slides for s in slide.shapes if hasattr(s, "text")])
                elif f.name.endswith(".xlsx"): text += pd.read_excel(f).to_string()
            except: pass
    if url:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            text += f"\n[URL내용: {url}]\n{soup.get_text()[:3000]}"
        except: pass
    return text

def run_analysis(data, step_type, insight="", brand_ctx="", consumer_raw=""):
    if not gemini_key: return "⚠️ Gemini API Key가 필요합니다."
    try:
        client = genai.Client(api_key=gemini_key)
        base_p = "자기소개 생략. 광고 대행사 총괄 기획자로서 분석하세요. 리스트 형식을 사용하세요.\n\n"
        
        prompts = {
            "brand": f"{base_p}[STEP 1] 자사 브랜드 분석: 현재 브랜드의 강점, 포지션, 주요 활동, 소비자 접근 언어를 분석하세요. 인사이트: {insight}",
            "comp": f"{base_p}[STEP 2] 경쟁사 분석: 오직 입력된 경쟁사만 분석하세요. 임의로 브랜드를 추가하지 마세요. 경쟁사의 포지션, 활동, 소비자 접근 언어를 분석하세요. 자사({brand_ctx[:200]})와의 대조에 집중하세요.",
            "consumer": f"{base_p}[STEP 3] 소비자 데이터 분석: 블로그/카페/유튜브의 리얼 보이스를 기반으로 소비자의 실제 언어와 페인포인트를 도출하세요.",
            "final": f"{base_p}[STEP 4] 통합 전략 도출:\n1. 브랜드 vs 소비자 언어 Gap 분석 (표 형식 대조 필수)\n2. 경쟁사 대비 White Space\n3. 확보 가능한 타겟층 및 전략적 카피 문구\n인사이트: {insight}\n소비자 데이터: {consumer_raw[:5000]}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[step_type] + "\n\n데이터:\n" + data[:12000])
        return res.text
    except Exception as e: return f"분석 중 오류 발생: {e}"

# --- 4. 무결점 PDF 생성 엔진 ---

class MasterPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 폰트 로드 시도
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.fn = 'NG'
        else: self.fn = 'Arial'
        _ = self.set_auto_page_break(auto=True, margin=20)
        _ = self.set_margins(25, 20, 25)

    def write_safe(self, title, content):
        if not content: return
        self.add_page()
        self.set_font(self.fn, 'B', 16); self.set_text_color(0, 51, 102)
        self.cell(160, 15, txt=title, ln=True, align='C'); self.ln(10)
        
        self.set_font(self.fn, '', 10.5); self.set_text_color(50, 50, 50)
        # 너비를 160mm로 엄격히 제한하여 잘림 방지
        clean_text = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', content.replace('|', ' '))
        self.multi_cell(160, 7, txt=clean_text)

# --- 5. UI 단계별 실행 ---

if menu == "1단계. 브랜드 분석 (Thesis)":
    st.title("🏢 1단계. 브랜드(자사) 분석")
    b_f = st.file_uploader("자사 자료 업로드", accept_multiple_files=True)
    b_u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 인사이트", value=st.session_state['brand_insight'], height=100)
    if st.button("브랜드 분석 시작"):
        with st.spinner("분석 중..."):
            st.session_state['brand_analysis'] = run_analysis(extract_content(b_f, b_u), "brand", st.session_state['brand_insight'])
            _ = st.rerun()
    st.markdown(st.session_state['brand_analysis'])

elif menu == "2단계. 경쟁사 분석 (Competitor)":
    st.title("⚔️ 2단계. 경쟁사 분석 (최대 3개)")
    c_f = st.file_uploader("경쟁사 자료 업로드", accept_multiple_files=True)
    col1, col2 = st.columns([1, 2])
    with col1: c1n = st.text_input("경쟁사 1"); c2n = st.text_input("경쟁사 2"); c3n = st.text_input("경쟁사 3")
    with col2: c1u = st.text_input("경쟁사 1 URL"); c2u = st.text_input("경쟁사 2 URL"); c3u = st.text_input("경쟁사 3 URL")
    if st.button("경쟁사 분석 시작"):
        with st.spinner("지정 브랜드 분석 중..."):
            all_c = extract_content(c_f)
            for n, u in [(c1n, c1u), (c2n, c2u), (c3n, c3u)]:
                if n:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{n} 특징 마케팅", "gl": "kr", "hl": "ko"}).json()
                    all_c += f"\n[{n}]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])]) + extract_content(url=u)
            st.session_state['comp_analysis'] = run_analysis(all_c, "comp", brand_ctx=st.session_state['brand_analysis'])
            _ = st.rerun()
    st.markdown(st.session_state['comp_analysis'])

elif menu == "3단계. 소비자 분석 (Antithesis)":
    st.title("👥 3단계. 소비자 리얼 데이터 분석")
    kw = st.text_input("분석 키워드 (쉼표 구분 가능)")
    if st.button("소비자 보이스 수집"):
        with st.spinner("대량 수집 중..."):
            all_r = []
            for k in [x.strip() for x in kw.split(",")]:
                for qs in ["후기", "단점", "실망"]:
                    res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{k} {qs}", "num": 10, "gl": "kr", "hl": "ko"}).json()
                    all_r.extend([{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])])
            st.session_state['consumer_data'] = all_r
            st.session_state['consumer_analysis'] = run_analysis(str(all_r), "consumer")
            _ = st.rerun()
    st.markdown(st.session_state['consumer_analysis'])

elif menu == "4단계. 통합 전략 및 PDF (Synthesis)":
    st.title("🧠 4단계. 통합 분석 및 리포트")
    if st.button("🚀 최종 전략 리포트 생성"):
        with st.spinner("데이터 통합 및 Gap 도출 중..."):
            comb = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = run_analysis(comb, "final", st.session_state['brand_insight'], consumer_raw=str(st.session_state['consumer_data']))
            _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        pdf = MasterPDF()
        _ = pdf.write_safe("BRAND ANALYSIS", st.session_state['brand_analysis'])
        _ = pdf.write_safe("COMPETITOR ANALYSIS", st.session_state['comp_analysis'])
        _ = pdf.write_safe("CONSUMER REAL VOICE", st.session_state['consumer_analysis'])
        _ = pdf.write_safe("STRATEGIC GAP REPORT", st.session_state['final_report'])
        _ = st.download_button("📥 통합 리포트 PDF 다운로드 (v20.0)", data=bytes(pdf.output()), file_name="GapFinder_Report.pdf", mime="application/pdf")
