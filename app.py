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

# --- 1. 기본 설정 및 데이터 초기화 ---
st.set_page_config(page_title="GapFinder AI v5.8", layout="wide")

for key in ['brand_text', 'brand_analysis', 'consumer_data', 'consumer_analysis', 'final_report']:
    if key not in st.session_state:
        st.session_state[key] = "" if 'analysis' in key or 'report' in key or 'text' in key else []

# --- 2. 사이드바 ---
with st.sidebar:
    st.header("🔑 API 설정")
    gemini_key = st.text_input("1. Gemini API Key", type="password")
    serper_key = st.text_input("2. Serper API Key", type="password")
    st.divider()
    menu = st.radio("전략 수립 단계", ["STEP 1. 브랜드 보이스 분석", "STEP 2. 소비자 리얼 보이스 탐색", "STEP 3. 전략적 Gap 도출"])
    
    st.subheader("📊 수집 현황")
    b_status = "✅" if st.session_state['brand_analysis'] else "❌"
    c_status = "✅" if st.session_state['consumer_analysis'] else "❌"
    st.write(f"브랜드 분석: {b_status}")
    st.write(f"소비자 분석: {c_status}")

# --- 3. 핵심 유틸리티 함수 ---

def validate_keys():
    if not gemini_key or not serper_key:
        st.error("⚠️ 사이드바에 API 키를 모두 입력해주세요!"); st.stop()

def extract_text(files, url):
    text = ""
    if files:
        for f in files:
            try:
                if f.name.endswith(".pdf"):
                    text += "\n".join([p.extract_text() for p in PdfReader(f).pages])
                elif f.name.endswith(".pptx"):
                    prs = Presentation(f)
                    text += "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
                elif f.name.endswith(".xlsx"):
                    text += pd.read_excel(f).to_string()
            except: text += f"\n[{f.name} 실패]"
    if url:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(['script', 'style']): s.decompose()
            text += f"\n\n[URL]\n{soup.get_text()[:4000]}"
        except: text += "\nhttps://donotfear.tistory.com/93"
    return text

def analyze_ai(content, target_type):
    try:
        client = genai.Client(api_key=gemini_key)
        prompt = f"당신은 15년차 브랜드 전략가입니다. 다음 {'브랜드 자료' if target_type=='brand' else '소비자 데이터'}를 심층 분석하여 전략 보고서 형태로 작성하세요.\n\n"
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt + content[:8000])
        return response.text
    except Exception as e: return f"분석 실패: {str(e)}"

