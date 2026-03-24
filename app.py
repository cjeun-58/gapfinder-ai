# --- [STEP 2. 소비자 트렌드 크롤링] 부분만 아래 내용으로 교체하거나 전체를 업데이트하세요 ---

elif menu == "STEP 2. 소비자 트렌드 크롤링":
    st.title("👥 STEP 2. 한국형 소비자 트렌드 수집")
    st.markdown("네이버 블로그, 카페, 커뮤니티 위주의 한국어 데이터를 우선 수집합니다.")
    
    keywords = st.text_input("분석 키워드 (쉼표 구분)", placeholder="유리 에어프라이어 단점, 글라스 에어프라이어 후기")
    manual_input = st.text_area("수동 입력 (직접 복사한 리뷰가 있다면 넣어주세요)")
    
    if st.button("한국어 트렌드 수집 시작"):
        if validate_api_key():
            all_results = []
            if keywords:
                kw_list = [k.strip() for k in keywords.split(",")]
                for kw in kw_list:
                    with st.spinner(f"'{kw}' 검색 중..."):
                        try:
                            with DDGS() as ddgs:
                                # [핵심 변경] region='kr-kr' 설정으로 한국 결과 고정
                                # 검색어 뒤에 '네이버'를 붙여서 정확도 향상
                                search_query = f"{kw} 네이버 블로그 후기" 
                                res = list(ddgs.text(search_query, region='kr-kr', safesearch='off', timelimit='y'))
                                
                                if res:
                                    for r in res:
                                        r['source_keyword'] = kw
                                    all_results.extend(res[:5]) # 키워드당 상위 5건
                            time.sleep(1.5) 
                        except Exception as e:
                            st.warning(f"'{kw}' 수집 중 오류: {e}")
            
            if manual_input:
                all_results.append({'title': '사용자 직접 입력 데이터', 'body': manual_input, 'source_keyword': '수동'})

            if not all_results:
                st.error("❌ 수집된 데이터가 없습니다. 키워드를 더 단순하게 바꿔보세요.")
            else:
                st.session_state['consumer_data'] = all_results
                # 요약 시에도 한국어 맥락 강조
                combined_c = "\n".join([f"[{r.get('source_keyword')}] {r.get('title')}: {r.get('body')}" for r in all_results])
                st.session_state['consumer_summary'] = get_quick_summary(api_key, combined_c, "한국 소비자 여론")
                st.success(f"한국어 데이터 총 {len(all_results)}건 확보 완료!")

    if st.session_state['consumer_summary']:
        st.info("📝 한국 소비자 여론 요약")
        st.markdown(st.session_state['consumer_summary'])
        with st.expander("원본 데이터 리스트 확인"):
            st.table(pd.DataFrame(st.session_state['consumer_data'])[['source_keyword', 'title', 'body']])
