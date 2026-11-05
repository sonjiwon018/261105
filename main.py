```python
# ==========================================
# 급식 규칙 찾기
# 송탄고 급식 메뉴 연관 규칙 분석
# ==========================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from itertools import combinations
from collections import Counter

# ==========================================
# 1. 기본 설정
# ==========================================

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.caption(
    "송탄고 급식 데이터를 이용해 어떤 메뉴들이 함께 등장하는지 분석합니다."
)

CSV_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


# ==========================================
# 2. 데이터 불러오기
# ==========================================

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL, encoding="utf-8")

    df = df[["날짜", "식사", "메뉴"]].copy()
    df = df.dropna(subset=["메뉴"])

    return df


try:
    df = load_data()

except Exception as e:
    st.error("CSV 데이터를 불러오지 못했습니다.")
    st.error(f"오류 내용: {e}")
    st.stop()


# ==========================================
# 3. 메뉴 이름 정리
# ==========================================

def clean_menu(menu):
    """
    메뉴 이름에서 괄호와 괄호 안의 내용 제거
    """

    menu = str(menu)

    menu = re.sub(r"\([^)]*\)", "", menu)
    menu = re.sub(r"（[^）]*）", "", menu)

    return menu.strip()


# ==========================================
# 4. 하루 식단을 장바구니로 변환
# ==========================================

transactions = []

for menu_text in df["메뉴"]:

    menus = str(menu_text).split("|")

    menus = [clean_menu(menu) for menu in menus]

    menus = [menu for menu in menus if menu]

    # 하루 안에서 중복된 메뉴는 한 번만 계산
    menus = sorted(set(menus))

    transactions.append(menus)


total_days = len(transactions)

# 전체 메뉴 종류
all_menus = sorted({
    menu
    for transaction in transactions
    for menu in transaction
})

total_menu_types = len(all_menus)


# ==========================================
# 5. 메뉴별 등장 횟수 계산
# ==========================================

menu_count = Counter()

for transaction in transactions:
    menu_count.update(transaction)


# ==========================================
# 6. 함께 등장한 메뉴 쌍 계산
# ==========================================

pair_count = Counter()

for transaction in transactions:

    pairs = combinations(transaction, 2)

    pair_count.update(pairs)


# 서로 다른 메뉴 쌍의 수
total_pairs = len(pair_count)


# ==========================================
# 7. 연관 규칙 계산
# ==========================================

rules = []

for (menu_a, menu_b), count in pair_count.items():

    # 지지도
    support = count / total_days

    # A → B
    confidence_ab = count / menu_count[menu_a]

    support_b = menu_count[menu_b] / total_days

    lift_ab = confidence_ab / support_b

    rules.append({
        "조건": menu_a,
        "결과": menu_b,
        "동시": count,
        "지지도": support,
        "신뢰도": confidence_ab,
        "향상도": lift_ab
    })

    # B → A
    confidence_ba = count / menu_count[menu_b]

    support_a = menu_count[menu_a] / total_days

    lift_ba = confidence_ba / support_a

    rules.append({
        "조건": menu_b,
        "결과": menu_a,
        "동시": count,
        "지지도": support,
        "신뢰도": confidence_ba,
        "향상도": lift_ba
    })


columns = [
    "조건", "결과", "동시",
    "지지도", "신뢰도", "향상도"
]

rules_df = pd.DataFrame(rules, columns=columns)


# ==========================================
# 8. 급식 데이터 요약
# ==========================================

st.divider()
st.header("📊 급식 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric(
    "급식 일수",
    f"{total_days}일"
)

col2.metric(
    "메뉴 종류 수",
    f"{total_menu_types}개"
)

col3.metric(
    "함께 나온 메뉴 쌍",
    f"{total_pairs}쌍"
)


# ==========================================
# 9. 연관 규칙 찾아보기
# ==========================================

st.divider()
st.header("🔍 연관 규칙 찾아보기")

col1, col2 = st.columns(2)

with col1:

    selected_menu = st.selectbox(
        "메뉴 선택 (규칙 좁혀 보기)",
        options=["전체 메뉴"] + all_menus,
        index=0,
        key="rule_menu"
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"],
        index=0
    )


# ==========================================
# 10. 최소 동시 일수 슬라이더
# ==========================================

min_days = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 메뉴 규칙은 제외합니다."
)


# ==========================================
# 11. 규칙 필터링
# ==========================================

filtered_df = rules_df.copy()

# 메뉴 선택 필터
if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ]

# 최소 동시 일수 필터
filtered_df = filtered_df[
    filtered_df["동시"] >= min_days
]


# ==========================================
# 12. 정렬
# ==========================================

sort_columns = {
    "향
