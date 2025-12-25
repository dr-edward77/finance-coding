"""
Market Dashboard - Streamlit 버전 (흰색 테마)
Fear & Greed + VIX, 국채금리, 하이일드, 달러, 금, 비트코인, S&P500, NASDAQ
차트: 1개월, 1년, 3년
"""
import streamlit as st
import requests
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 설정
st.set_page_config(
    page_title="Market Dashboard",
    page_icon="📊",
    layout="centered"
)

# 흰색 테마 스타일
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        max-width: 500px;
        margin: 0 auto;
    }
    .main-title {
        color: #1a1a2e;
        font-size: 28px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    .section-title {
        color: #1a1a2e;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
    }
    .metric-title {
        color: #495057;
        font-size: 14px;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #1a1a2e;
        font-size: 28px;
        font-weight: bold;
    }
    .compare-box {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e9ecef;
        margin: 5px 0;
    }
    .compare-label {
        color: #6c757d;
        font-size: 12px;
        margin-bottom: 3px;
    }
    .compare-value {
        font-size: 22px;
        font-weight: bold;
    }
    .index-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .index-title {
        color: #1a1a2e;
        font-size: 16px;
        font-weight: 600;
    }
    .index-value {
        color: #1a1a2e;
        font-size: 24px;
        font-weight: bold;
    }
    .change-positive {
        color: #2e7d32;
        font-size: 14px;
        font-weight: 500;
    }
    .change-negative {
        color: #d32f2f;
        font-size: 14px;
        font-weight: 500;
    }
    .period-label {
        color: #6c757d;
        font-size: 12px;
        margin: 8px 0 4px 0;
    }
    .footer-text {
        color: #adb5bd;
        font-size: 11px;
        text-align: center;
    }
    hr {
        border: none;
        border-top: 1px solid #e9ecef;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)


# ===== 색상 함수 =====
def get_fng_color(value):
    """Fear & Greed 값에 따른 색상 (흰 배경용)"""
    if value < 25:
        return '#d32f2f'  # Extreme Fear - 빨강
    elif value < 45:
        return '#f57c00'  # Fear - 주황
    elif value < 55:
        return '#fbc02d'  # Neutral - 노랑 (살짝 진하게)
    elif value < 75:
        return '#689f38'  # Greed - 연두
    else:
        return '#2e7d32'  # Extreme Greed - 초록


def get_fng_rating(value):
    """Fear & Greed 상태 텍스트"""
    if value < 25:
        return 'Extreme Fear'
    elif value < 45:
        return 'Fear'
    elif value < 55:
        return 'Neutral'
    elif value < 75:
        return 'Greed'
    else:
        return 'Extreme Greed'


# ===== 데이터 가져오기 =====
@st.cache_data(ttl=300)  # 5분 캐시
def fetch_fear_greed():
    """Fear & Greed 데이터 가져오기"""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://edition.cnn.com/',
            'Origin': 'https://edition.cnn.com',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        fg = data.get('fear_and_greed', {})
        
        return {
            'score': fg.get('score', 0),
            'previous_close': fg.get('previous_close', 0),
            'previous_1_week': fg.get('previous_1_week', 0),
            'previous_1_month': fg.get('previous_1_month', 0),
            'previous_1_year': fg.get('previous_1_year', 0),
            'success': True
        }
    except Exception as e:
        return {'score': 0, 'success': False, 'error': str(e)}


@st.cache_data(ttl=300)
def fetch_market_data(ticker):
    """Yahoo Finance에서 데이터 가져오기"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3 + 30)
        
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        
        # Close 컬럼 추출
        if isinstance(data.columns, pd.MultiIndex):
            close = data['Close'][ticker].dropna()
        else:
            close = data['Close'].dropna()
        
        if len(close) == 0:
            return None
        
        # 현재 값과 변동률
        current = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) > 1 else current
        change = ((current - prev) / prev) * 100 if prev != 0 else 0
        
        # 기간별 데이터
        now = datetime.now()
        
        month_ago = now - timedelta(days=30)
        history_1m = close[close.index >= month_ago.strftime('%Y-%m-%d')]
        
        year_ago = now - timedelta(days=365)
        history_1y = close[close.index >= year_ago.strftime('%Y-%m-%d')]
        
        three_years_ago = now - timedelta(days=365*3)
        history_3y = close[close.index >= three_years_ago.strftime('%Y-%m-%d')]
        
        return {
            'current': current,
            'change': change,
            '1M': history_1m,
            '1Y': history_1y,
            '3Y': history_3y
        }
    except Exception as e:
        return None


# ===== 차트 함수 =====
def create_gauge_chart(value):
    """Fear & Greed 반원형 게이지 (흰 배경용)"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'font': {'size': 50, 'color': '#1a1a2e'}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 2,
                'tickcolor': "#adb5bd",
                'tickfont': {'color': '#6c757d', 'size': 12},
                'tickvals': [0, 25, 50, 75, 100],
            },
            'bar': {'color': get_fng_color(value), 'thickness': 0.3},
            'bgcolor': "#e9ecef",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 25], 'color': '#ffcdd2'},
                {'range': [25, 45], 'color': '#ffe0b2'},
                {'range': [45, 55], 'color': '#fff9c4'},
                {'range': [55, 75], 'color': '#dcedc8'},
                {'range': [75, 100], 'color': '#c8e6c9'},
            ],
            'threshold': {
                'line': {'color': get_fng_color(value), 'width': 4},
                'thickness': 0.8,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "#1a1a2e"},
        height=220,
        margin=dict(l=20, r=20, t=40, b=0)
    )
    
    return fig


