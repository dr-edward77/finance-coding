# -*- coding: utf-8 -*-
"""
Korean News Scraper - 한국 주요 뉴스 스크래퍼
네이버 뉴스 랭킹에서 주요 언론사별 인기 기사를 tkinter GUI로 표시합니다.
실행: python korean_news_scraper.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
import threading
import webbrowser
import time
from datetime import datetime


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


# === 스크래핑 함수 ===

def fetch_page(url, timeout=10, retries=2):
    """URL에서 HTML을 가져와 BeautifulSoup 객체로 반환"""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, 'lxml')
        except requests.RequestException:
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
                continue
            return None


def scrape_naver_ranking():
    """네이버 뉴스 랭킹 스크래핑"""
    articles = []
    soup = fetch_page(NAVER_RANKING_URL)
    if soup is None:
        return articles

    ranking_boxes = soup.find_all('div', class_='rankingnews_box')
    if not ranking_boxes:
        ranking_boxes = soup.find_all('div', class_=lambda c: c and 'ranking' in c.lower())
        if not ranking_boxes:
            return articles

    for box in ranking_boxes:
        try:
            press_tag = box.find('strong', class_='rankingnews_name')
            if not press_tag:
                press_tag = box.find('strong')
            press_name = press_tag.get_text(strip=True) if press_tag else "알 수 없음"

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


# === GUI ===

class NewsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("한국 주요 뉴스")
        self.root.geometry("800x700")
        self.root.configure(bg='#ffffff')
        self.root.minsize(600, 500)

        self.articles = []
        self.filtered = []
        self.url_map = {}  # tree item id -> url

        self._build_ui()
        self._load_news()

    def _build_ui(self):
        # 상단 헤더
        header_frame = tk.Frame(self.root, bg='#ffffff', pady=10)
        header_frame.pack(fill='x')

        tk.Label(
            header_frame, text="한국 주요 뉴스",
            font=('맑은 고딕', 18, 'bold'), bg='#ffffff', fg='#1a1a2e'
        ).pack()

        self.time_label = tk.Label(
            header_frame,
            text=datetime.now().strftime('%Y-%m-%d %H:%M') + " 기준",
            font=('맑은 고딕', 10), bg='#ffffff', fg='#6c757d'
        )
        self.time_label.pack()

        # 툴바
        toolbar = tk.Frame(self.root, bg='#ffffff', pady=5, padx=10)
        toolbar.pack(fill='x')

        refresh_btn = tk.Button(
            toolbar, text="새로고침", command=self._load_news,
            font=('맑은 고딕', 10), bg='#3498db', fg='#ffffff',
            activebackground='#2980b9', activeforeground='#ffffff',
            relief='flat', padx=15, pady=4, cursor='hand2'
        )
        refresh_btn.pack(side='left')

        # 언론사 필터
        tk.Label(
            toolbar, text="  언론사:", font=('맑은 고딕', 10),
            bg='#ffffff', fg='#2c3e50'
        ).pack(side='left', padx=(15, 5))

        self.filter_var = tk.StringVar(value="전체")
        self.filter_combo = ttk.Combobox(
            toolbar, textvariable=self.filter_var, state='readonly',
            width=20, font=('맑은 고딕', 10)
        )
        self.filter_combo['values'] = ["전체"]
        self.filter_combo.pack(side='left')
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filter())

        # 상태 표시
        self.status_label = tk.Label(
            toolbar, text="", font=('맑은 고딕', 9),
            bg='#ffffff', fg='#6c757d'
        )
        self.status_label.pack(side='right')

        # 뉴스 트리뷰
        tree_frame = tk.Frame(self.root, bg='#ffffff', padx=10, pady=5)
        tree_frame.pack(fill='both', expand=True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('News.Treeview',
            font=('맑은 고딕', 11),
            rowheight=32,
            background='#ffffff',
            fieldbackground='#ffffff',
            foreground='#2c3e50',
        )
        style.configure('News.Treeview.Heading',
            font=('맑은 고딕', 11, 'bold'),
            background='#f8f9fa',
            foreground='#1a1a2e',
        )
        style.map('News.Treeview',
            background=[('selected', '#e8f4f8')],
            foreground=[('selected', '#2c3e50')],
        )

        columns = ('rank', 'source', 'title')
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show='headings',
            style='News.Treeview', selectmode='browse'
        )

        self.tree.heading('rank', text='순위')
        self.tree.heading('source', text='언론사')
        self.tree.heading('title', text='기사 제목')

        self.tree.column('rank', width=50, minwidth=40, anchor='center')
        self.tree.column('source', width=120, minwidth=80, anchor='center')
        self.tree.column('title', width=550, minwidth=300, anchor='w')

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 더블클릭으로 기사 열기
        self.tree.bind('<Double-1>', self._open_article)

        # 하단 안내
        footer = tk.Frame(self.root, bg='#f8f9fa', pady=8)
        footer.pack(fill='x', side='bottom')

        tk.Label(
            footer, text="기사를 더블클릭하면 브라우저에서 열립니다",
            font=('맑은 고딕', 9), bg='#f8f9fa', fg='#6c757d'
        ).pack()

    def _load_news(self):
        """백그라운드 스레드에서 뉴스 로딩"""
        self.status_label.config(text="뉴스 불러오는 중...", fg='#e67e22')
        self.tree.delete(*self.tree.get_children())
        self.url_map.clear()

        def _fetch():
            articles = scrape_naver_ranking()
            self.root.after(0, lambda: self._on_news_loaded(articles))

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_news_loaded(self, articles):
        """뉴스 로딩 완료 콜백 (메인 스레드)"""
        self.articles = articles
        self.time_label.config(
            text=datetime.now().strftime('%Y-%m-%d %H:%M') + " 기준"
        )

        if not articles:
            self.status_label.config(text="뉴스를 불러올 수 없습니다", fg='#e74c3c')
            messagebox.showwarning("경고", "뉴스를 불러올 수 없습니다.\n네트워크 연결을 확인해주세요.")
            return

        # 필터 콤보박스 업데이트
        sources = list(dict.fromkeys(a['source'] for a in articles))
        self.filter_combo['values'] = ["전체"] + sources
        self.filter_var.set("전체")

        self._apply_filter()

    def _apply_filter(self):
        """언론사 필터 적용"""
        self.tree.delete(*self.tree.get_children())
        self.url_map.clear()

        selected = self.filter_var.get()
        if selected == "전체":
            self.filtered = self.articles
        else:
            self.filtered = [a for a in self.articles if a['source'] == selected]

        for article in self.filtered:
            item_id = self.tree.insert('', 'end', values=(
                article['rank'],
                article['source'],
                article['title'],
            ))
            self.url_map[item_id] = article['url']

        total = len(self.articles)
        shown = len(self.filtered)
        if selected == "전체":
            self.status_label.config(text=f"총 {total}개 기사", fg='#27ae60')
        else:
            self.status_label.config(text=f"{shown}개 / 전체 {total}개", fg='#27ae60')

    def _open_article(self, event):
        """더블클릭 시 브라우저에서 기사 열기"""
        selected = self.tree.selection()
        if not selected:
            return
        url = self.url_map.get(selected[0], '')
        if url:
            webbrowser.open(url)


def main():
    root = tk.Tk()
    NewsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