def generate_pdf(content_list):
    """가독성을 극대화한 멀티 폰트 PDF 생성"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 폰트 파일명 (깃허브 업로드된 명칭과 일치해야 함)
    font_reg = "NanumGothic.ttf"
    font_bold = "NanumGothicBold.ttf"
    
    # 폰트 등록
    try:
        pdf.add_font('NanumGothic', '', font_reg)
        pdf.add_font('NanumGothic', 'B', font_bold)
        pdf.set_font('NanumGothic', size=11)
        use_custom_font = True
    except:
        pdf.set_font("Arial", size=10)
        use_custom_font = False

    # 리포트 전체 타이틀
    pdf.set_font('NanumGothic', 'B', 20) if use_custom_font else pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, txt="Brand Gap Analysis Strategy Report", ln=True, align='C')
    pdf.ln(10)

    for title, body in content_list:
        if body:
            # 섹션 헤더 디자인
            pdf.set_fill_color(240, 240, 240) # 연한 회색 배경
            pdf.set_text_color(0, 51, 102)
            pdf.set_font('NanumGothic', 'B', 14) if use_custom_font else pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 12, txt=f"  {title}", ln=True, fill=True)
            pdf.ln(5)
            
            # 본문 디자인
            pdf.set_text_color(40, 40, 40)
            pdf.set_font('NanumGothic', '', 10.5) if use_custom_font else pdf.set_font("Arial", size=10)
            
            # 특수기호 및 인코딩 처리
            safe_body = body.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2502', '|')
            pdf.multi_cell(0, 7, txt=safe_body)
            pdf.ln(12) # 섹션 간 충분한 여백
            
            # 섹션 구분선
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
    return bytes(pdf.output())

# --- 4. 메인 로직 ---

if menu == "STEP 1. 브랜드 보이스 분석":
    st.title("🏢 STEP 1. 브랜드 보이스 심층 분석")
    files = st.file_uploader("브랜드 관련 파일", type=["pdf", "pptx", "xlsx"], accept_multiple_files=True)
    url = st.text_input("브랜드 공식 웹사이트/상세페이지 URL")
    if st.button("브랜드 데이터 분석 시작"):
        if not gemini_key: st.error("Gemini Key를 입력하세요."); st.stop()
        with st.spinner("브랜드 자산을 심층 분석 중..."):
            raw = extract_text(files, url)
            st.session_state['brand_text'] = raw
            st.session_state['brand_analysis'] = analyze_ai(raw, "brand")
            st.success("완료!")
    if st.session_state['brand_analysis']: st.markdown(st.session_state['brand_analysis'])

elif menu == "STEP 2. 소비자 리얼 보이스 탐색":
    st.title("👥 STEP 2. 소비자 언어 및 트렌드 탐색")
    keywords = st.text_input("분석 키워드 (쉼표 구분)")
    if st.button("소비자 데이터 수집 및 분석"):
        validate_keys()
        with st.spinner("수집 및 분석 중..."):
            all_res = []
            kw_list = [k.strip() for k in keywords.split(",")]
            for kw in kw_list:
                try:
                    res = requests.post("https://google.serper.dev/search", 
                                        headers={'X-API-KEY': serper_key, 'Content-Type': 'application/json'}, 
                                        json={"q": f"{kw} (site:naver.com OR site:youtube.com OR site:instagram.com) 후기", "gl": "kr", "hl": "ko"}).json()
                    if 'organic' in res:
                        for r in res['organic']: all_res.append({'title': r.get('title', ''), 'body': r.get('snippet', '')})
                except: pass
                time.sleep(0.5)
            st.session_state['consumer_data'] = all_res
            c_combined = "\n".join([f"{d['title']}: {d['body']}" for d in all_res])
            st.session_state['consumer_analysis'] = analyze_ai(c_combined, "consumer")
            st.success("완료!")
    if st.session_state['consumer_analysis']: st.markdown(st.session_state['consumer_analysis'])

elif menu == "STEP 3. 전략적 Gap 도출":
    st.title("🧠 STEP 3. 최종 전략 및 리포트 다운로드")
    
    if not st.session_state['brand_analysis'] or not st.session_state['consumer_analysis']:
        st.error("STEP 1, 2 분석을 먼저 완료해주세요.")
    else:
        if st.button("🚀 최종 Gap 전략 리포트 생성"):
            validate_keys()
            with st.spinner("전략 리포트 작성 중..."):
                client = genai.Client(api_key=gemini_key)
                prompt = f"광고 전략가로서 아래 두 데이터를 대조하여 전략 보고서를 작성하세요.\n\n[브랜드 분석]\n{st.session_state['brand_analysis']}\n\n[소비자 분석]\n{st.session_state['consumer_analysis']}"
                st.session_state['final_report'] = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt).text

        if st.session_state['final_report']:
            st.markdown("---")
            st.subheader("📊 최종 전략 리포트")
            st.markdown(st.session_state['final_report'])
            
            st.divider()
            st.subheader("📥 리포트 다운로드 설정")
            
            c1, c2, c3 = st.columns(3)
            with c1: include_step1 = st.checkbox("STEP 1. 브랜드 분석 포함", value=True)
            with c2: include_step2 = st.checkbox("STEP 2. 소비자 분석 포함", value=True)
            with c3: include_step3 = st.checkbox("STEP 3. 최종 전략 포함", value=True)
            
            export_list = []
            if include_step1: export_list.append(("STEP 1. BRAND VOICE ANALYSIS", st.session_state['brand_analysis']))
            if include_step2: export_list.append(("STEP 2. CONSUMER REAL VOICE", st.session_state['consumer_analysis']))
            if include_step3: export_list.append(("STEP 3. STRATEGIC GAP & COPY", st.session_state['final_report']))
            
            if export_list:
                try:
                    pdf_output = generate_pdf(export_list)
                    st.download_button(
                        label="📥 선택한 섹션 PDF 통합 다운로드 (High Quality)",
                        data=pdf_output,
                        file_name="Brand_Gap_Strategy_Report.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"PDF 생성 오류: {e}")
            
            txt_content = ""
            for t, b in export_list: txt_content += f"--- {t} ---\n{b}\n\n"
            st.download_button(label="📄 텍스트(TXT) 파일 다운로드", data=txt_content, file_name="Strategy_Analysis.txt", mime="text/plain")
