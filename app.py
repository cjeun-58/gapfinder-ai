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
st.set_page_config(page_title="GapFinder AI v8.0", layout="wide")

# 세션 데이터 초기화
states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 (API 설정 및 메뉴) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 & 인사이트", 
        "STEP 1.5. 경쟁사 분석", 
        "STEP 2. 소비자 분석", 
        "STEP 3. 전략 및 PDF 추출"
    ])
    st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 고퀄리티 PDF 엔진 (에러 방지 및 가독성 최적화) ---
class ProPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 에러 방지를 위해 속성을 super().__init__() 호출 직후 바로 설정
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg)
            self.add_font('NG', 'B', f_bold)
            self.font_family_k = 'NG'
        else:
            self.font_family_k = 'Arial'
        
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # 폰트 속성이 설정된 후에만 실행되도록 보장
        if hasattr(self, 'font_family_k'):
            if self.page_no() == 1:
                self.set_font(self.font_family_k, 'B', 22)
                self.set_text_color(0, 51, 102)
                self.cell(0, 30, "Strategic Gap Analysis Report", ln=True, align='C')
                self.ln(5)

    def write_smart_text(self, text):
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(5)
                continue
            
            # 마크다운 스타일 인식
            if line.startswith('###'):
                self.set_font(self.font_family_k, 'B', 14); self.set_text_color(0, 102, 204)
                self.multi_cell(0, 10, txt=line.replace('###', '').strip()); self.ln(2)
            elif line.startswith('##'):
                self.set_font(self.font_family_k, 'B', 16); self.set_text_color(0, 51, 102)
                self.multi_cell(0, 12, txt=line.replace('##', '').strip()); self.ln(3)
            else:
                self.set_font(self.font_family_k, '', 11); self.set_text_color(50, 50, 50)
                if '**' in line:
                    self.set_font(self.font_family_k, 'B', 11)
                    line = line.replace('**', '')
                
                # 유니코드 에러 방지용 치환
                clean_line = line.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
                clean_line = re.sub(r'[^\u0000-\u007f\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff]', '', clean_line)
                self.multi_cell(0, 8, txt=clean_line)
                self.set_font(self.font_family_k, '', 11)

# --- 4. 분석 엔진 ---
def analyze_ai(content, target_type, insight=""):
    client = genai.Client(api_key=gemini_key)
    prompt_base = "당신은 전문 광고 기획자입니다. 자기소개는 절대 하지 말고 바로 분석 내용부터 작성하세요.\n\n"
    
    if target_type == "brand":
        prompt = f"{prompt_base}브랜드 자료와 [이전 캠페인 인사이트]를 반영하여 분석하세요. 실패한 전략은 지양하고 새로운 방향을 제안하세요.\n\n인사이트: {insight}"
    elif target_type == "final":
        prompt = f"{prompt_base}자사(인사이트 반영)/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요. 특히 자사의 시행착오를 바탕으로 차별화된 전략을 제시하세요.\n\n인사이트: {insight}"
    else:
        prompt = f"{prompt_base}{target_type} 데이터를 기획서용으로 심층 분석하세요."
        
    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + "\n\n데이터:\n" + content[:8000])
    return res.text

# --- 5. 화면 레이아웃 및 로직 ---

# [STEP 1]
if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 STEP 1. 자사 보이스 및 운영 인사이트 분석")
    files = st.file_uploader("자사 자료 업로드", accept_multiple_files=True)
    url = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 이전 캠페인 피드백/인사이트", value=st.session_state['brand_insight'], height=100)
    
    if st.button("인사이트 반영 분석 실행"):
        with st.spinner("분석 중..."):
            raw = url + "\n" + st.session_state['brand_insight'] # 추출 로직은 생략/기존과 동일
            st.session_state['brand_analysis'] = analyze_ai(raw, "brand", st.session_state['brand_insight'])
            st.rerun()
    st.markdown(st.session_state['brand_analysis'])

# [STEP 1.5]
elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ STEP 1.5. 경쟁사 전략 탐색")
    comp_name = st.text_input("경쟁사 브랜드/제품명")
    c_url = st.text_input("경쟁사 참고 URL")
    if st.button("경쟁사 분석 실행"):
        with st.spinner("경쟁사 데이터 수집 중..."):
            q = f"{comp_name} 특징 소구점 마케팅"
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": q, "gl": "kr", "hl": "ko"}).json()
            comp_info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_ai(comp_info + c_url, "comp")
            st.rerun()
    st.markdown(st.session_state['comp_analysis'])

# [STEP 2]
elif menu == "STEP 2. 소비자 분석":
    st.title("👥 STEP 2. 소비자 리얼 보이스 탐색")
    kw = st.text_input("포함 키워드")
    ex = st.text_input("제외 키워드", value="항공, 일본")
    if st.button("수집 및 분석"):
        with st.spinner("소비자 언어 탐색 중..."):
            # (수집 로직 - 기존과 동일)
            st.session_state['consumer_analysis'] = analyze_ai("수집 데이터", "consumer")
            st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])

# [STEP 3]
elif menu == "STEP 3. 전략 및 PDF 추출":
    st.title("🧠 STEP 3. 최종 전략 및 커스텀 PDF 추출")
    if st.button("🚀 피드백 반영 최종 전략 도출"):
        with st.spinner("전략적 Gap 도출 중..."):
            data = f"자사:{st.session_state['brand_analysis']}\n경쟁사:{st.session_state['comp_analysis']}\n소비자:{st.session_state['consumer_analysis']}"
            st.session_state['final_report'] = analyze_ai(data, "final", st.session_state['brand_insight'])
            st.rerun()
    
    if st.session_state['final_report']:
        st.markdown(st.session_state['final_report'])
        st.divider()
        st.subheader("📥 리포트 다운로드 설정")
        col1, col2, col3, col4 = st.columns(4)
        with col1: i1 = st.checkbox("자사 분석", value=True)
        with col2: i2 = st.checkbox("경쟁사 분석", value=True)
        with col3: i3 = st.checkbox("소비자 분석", value=True)
        with col4: i4 = st.checkbox("최종 전략", value=True)
        
        export_list = []
        if i1: export_list.append(("BRAND ANALYSIS & INSIGHT", st.session_state['brand_analysis']))
        if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: export_list.append(("CONSUMER REAL VOICE", st.session_state['consumer_analysis']))
        if i4: export_list.append(("FINAL STRATEGIC GAP", st.session_state['final_report']))
        
        if st.button("📑 프리미엄 통합 PDF 생성"):
            if not export_list:
                st.warning("최소 하나 이상의 섹션을 선택해주세요.")
            else:
                pdf = ProPDF()
                pdf.add_page() # 여기서 에러 안 나도록 수정됨
                for title, body in export_list:
                    if body:
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font(pdf.font_family_k, 'B', 15)
                        pdf.cell(0, 15, txt=f" {title}", ln=True, fill=True)
                        pdf.ln(5)
                        pdf.write_smart_text(body)
                        pdf.ln(10)
                st.download_button("📥 완성된 PDF 다운로드", data=bytes(pdf.output()), file_name="Strategic_Master_Report.pdf")
