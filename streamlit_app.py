"""
CNN Fear & Greed Index - Streamlit 버전
iPhone/모바일에서도 볼 수 있는 웹앱
"""
import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="Fear & Greed Index",
    page_icon="📊",
    layout="centered"
)

# 다크 테마 스타일
st.markdown("""
<style>
    .stApp {
        background-color: #0a0a1a;
    }
    .big-number {
        font-size: 72px;
        font-weight: bold;
        text-align: center;
        margin: 0;
    }
    .rating-text {
        font-size: 24px;
        text-align: center;
        font-weight: 600;
    }
    .info-card {
        background-color: #1a1a2e;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .info-label {
        color: #8888aa;
        font-size: 14px;
    }
    .info-value {
        font-size: 28px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def get_color(value):
    """값에 따른 색상 반환"""
    if value < 25:
        return '#c62828'  # Extreme Fear - 빨강
    elif value < 45:
        return '#ef6c00'  # Fear - 주황
    elif value < 55:
        return '#fdd835'  # Neutral - 노랑
    elif value < 75:
        return '#7cb342'  # Greed - 연두
    else:
        return '#2e7d32'  # Extreme Greed - 초록


def get_rating(value):
    """값에 따른 상태 텍스트"""
    if value < 25:
        return 'Extreme Fear', '극단적 공포'
    elif value < 45:
        return 'Fear', '공포'
    elif value < 55:
        return 'Neutral', '중립'
    elif value < 75:
        return 'Greed', '탐욕'
    else:
        return 'Extreme Greed', '극단적 탐욕'


def create_gauge(value):
    """Plotly 반원형 게이지 생성"""
    color = get_color(value)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'font': {'size': 60, 'color': 'white'}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 2,
                'tickcolor': "#4a4a6a",
                'tickfont': {'color': '#8888aa', 'size': 14},
                'tickvals': [0, 25, 50, 75, 100],
            },
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "#1a1a2e",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 25], 'color': '#c62828'},
                {'range': [25, 45], 'color': '#ef6c00'},
                {'range': [45, 55], 'color': '#fdd835'},
                {'range': [55, 75], 'color': '#7cb342'},
                {'range': [75, 100], 'color': '#2e7d32'},
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.8,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "white"},
        height=300,
        margin=dict(l=30, r=30, t=50, b=0)
    )
    
    return fig


@st.cache_data(ttl=300)  # 5분 캐시
def fetch_data():
    """CNN API에서 데이터 가져오기"""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        fg = data.get('fear_and_greed', {})
        
        return {
            'score': fg.get('score', 50),
            'rating': fg.get('rating', ''),
            'previous_close': fg.get('previous_close', 0),
            'previous_1_week': fg.get('previous_1_week', 0),
            'previous_1_month': fg.get('previous_1_month', 0),
            'previous_1_year': fg.get('previous_1_year', 0),
            'success': True
        }
        
    except Exception as e:
        return {
            'score': 50,
            'error': str(e),
            'success': False
        }


# 메인 UI
st.title("📊 Fear & Greed Index")

# 새로고침 버튼
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()

# 데이터 가져오기
data = fetch_data()

if data['success']:
    score = data['score']
    rating_en, rating_kr = get_rating(score)
    color = get_color(score)
    
    # 게이지 차트
    fig = create_gauge(score)
    st.plotly_chart(fig, use_container_width=True)
    
    # 상태 표시
    st.markdown(
        f'<p class="rating-text" style="color: {color};">{rating_en} ({rating_kr})</p>',
        unsafe_allow_html=True
    )
    
    st.divider()
    
    # 비교 데이터
    st.subheader("📈 비교")
    
    col1, col2, col3, col4 = st.columns(4)
    
    comparisons = [
        (col1, '전일 종가', data.get('previous_close', 0)),
        (col2, '1주 전', data.get('previous_1_week', 0)),
        (col3, '1달 전', data.get('previous_1_month', 0)),
        (col4, '1년 전', data.get('previous_1_year', 0)),
    ]
    
    for col, label, value in comparisons:
        with col:
            val_color = get_color(value)
            st.markdown(f"""
            <div class="info-card">
                <div class="info-label">{label}</div>
                <div class="info-value" style="color: {val_color};">{value:.0f}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # 업데이트 시간
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
else:
    st.error(f"데이터를 가져올 수 없습니다: {data.get('error', 'Unknown error')}")
    st.info("잠시 후 다시 시도해주세요.")


# 푸터
st.divider()
st.caption("Data source: CNN Business Fear & Greed Index")
