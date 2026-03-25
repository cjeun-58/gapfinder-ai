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

# --- 1. 초기 설정 및 세션 관리 ---
_ = st.set_page_config(page_title="GapFinder AI v17.0", layout="wide")

states = ['brand_analysis', 'brand_insight', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = [] if 'data' in key else ""

# --- 2. 사이드바 메뉴 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    _ = st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 (Thesis)", 
        "STEP 1.5. 경쟁사 Deep-Dive", 
        "STEP 2. 소비자 데이터 (Evidence)", 
        "STEP 3. 하이브리드 전략 리포트"
    ])

# --- 3. 핵심 분석 엔진 (Gap 분석 및 v6.5 결론 강화) ---

def analyze_hybrid_v17(content, target_type, insight="", brand_context="", consumer_raw=""):
    try:
        client = genai.Client(api_key=gemini_key)
        p_base = "인사말 생략. 광고 대행사 총괄 기획자로서 분석하세요. 표 기호(|)는 사용하지 말고 불렛 포인트 리스트로만 작성하세요.\n\n"
        
        prompts = {
            "brand": f"{p_base}[Thesis] 자사 브랜드 분석. 운영 인사이트({insight})를 반영하여 현재 소구점을 정의하세요.",
            "comp": f"{p_base}[Competitor] 경쟁사 분석. 자사({brand_context[:200]}) 대비 경쟁사의 한계와 화이트스페이스를 도출하세요.",
            "consumer": f"{p_base}[Evidence] 소비자 Raw Voice 분석. 각 페인포인트에 [데이터 #번] 태그를 붙이세요.",
            "final": f"{p_base}[Strategic Gap Report]\n1. GAP FINDER (언어 대조): 브랜드가 말하는 '가치'와 소비자가 원하는 '실속'을 구체적인 워딩으로 1:1 대조 분석하세요.\n2. 타겟별 DA 카피: 각 카피마다 [근거: 소비자 언어 '...']를 명시하세요.\n3. Victory Strategy v6.5: '거부감을 자부심으로 전환'하는 식의 선언적 필승 전략을 한 문장으로 정의하세요.\n인사이트: {insight}\n소비자 데이터: {consumer_raw[:6000]}"
        }
        res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompts[target_type] + "\n\n데이터:\n" + content[:12000])
        return res.text
    except Exception as e: return f"분석 오류: {e}"

# --- 4. 무결점 PDF 엔진 (잘림 방지 최적화) ---

class PiecePDF(FPDF):
    def __init__(self):
        super().__init__()
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg):
            self.add_font('NG', '', f_reg); self.add_font('NG', 'B', f_bold); self.fn = 'NG'
        else: self.fn = 'Arial'
        _ = self.set_auto_page_break(auto=True, margin=20)
        _ = self.set_margins(20, 20, 20)

    def header(self):
        if self.page_no() == 1:
            self.set_font(self.fn, 'B', 18); self.set_text_color(0, 51, 102)
            self.cell(170, 15, txt="Strategic Hybrid Strategy Report", ln=True, align='C'); self.ln(5)

    def write_safe(self, text):
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: self.ln(5); continue
            self.set_font(self.fn, '', 10); self.set_text_color(50, 50, 50)
            if line.startswith('##') or line.startswith('1.') or 'Strategy' in line: 
                self.set_font(self.fn, 'B', 12)
                line = line.replace('##', '').strip()
            # 특수 기호 정제 및 170mm 폭 강제 지정 (잘림 방지 핵심)
            clean = re.sub(r'[^\u0000-\u007f\uac00-\ud7af]', '', line.replace('|', ' '))
            self.multi_cell(170, 7, txt=clean)

# --- 5. 단계별 실행 로직 ---

if menu == "STEP 1. 자사 분석 (Thesis)":
    st.title("🏢 STEP 1. 자사 정체성 및 인사이트")
    b_u = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 운영 인사이트", value=st.session_state['brand_insight'], height=100)
    if st.button("분석 실행"):
        st.session_state['brand_analysis'] = analyze_hybrid_v17(b_u, "brand", st.session_state['brand_insight'])
        _ = st.rerun()
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 Deep-Dive":
    st.title("⚔️ STEP 1.5. 경쟁사 정밀 분석")
    col1, col2 = st.columns([1, 2])
    with col1: c1n = st.text_input("경쟁사 1")
    with col2: c1u = st.text_input("경쟁사 1 URL")
    if st.button("경쟁사 분석"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": f"{c1n} 특징 마케팅", "gl": "kr", "hl": "ko"}).json()
        all_c = f"[{c1n}]\n" + "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
        st.session_state['comp_analysis'] = analyze_hybrid_v17(all_c, "comp", brand_context=st.session_state['brand_analysis'])
        _ = st.rerun()
    if st.session_state['comp_analysis']: st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 데이터 (Evidence)":
    st.title("👥 STEP 2. 소비자 보이스 수집")
    kw = st.text_input("키워드")
    if st.button("데이터 수집"):
        res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": kw + " 후기 단점", "num": 15, "gl": "kr", "hl": "ko"}).json()
        all_r = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
        st.session_state['consumer_data'] = all_r
        st.session_state['consumer_analysis'] = analyze_hybrid_v17(str(all_r), "consumer")
        _ = st.rerun()
    if st.session_state['consumer_analysis']: 
        st.markdown(st.session_state['consumer_analysis'])
        _ = st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 하이브리드 전략 리포트":
    st.title("🧠 STEP 3. GAP FINDER & Victory Strategy")
    if st.button("🚀 통합 전략 리포트 도출"):
        comb = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
        st.session_state['final_report'] = analyze_hybrid_v17(comb, "final", st.session_state['brand_insight'], consumer_raw=str(st.session_state['consumer_data']))
        _ = st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 리포트 다운로드 (안전 시스템)")
        exp = [("BRAND", st.session_state['brand_analysis']), ("COMPETITOR", st.session_state['comp_analysis']), 
               ("CONSUMER", st.session_state['consumer_analysis']), ("STRATEGY", st.session_state['final_report'])]
        
        c_pd, c_tx = st.columns(2)
        with c_pd:
            try:
                pdf = PiecePDF(); _ = pdf.add_page()
                for t, b in exp:
                    _ = pdf.set_fill_color(240, 240, 240); _ = pdf.set_font(pdf.fn, 'B', 12)
                    _ = pdf.cell(170, 10, txt=f" {t}", ln=True, fill=True); _ = pdf.ln(3)
                    _ = pdf.write_safe(b); _ = pdf.ln(8)
                st.download_button("📥 PDF 다운로드 (잘림 방지)", data=bytes(pdf.output()), file_name="Strategy_Master.pdf", mime="application/pdf")
            except: st.error("PDF 생성 중 일시적 오류가 발생했습니다. 텍스트 파일을 이용해주세요.")
        with c_tx:
            full_txt = ""
            for t, b in exp: full_txt += f"[{t}]\n{b}\n\n"
            st.download_button("📥 텍스트 파일 다운로드 (.txt)", data=full_txt, file_name="Strategy_Master.txt", mime="text/plain")
