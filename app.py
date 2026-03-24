import streamlit as st
from google import genai
import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io
import time
import os
import re

# --- 1. 기본 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v7.0", layout="wide")

for key in ['brand_text', 'brand_analysis', 'comp_analysis', 'consumer_data', 'consumer_analysis', 'final_report']:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key else []

# --- 2. 사이드바 (상태 체크) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 자사 분석", "STEP 1.5. 경쟁사 분석", "STEP 2. 소비자 분석", "STEP 3. 전략 및 PDF 추출"])
    st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 고퀄리티 PDF 엔진 (마크다운 파서 탑재) ---
class ProPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()
        # 폰트 등록
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg)
            self.add_font('NG', 'B', f_bold)
            self.font_family_k = 'NG'
        else:
            self.font_family_k = 'Arial'

    def header(self):
        if self.page_no() == 1:
            self.set_font(self.font_family_k, 'B', 22)
            self.set_text_color(0, 51, 102)
            self.cell(0, 30, "Strategic Gap Analysis Report", ln=True, align='C')
            self.ln(5)

    def write_smart_text(self, text):
        """마크다운 기호를 해석하여 폰트 스타일을 적용합니다."""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(5)
                continue
            
            # 제목 처리
            if line.startswith('###'):
                self.set_font(self.font_family_k, 'B', 14)
                self.set_text_color(0, 102, 204)
                self.multi_cell(0, 10, txt=line.replace('###', '').strip())
                self.ln(2)
            elif line.startswith('##'):
                self.set_font(self.font_family_k, 'B', 16)
                self.set_text_color(0, 51, 102)
                self.multi_cell(0, 12, txt=line.replace('##', '').strip())
                self.ln(3)
            elif line.startswith('#'):
                self.set_font(self.font_family_k, 'B', 18)
                self.set_text_color(0, 0, 0)
                self.multi_cell(0, 15, txt=line.replace('#', '').strip())
                self.ln(4)
            else:
                # 일반 텍스트 및 볼드 처리 (**텍스트**)
                self.set_font(self.font_family_k, '', 11)
                self.set_text_color(50, 50, 50)
                
                # 볼드 부분만 따로 그리기엔 복잡하므로, 줄 단위 볼드 감지
                if '**' in line:
                    self.set_font(self.font_family_k, 'B', 11)
                    line = line.replace('**', '')
                
                # 유니코드 에러 방지용 치환 (이모지 제거 등)
                clean_line = line.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
                # 이모지 등 지원하지 않는 유니코드 제거
                clean_line = re.sub(r'[^\u0000-\u007f\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff]', '', clean_line)
                
                self.multi_cell(0, 8, txt=clean_line)
                self.set_font(self.font_family_k, '', 11) # 원복

# --- 4. 핵심 로직 ---

def analyze_ai(content, target_type):
    client = genai.Client(api_key=gemini_key)
    # [수정] 자아 비대해진 AI 억제 프롬프트
    prompt_base = "당신은 광고 기획자입니다. 인사말이나 '15년차' 같은 자기소개는 절대 하지 마세요. '님'이나 '습니다' 같은 공손한 어투는 유지하되 바로 본론(분석)부터 작성하세요.\n\n"
    
    if target_type == "final":
        prompt = prompt_base + "자사/경쟁사/소비자 데이터를 비교하여 브랜드와 소비자 사이의 '언어 Gap'을 정밀 분석하고 광고 카피를 제안하세요."
    else:
        prompt = prompt_base + f"{target_type} 데이터를 분석하여 기획서용 리포트를 작성하세요."
    
    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + "\n\n데이터:\n" + content[:8000])
    return res.text

# --- 5. 화면 레이아웃 ---

if menu == "STEP 1. 자사 분석":
    st.title("🏢 자사 브랜드 분석")
    files = st.file_uploader("자사 자료", accept_multiple_files=True)
    url = st.text_input("자사 URL")
    if st.button("분석 실행"):
        with st.spinner("분석 중..."):
            raw = ""
            if files: # (파일 추출 로직 생략 - 이전과 동일)
                pass 
            st.session_state['brand_analysis'] = analyze_ai(raw + url, "brand")
            st.rerun()
    st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ 경쟁사 전략 분석")
    comp_name = st.text_input("경쟁사 명칭 (예: 담터 콤부차)")
    c_url = st.text_input("경쟁사 URL")
    if st.button("경쟁사 분석 실행"):
        with st.spinner("경쟁사 탐색 중..."):
            # Serper로 경쟁사 USP 검색 후 AI 분석
            q = f"{comp_name} 특징 소구점 마케팅"
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": q, "gl": "kr", "hl": "ko"}).json()
            comp_info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_ai(comp_info + c_url, "comp")
            st.rerun()
    st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 소비자 리얼 보이스 탐색")
    kw = st.text_input("포함 키워드")
    ex = st.text_input("제외 키워드", value="항공, 일본")
    if st.button("수집 및 분석"):
        with st.spinner("데이터 수집 중..."):
            # (Serper 수집 로직 - 이전과 동일)
            # st.session_state['consumer_data'] = 수집결과
            # st.session_state['consumer_analysis'] = analyze_ai(결과, "consumer")
            st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.subheader("🔍 수집 원본 데이터 (Raw Data)")
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 및 PDF 추출":
    st.title("🧠 최종 전략 & 고퀄리티 PDF")
    if st.button("🚀 최종 필승 전략 도출"):
        with st.spinner("전략적 간극 분석 중..."):
            data = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_ai(data, "final")
            st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 리포트 다운로드 (High Quality)")
        # 체크박스 선택 로직
        export_list = [("FINAL STRATEGY", st.session_state['final_report'])]
        
        if st.button("📑 프리미엄 PDF 생성"):
            pdf = ProPDF()
            for title, body in export_list:
                pdf.set_font('NG', 'B', 16) if 'NG' in pdf.fonts else pdf.set_font("Arial", 'B', 14)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 15, txt=f" {title}", ln=True, fill=True)
                pdf.ln(5)
                pdf.write_smart_text(body)
                pdf.ln(10)
            
            st.download_button("📥 완성된 PDF 다운로드", data=bytes(pdf.output()), file_name="Total_Strategy_Master.pdf")
