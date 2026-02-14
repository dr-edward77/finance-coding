# -*- coding: utf-8 -*-
"""
Korean News Scraper - 한국 주요 뉴스 스크래퍼
네이버 뉴스 랭킹에서 주요 언론사별 인기 기사를 Streamlit GUI로 표시합니다.
실행: streamlit run korean_news_scraper.py
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime


# === 페이지 설정 ===

st.set_page_config(
    page_title="한국 주요 뉴스",
    page_icon="📰",
    layout="centered"
)

# === 상수 ===

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
}

NAVER_RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
REQUEST_DELAY = 0.3


# === 스타일 ===

st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    .news-header {
        color: #1a1a2e;
        font-size: 26px;
        font-weight: bold;
        text-align: center;
        padding: 20px 0 10px 0;
    }
    .news-time {
        color: #6c757d;
        font-size: 13px;
        text-align: center;
        margin-bottom: 20px;
    }
    .press-name {
        color: #1a1a2e;
        font-size: 18px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 8px;
        padding-bottom: 5px;
        border-bottom: 2px solid #e9ecef;
    }
    .news-item {
        padding: 8px 0;
        border-bottom: 1px solid #f1f3f5;
    }
    .news-rank {
        color: #e74c3c;
        font-weight: bold;
        font-size: 14px;
    }
    .news-title {
        color: #2c3e50;
        font-size: 14px;
        text-decoration: none;
    }
    .news-title:hover {
        color: #3498db;
    }
    .news-summary {
        color: #7f8c8d;
        font-size: 12px;
        margin-top: 3px;
        line-height: 1.4;
    }
    .total-count {
        color: #6c757d;
        font-size: 13px;
        text-align: center;
        margin-top: 20px;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# === 핵심 함수 ===

def fetch_page(url, timeout=10, retries=2):
    """URL에서 HTML을 가져와 BeautifulSoup 객체로 반환"""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            # 인코딩 자동 감지: apparent_encoding 사용
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
                continue
            return None


@st.cache_data(ttl=300)
def scrape_naver_ranking():
    """네이버 뉴스 랭킹 (가장 많이 본 뉴스) 스크래핑"""
    articles = []
    soup = fetch_page(NAVER_RANKING_URL)
    if soup is None:
        return articles

    # 랭킹뉴스 박스 찾기
    ranking_boxes = soup.find_all('div', class_='rankingnews_box')
    if not ranking_boxes:
        ranking_boxes = soup.find_all('div', class_=lambda c: c and 'ranking' in c.lower())
        if not ranking_boxes:
            return articles

    for box in ranking_boxes:
        try:
            # 언론사명 추출
            press_tag = box.find('strong', class_='rankingnews_name')
            if not press_tag:
                press_tag = box.find('strong')
            press_name = press_tag.get_text(strip=True) if press_tag else "알 수 없음"

            # 기사 목록 추출
            news_list = box.find('ul', class_='rankingnews_list')
            if not news_list:
                news_list = box.find('ul')
            if not news_list:
                continue

            for li in news_list.find_all('li'):
                try:
                    rank_tag = li.find('em', class_='list_ranking_num')
                    rank = rank_tag.get_text(strip=True) if rank_tag else ""

                    link_tag = li.find('a')
                    if not link_tag:
                        continue

                    title = link_tag.get_text(strip=True)
                    url = link_tag.get('href', '')

                    if not title or len(title) < 5:
                        continue

                    if url and not url.startswith('http'):
                        url = 'https://news.naver.com' + url

                    articles.append({
                        'source': press_name,
                        'rank': rank,
                        'title': title,
                        'url': url,
                    })
                except Exception:
                    continue
        except Exception:
            continue

    return articles


@st.cache_data(ttl=300)
def fetch_article_summary(article_url, max_chars=200):
    """기사 URL에서 본문 요약 (첫 2-3문장) 추출"""
    if not article_url:
        return None

    soup = fetch_page(article_url, timeout=8)
    if soup is None:
        return None

    body_selectors = [
        '#dic_area',
        '#articeBody',
        '#newsEndContents',
        'div.article_body',
        'article',
    ]

    for selector in body_selectors:
        body = soup.select_one(selector)
        if body:
            for tag in body.find_all(['script', 'style', 'span', 'em']):
                if tag.get('class'):
                    tag.decompose()
            text = body.get_text(strip=True)
            if len(text) > 30:
                truncated = text[:max_chars]
                if '.' in truncated:
                    return truncated.rsplit('.', 1)[0] + '.'
                return truncated + '...'

    return None


# === 메인 UI ===

st.markdown('<div class="news-header">한국 주요 뉴스</div>', unsafe_allow_html=True)
st.markdown(f'<div class="news-time">{datetime.now().strftime("%Y-%m-%d %H:%M")} 기준</div>', unsafe_allow_html=True)

# 새로고침 + 요약 옵션
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col2:
    show_summary = st.checkbox("기사 요약 표시")

# 뉴스 로딩
with st.spinner("뉴스를 불러오는 중..."):
    articles = scrape_naver_ranking()

if not articles:
    st.error("뉴스를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# 언론사 필터
all_sources = list(dict.fromkeys(a['source'] for a in articles))
selected_sources = st.multiselect(
    "언론사 필터",
    options=all_sources,
    default=all_sources,
    label_visibility="collapsed",
    placeholder="언론사를 선택하세요 (전체 기본)"
)

if not selected_sources:
    selected_sources = all_sources

filtered = [a for a in articles if a['source'] in selected_sources]

# 뉴스 표시
current_source = None
for article in filtered:
    if article['source'] != current_source:
        current_source = article['source']
        st.markdown(f'<div class="press-name">{current_source}</div>', unsafe_allow_html=True)

    rank_display = f'<span class="news-rank">{article["rank"]}</span> ' if article['rank'] else ''
    st.markdown(
        f'<div class="news-item">'
        f'{rank_display}'
        f'<a class="news-title" href="{article["url"]}" target="_blank">{article["title"]}</a>'
        f'</div>',
        unsafe_allow_html=True
    )

    if show_summary and article.get('url'):
        summary = fetch_article_summary(article['url'])
        if summary:
            st.markdown(f'<div class="news-summary">{summary}</div>', unsafe_allow_html=True)
        time.sleep(REQUEST_DELAY)

st.markdown(
    f'<div class="total-count">총 {len(filtered)}개 기사 (전체 {len(articles)}개)</div>',
    unsafe_allow_html=True
)
