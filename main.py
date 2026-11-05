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

    # 필요한 열만 사용
    df = df[["날짜", "식사", "메뉴"]].copy()

    # 결측치 제거
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
    예: 돈까스(소스) -> 돈까스
    """

    menu = str(menu)

    # 일반 괄호 및 전각 괄호 안의 내용 제거
    menu = re.sub(r"\([^)]*\)", "", menu)
    menu = re.sub(r"（[^）]*）", "", menu)

    return menu.strip()


# ==========================================
# 4. 하루 식단을 장바구니로 변환
# ==========================================

transactions = []

for menu_text in df["메뉴"]:

    # 세로줄을 기준으로 메뉴 분리
    menus = str(menu_text).split("|")

    # 메뉴 이름 정리
    menus = [clean_menu(menu) for menu in menus]

    # 빈 메뉴 제거
    menus = [menu for menu in menus if menu]

    # 하루 안에서 같은 메뉴가 중복되면 한 번만 계산
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
# 5. 메뉴 등장 횟수 계산
# ==========================================

menu_count = Counter()

for transaction in transactions:
    menu_count.update(transaction)


# ==========================================
# 6. 함께 등장한 메뉴 쌍 계산
# ==========================================

pair_count = Counter()

for transaction in transactions:

    # 하루 식단에서 가능한 모든 메뉴 쌍
    pairs = combinations(transaction, 2)

    pair_count.update(pairs)


# 함께 나온 적이 있는 서로 다른 메뉴 쌍의 수
total_pairs = len(pair_count)


# ==========================================
# 7. 연관 규칙 계산
# ==========================================

rules = []

for (menu_a, menu_b), count in pair_count.items():

    # 지지도
    support = count / total_days

    # 메뉴 A -> 메뉴 B
    confidence_ab = count / menu_count[menu_a]

    # 메뉴 B의 등장 비율
    support_b = menu_count[menu_b] / total_days

    # 향상도
    lift_ab = confidence_ab / support_b

    rules.append({
        "조건": menu_a,
        "결과": menu_b,
        "동시": count,
        "지지도": support,
        "신뢰도": confidence_ab,
        "향상도": lift_ab
    })

    # 메뉴 B -> 메뉴 A
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


rules_df = pd.DataFrame(rules)


# ==========================================
# 8. 데이터 요약
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
# 9. 메뉴 및 정렬 기준 선택
# ==========================================

st.divider()
st.header("🔍 연관 규칙 찾아보기")

col1, col2 = st.columns(2)

with col1:

    selected_menu = st.selectbox(
        "메뉴 선택",
        options=["전체 메뉴"] + all_menus,
        index=0
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"],
        index=0
    )


# ==========================================
# 10. 메뉴 필터링
# ==========================================

filtered_df = rules_df.copy()

if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ]


# ==========================================
# 11. 정렬
# ==========================================

sort_columns = {
    "향상도 순": ["향상도", "신뢰도", "동시"],
    "신뢰도 순": ["신뢰도", "향상도", "동시"],
    "동시 순": ["동시", "향상도", "신뢰도"]
}

filtered_df = filtered_df.sort_values(
    by=sort_columns[sort_option],
    ascending=False
).reset_index(drop=True)


# ==========================================
# 12. 연관 규칙 표
# ==========================================

st.subheader("📋 메뉴 연관 규칙 표")

st.caption(
    "A → B는 A가 나온 날 B도 함께 나올 가능성을 의미합니다. "
    "화살표 방향을 바꾼 규칙도 별도로 표시합니다."
)

st.dataframe(
    filtered_df.style.format({
        "지지도": "{:.2%}",
        "신뢰도": "{:.2%}",
        "향상도": "{:.3f}"
    }),
    use_container_width=True,
    hide_index=True,
    height=500
)


# ==========================================
# 13. 향상도 상위 10개 그래프
# ==========================================

st.divider()
st.header("📈 향상도 상위 10개 메뉴 규칙")

st.caption(
    "향상도가 높을수록 두 메뉴가 서로 독립적이라고 가정했을 때보다 "
    "함께 등장하는 경향이 강합니다."
)

if len(filtered_df) > 0:

    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=False
        )
        .head(10)
        .copy()
    )

    # 그래프용 메뉴 조합 이름
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    # 가로 막대그래프
    fig = px.bar(
        top10.sort_values("향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10.sort_values(
            "향상도",
            ascending=True
        )["향상도"].round(2),
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "메뉴 연관 규칙"
        },
        title="향상도가 높은 메뉴 조합 TOP 10",
        color="향상도",
        color_continuous_scale="YlOrBr"
    )

    fig.update_layout(
        height=550,
        yaxis_title="",
        xaxis_title="향상도",
        coloraxis_showscale=False
    )

    fig.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.warning("선택한 메뉴와 관련된 연관 규칙이 없습니다.")


# ==========================================
# 14. 분석 결과 해석 안내
# ==========================================

st.divider()
st.header("💡 연관 규칙 지표 이해하기")

with st.expander("지지도, 신뢰도, 향상도란?"):

    st.markdown("""
    **① 지지도 (Support)**

    전체 급식일 중 두 메뉴가 함께 등장한 날의 비율입니다.

    지지도가 높으면 전체 급식에서 해당 메뉴 조합이 자주 등장했다는 뜻입니다.

    **② 신뢰도 (Confidence)**

    조건 메뉴가 등장했을 때 결과 메뉴도 함께 등장한 비율입니다.

    예를 들어 A → B의 신뢰도가 80%라면,
    A가 나온 날 중 80%에 B도 나왔다는 뜻입니다.

    **③ 향상도 (Lift)**

    두 메뉴가 서로 독립적으로 등장한다고 가정했을 때보다
    실제로 함께 등장하는 정도가 얼마나 높은지 나타냅니다.

    - 향상도 > 1 : 함께 등장하는 경향이 있음
    - 향상도 = 1 : 독립적으로 등장하는 것과 비슷함
    - 향상도 < 1 : 함께 등장하는 경향이 적음

    **주의:** 향상도가 높더라도 함께 등장한 횟수(동시)가 적을 수 있으므로
    지지도와 동시 등장 횟수도 함께 확인하는 것이 좋습니다.
    """)
