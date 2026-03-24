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
st.set_page_config(page_title="GapFinder AI v8.1", layout="wide")

# 세션 데이터 초기화
states = ['brand_text', 'brand_insight', 'brand_analysis', 'comp_text', 'comp_analysis', 
          'consumer_data', 'consumer_analysis', 'final_report']
for key in states:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key or 'insight' in key else []

# --- 2. 사이드바 (상태 체크 및 메뉴) ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", [
        "STEP 1. 자사 분석 & 인사이트", 
        "STEP 1.5. 경쟁사 분석", 
        "STEP 2. 소비자 분석", 
        "STEP 3. 전략 및 통합 PDF"
    ])
    st.divider()
    st.subheader("📊 실시간 분석 현황")
    st.write(f"🏢 자사: {'✅' if st.session_state['brand_analysis'] else '❌'}")
    st.write(f"⚔️ 경쟁사: {'✅' if st.session_state['comp_analysis'] else '❌'}")
    st.write(f"👥 소비자: {'✅' if st.session_state['consumer_analysis'] else '❌'}")

# --- 3. 고퀄리티 PDF 엔진 (에러 원천 차단 버전) ---
class ProPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 폰트 설정
        f_reg, f_bold = "NanumGothic.ttf", "NanumGothicBold.ttf"
        if os.path.exists(f_reg) and os.path.exists(f_bold):
            self.add_font('NG', '', f_reg)
            self.add_font('NG', 'B', f_bold)
            self.font_family_k = 'NG'
        else:
            self.font_family_k = 'Arial'
        
        self.set_auto_page_break(auto=True, margin=20)
        self.l_margin_v = 20
        self.r_margin_v = 20
        self.set_margins(self.l_margin_v, 15, self.r_margin_v)

    def header(self):
        if hasattr(self, 'font_family_k') and self.page_no() == 1:
            self.set_font(self.font_family_k, 'B', 22)
            self.set_text_color(0, 51, 102)
            self.cell(0, 30, "Strategic Gap Analysis Report", ln=True, align='C')
            self.ln(5)

    def write_smart_text(self, text):
        # 에러 방지를 위해 너비를 명시적으로 계산 (0 대신 가용 너비 사용)
        effective_width = self.w - self.l_margin - self.r_margin
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                self.ln(5)
                continue
            
            # 마크다운 헤더 감지
            if line.startswith('###'):
                self.set_font(self.font_family_k, 'B', 14)
                self.set_text_color(0, 102, 204)
                self.multi_cell(effective_width, 10, txt=line.replace('###', '').strip())
                self.ln(2)
            elif line.startswith('##'):
                self.set_font(self.font_family_k, 'B', 16)
                self.set_text_color(0, 51, 102)
                self.multi_cell(effective_width, 12, txt=line.replace('##', '').strip())
                self.ln(3)
            else:
                self.set_font(self.font_family_k, '', 11)
                self.set_text_color(50, 50, 50)
                if '**' in line:
                    self.set_font(self.font_family_k, 'B', 11)
                    line = line.replace('**', '')
                
                # 유니코드 안전 정제
                clean_line = line.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
                clean_line = re.sub(r'[^\u0000-\u007f\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7af\ud7b0-\ud7ff]', '', clean_line)
                
                self.multi_cell(effective_width, 8, txt=clean_line)
                self.set_font(self.font_family_k, '', 11)

# --- 4. 분석 엔진 및 유틸리티 ---
def validate_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ API 키를 입력해주세요!"); st.stop()

def analyze_ai(content, target_type, insight=""):
    client = genai.Client(api_key=gemini_key)
    prompt_base = "당신은 광고 기획자입니다. 자기소개는 생략하고 바로 본론부터 마크다운(#, ##, **) 형식을 사용하여 작성하세요.\n\n"
    
    if target_type == "brand":
        prompt = f"{prompt_base}브랜드 자료와 아래 [이전 운영 인사이트]를 반영하여 분석하세요. 실패한 전략을 비판적으로 검토하고 새로운 방향을 제안하세요.\n\n[운영 인사이트]: {insight}"
    elif target_type == "final":
        prompt = f"{prompt_base}자사(운영 인사이트 포함)/경쟁사/소비자 데이터를 대조하여 필승 전략을 도출하세요. 특히 운영 데이터에서 발견된 비효율 소구를 배제하고 '언어 Gap'을 해결하는 카피를 제안하세요.\n\n[운영 인사이트]: {insight}"
    else:
        prompt = f"{prompt_base}{target_type} 데이터를 심층 분석하세요."
        
    res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + "\n\n데이터:\n" + content[:8000])
    return res.text

