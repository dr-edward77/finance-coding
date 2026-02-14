# -*- coding: utf-8 -*-
"""
Korean News Scraper - 한국 주요 뉴스 스크래퍼
네이버 뉴스 랭킹에서 주요 언론사별 인기 기사를 수집합니다.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import time
import argparse
from datetime import datetime


# === 상수 ===

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

NAVER_RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
REQUEST_DELAY = 0.5
DEFAULT_OUTPUT_DIR = "news_output"


# === 핵심 함수 ===

def fetch_page(url, timeout=10, retries=2):
    """URL에서 HTML을 가져와 BeautifulSoup 객체로 반환"""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml', from_encoding='utf-8')
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
                continue
            print(f"  [오류] {url} 접속 실패: {e}")
            return None


def scrape_naver_ranking():
    """네이버 뉴스 랭킹 (가장 많이 본 뉴스) 스크래핑"""
    articles = []
    soup = fetch_page(NAVER_RANKING_URL)
    if soup is None:
        return articles

    # 랭킹뉴스 박스 찾기
    ranking_boxes = soup.find_all('div', class_='rankingnews_box')
    if not ranking_boxes:
        # fallback: 클래스명이 변경된 경우
        ranking_boxes = soup.find_all('div', class_=lambda c: c and 'ranking' in c.lower())
        if not ranking_boxes:
            print("  [경고] 랭킹뉴스 구조가 변경되었을 수 있습니다.")
            print("  [경고] 네이버 뉴스 랭킹 페이지의 HTML 구조를 확인해주세요.")
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

                    # 상대 URL 처리
                    if url and not url.startswith('http'):
                        url = 'https://news.naver.com' + url

                    articles.append({
                        'source': press_name,
                        'rank': rank,
                        'title': title,
                        'summary': '',
                        'url': url,
                        'scraped_at': datetime.now().isoformat(),
                    })
                except Exception:
                    continue
        except Exception:
            continue

    return articles


def fetch_article_summary(article_url, max_chars=200):
    """기사 URL에서 본문 요약 (첫 2-3문장) 추출"""
    if not article_url:
        return None

    soup = fetch_page(article_url, timeout=8)
    if soup is None:
        return None

    # 네이버 뉴스 기사 본문 선택자 (우선순위 순)
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
            # 불필요한 요소 제거
            for tag in body.find_all(['script', 'style', 'span.end_photo_org', 'em.img_desc']):
                tag.decompose()
            text = body.get_text(strip=True)
            if len(text) > 30:
                # 첫 ~200자 (약 2-3문장)
                truncated = text[:max_chars]
                if '.' in truncated:
                    return truncated.rsplit('.', 1)[0] + '.'
                return truncated + '...'

    return None


# === 출력 함수 ===

def format_console_output(articles):
    """콘솔 출력용 포맷팅"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  한국 주요 뉴스 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    lines.append("=" * 60)

    current_source = None
    for article in articles:
        if article['source'] != current_source:
            current_source = article['source']
            lines.append(f"\n▶ {current_source}")
            lines.append("-" * 40)

        rank_prefix = f"  {article['rank']}. " if article['rank'] else "  - "
        lines.append(f"{rank_prefix}{article['title']}")
        if article.get('summary'):
            lines.append(f"     {article['summary']}")
        lines.append(f"     {article['url']}")

    lines.append(f"\n총 {len(articles)}개 기사 수집됨")
    return "\n".join(lines)


def save_to_json(articles, filepath):
    """JSON 파일로 저장"""
    try:
        output = {
            'scraped_at': datetime.now().isoformat(),
            'total_articles': len(articles),
            'articles': articles
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"  [저장] {filepath}")
    except Exception as e:
        print(f"  [오류] JSON 저장 실패: {e}")


# === CLI ===

def parse_args():
    parser = argparse.ArgumentParser(
        description='한국 주요 뉴스 스크래퍼 (Korean News Scraper)'
    )
    parser.add_argument(
        '--detail', action='store_true',
        help='기사 요약 (본문 첫 2-3문장)도 수집'
    )
    parser.add_argument(
        '--output', choices=['console', 'json', 'both'], default='both',
        help='출력 형식 (기본값: both)'
    )
    parser.add_argument(
        '--output-dir', default=DEFAULT_OUTPUT_DIR,
        help=f'JSON 출력 디렉토리 (기본값: {DEFAULT_OUTPUT_DIR})'
    )
    return parser.parse_args()


def main():
    # 콘솔 한글 출력 깨짐 방지
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    args = parse_args()

    print("한국 주요 뉴스 수집을 시작합니다...")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1단계: 네이버 랭킹뉴스 수집
    print("\n[1/2] 네이버 랭킹뉴스 수집 중...")
    all_articles = scrape_naver_ranking()
    print(f"  {len(all_articles)}개 기사 수집됨")

    # 2단계: 기사 요약 수집 (선택)
    if args.detail and all_articles:
        print("\n[2/2] 기사 요약 수집 중...")
        for i, article in enumerate(all_articles):
            summary = fetch_article_summary(article['url'])
            if summary:
                article['summary'] = summary
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(all_articles)} 처리 완료")
            time.sleep(REQUEST_DELAY)
    else:
        print("\n[2/2] 요약 수집 건너뜀 (--detail 옵션 사용시 수집)")

    # 결과 확인
    if not all_articles:
        print("\n수집된 기사가 없습니다.")
        sys.exit(1)

    # 3단계: 출력
    if args.output in ('console', 'both'):
        print(format_console_output(all_articles))

    if args.output in ('json', 'both'):
        os.makedirs(args.output_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(args.output_dir, f'korean_news_{date_str}.json')
        save_to_json(all_articles, filepath)

    print(f"\n완료! 총 {len(all_articles)}개 기사 수집됨.")


if __name__ == "__main__":
    main()