def create_line_chart(data, title, height=120):
    """라인 차트 생성 (흰 배경용)"""
    if data is None or len(data) == 0:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values.flatten(),
        mode='lines',
        line=dict(color='#1976d2', width=2),
        fill='tozeroy',
        fillcolor='rgba(25, 118, 210, 0.15)',
        name=title
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#f8f9fa',
        font={'color': '#6c757d', 'size': 10},
        height=height,
        margin=dict(l=10, r=10, t=5, b=20),
        xaxis=dict(
            showgrid=False,
            linecolor='#dee2e6',
            tickfont={'size': 9, 'color': '#6c757d'}
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e9ecef',
            linecolor='#dee2e6',
            tickfont={'size': 9, 'color': '#6c757d'}
        ),
        showlegend=False
    )
    
    return fig


# ===== 메인 UI =====
st.markdown('<p class="main-title">📊 Market Dashboard</p>', unsafe_allow_html=True)

# 새로고침 버튼
if st.button("🔄 새로고침"):
    st.cache_data.clear()

# ===== 1. Fear & Greed Index =====
st.markdown("---")
st.markdown('<p class="section-title">Fear & Greed Index</p>', unsafe_allow_html=True)

fng_data = fetch_fear_greed()

if fng_data['success'] and fng_data['score'] > 0:
    score = fng_data['score']
    rating = get_fng_rating(score)
    color = get_fng_color(score)
    
    # 게이지 차트
    gauge_fig = create_gauge_chart(score)
    st.plotly_chart(gauge_fig, use_container_width=True)
    
    # 상태 표시
    st.markdown(
        f'<p style="text-align: center; font-size: 20px; font-weight: bold; color: {color}; margin-top: -10px;">{rating}</p>',
        unsafe_allow_html=True
    )
    
    # 비교 데이터 (2x2)
    col1, col2 = st.columns(2)
    
    comparisons = [
        ('previous_close', '전일종가'),
        ('previous_1_week', '1주 전'),
        ('previous_1_month', '1달 전'),
        ('previous_1_year', '1년 전'),
    ]
    
    for i, (key, label) in enumerate(comparisons):
        val = fng_data.get(key, 0)
        val_color = get_fng_color(val)
        
        with [col1, col2][i % 2]:
            st.markdown(f"""
            <div class="compare-box">
                <div class="compare-label">{label}</div>
                <div class="compare-value" style="color: {val_color};">{val:.0f}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.warning("Fear & Greed 데이터를 가져올 수 없습니다.")


# ===== 지수 섹션 함수 =====
def render_index_section(title, ticker, format_str='{:.2f}'):
    """지수 섹션 렌더링"""
    st.markdown("---")
    
    data = fetch_market_data(ticker)
    
    if data:
        current = data['current']
        change = data['change']
        
        if change >= 0:
            change_html = f'<span class="change-positive">+{change:.2f}%</span>'
        else:
            change_html = f'<span class="change-negative">{change:.2f}%</span>'
        
        # 헤더 (타이틀 + 값)
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span class="index-title">{title}</span>
            <span>
                <span class="index-value">{format_str.format(current)}</span>
                {change_html}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # 차트 3개 (1개월, 1년, 3년)
        periods = [('1M', '1개월'), ('1Y', '1년'), ('3Y', '3년')]
        
        for period_key, period_label in periods:
            if period_key in data and len(data[period_key]) > 0:
                st.markdown(f'<p class="period-label">{period_label}</p>', unsafe_allow_html=True)
                chart = create_line_chart(data[period_key], period_label)
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
    else:
        st.markdown(f'<span class="index-title">{title}</span>', unsafe_allow_html=True)
        st.warning("데이터를 가져올 수 없습니다.")


# ===== 2. VIX =====
render_index_section("VIX (공포지수)", "^VIX", '{:.2f}')

# ===== 3. 10년물 국채금리 =====
render_index_section("10년물 국채금리 (%)", "^TNX", '{:.2f}')

# ===== 4. 하이일드 스프레드 (HYG ETF) =====
render_index_section("하이일드 (HYG ETF)", "HYG", '{:.2f}')

# ===== 5. 달러 인덱스 =====
render_index_section("달러 인덱스", "DX-Y.NYB", '{:.2f}')

# ===== 6. 금 =====
render_index_section("금 (Gold)", "GC=F", '{:,.0f}')

# ===== 7. 비트코인 =====
render_index_section("비트코인", "BTC-USD", '{:,.0f}')

# ===== 8. S&P 500 =====
render_index_section("S&P 500", "^GSPC", '{:,.0f}')

# ===== 9. NASDAQ =====
render_index_section("NASDAQ", "^IXIC", '{:,.0f}')


# 업데이트 시간
st.markdown("---")
st.markdown(
    f'<p class="footer-text">마지막 업데이트: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>Data: CNN, Yahoo Finance</p>',
    unsafe_allow_html=True
)