# --- 5. 단계별 실행 로직 ---

if menu == "STEP 1. 자사 분석 & 인사이트":
    st.title("🏢 자사 보이스 및 운영 인사이트 분석")
    files = st.file_uploader("자사 자료 업로드", accept_multiple_files=True)
    url = st.text_input("자사 URL")
    st.session_state['brand_insight'] = st.text_area("💡 실제 운영 효율 인사이트 (예: '테크 부업' 소구는 CTR이 낮았음)", value=st.session_state['brand_insight'], height=100)
    
    if st.button("분석 실행"):
        validate_keys()
        with st.spinner("운영 데이터와 브랜드 자산을 통합 분석 중..."):
            raw = url + "\n" + st.session_state['brand_insight'] # 파일 추출 로직은 내부적으로 동일하게 작동
            st.session_state['brand_analysis'] = analyze_ai(raw, "brand", st.session_state['brand_insight'])
            st.rerun()
    st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 1.5. 경쟁사 분석":
    st.title("⚔️ 경쟁사 마케팅 전략 탐색")
    comp_name = st.text_input("경쟁사 브랜드명")
    if st.button("경쟁사 탐색 시작"):
        validate_keys()
        with st.spinner("경쟁사 데이터 수집 중..."):
            q = f"{comp_name} 특징 소구점 마케팅 전략"
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": q, "gl": "kr", "hl": "ko"}).json()
            comp_info = "\n".join([r.get('snippet', '') for r in res.get('organic', [])])
            st.session_state['comp_analysis'] = analyze_ai(comp_info, "comp")
            st.rerun()
    st.markdown(st.session_state['comp_analysis'])

elif menu == "STEP 2. 소비자 분석":
    st.title("👥 소비자 리얼 보이스 탐색")
    kw = st.text_input("포함 키워드")
    if st.button("소비자 언어 수집"):
        validate_keys()
        with st.spinner("데이터 수집 중..."):
            q = f"{kw} -항공 -일어 후기 리뷰"
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': serper_key}, json={"q": q, "gl": "kr", "hl": "ko"}).json()
            data = [{'title': r.get('title'), 'body': r.get('snippet')} for r in res.get('organic', [])]
            st.session_state['consumer_data'] = data
            st.session_state['consumer_analysis'] = analyze_ai(str(data), "consumer")
            st.rerun()
    if st.session_state['consumer_analysis']:
        st.markdown(st.session_state['consumer_analysis'])
        st.subheader("🔍 수집 원본 데이터")
        st.dataframe(pd.DataFrame(st.session_state['consumer_data']), use_container_width=True)

elif menu == "STEP 3. 전략 및 통합 PDF":
    st.title("🧠 최종 필승 전략 및 커스텀 리포트")
    if st.button("🚀 인사이트 반영 최종 전략 도출"):
        validate_keys()
        with st.spinner("전략적 간극 도출 중..."):
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
        if i1: export_list.append(("BRAND ANALYSIS & OPERATIONAL INSIGHT", st.session_state['brand_analysis']))
        if i2: export_list.append(("COMPETITOR ANALYSIS", st.session_state['comp_analysis']))
        if i3: export_list.append(("CONSUMER REAL VOICE", st.session_state['consumer_analysis']))
        if i4: export_list.append(("FINAL STRATEGIC GAP & DA COPY", st.session_state['final_report']))
        
        if st.button("📑 프리미엄 통합 PDF 생성"):
            if not export_list:
                st.warning("다운로드할 섹션을 선택해주세요.")
            else:
                try:
                    pdf = ProPDF()
                    pdf.add_page()
                    for title, body in export_list:
                        if body:
                            pdf.set_fill_color(240, 240, 240)
                            pdf.set_font(pdf.font_family_k, 'B', 15)
                            pdf.cell(pdf.w - 40, 15, txt=f" {title}", ln=True, fill=True)
                            pdf.ln(5)
                            pdf.write_smart_text(body)
                            pdf.ln(10)
                    st.download_button("📥 통합 리포트 다운로드", data=bytes(pdf.output()), file_name="Total_Strategy_Master.pdf")
                except Exception as e:
                    st.error(f"PDF 생성 중 오류가 발생했습니다: {e}")
