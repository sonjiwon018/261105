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
st.caption("송탄고 급식 메뉴의 연관 규칙을 분석합니다.")

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
    st.error(str(e))
    st.stop()


# ==========================================
# 3. 메뉴 이름 정리
# ==========================================

def clean_menu(menu):
    menu = str(menu)

    # 괄호와 괄호 안의 내용 제거
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

    # 하루 안의 중복 메뉴 제거
    menus = sorted(set(menus))

    transactions.append(menus)


total_days = len(transactions)

all_menus = sorted({
    menu
    for transaction in transactions
    for menu in transaction
})

total_menu_types = len(all_menus)


# ==========================================
# 5. 메뉴별 등장 횟수
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


total_pairs = len(pair_count)


# ==========================================
# 7. 연관 규칙 계산
# ==========================================

rules = []

for (menu_a, menu_b), count in pair_count.items():

    support = count / total_days

    # A -> B
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

    # B -> A
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

col1.metric("급식 일수", f"{total_days}일")
col2.metric("메뉴 종류 수", f"{total_menu_types}개")
col3.metric("함께 나온 메뉴 쌍", f"{total_pairs}쌍")


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
        key="rule_menu"
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"]
    )


# ==========================================
# 10. 최소 동시 일수
# ==========================================

min_days = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 규칙은 제외합니다."
)


# ==========================================
# 11. 규칙 필터링
# ==========================================

filtered_df = rules_df.copy()

# 메뉴 필터
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
    "향상도 순": ["향상도", "신뢰도", "동시"],
    "신뢰도 순": ["신뢰도", "향상도", "동시"],
    "동시 순": ["동시", "향상도", "신뢰도"]
}

filtered_df = filtered_df.sort_values(
    by=sort_columns[sort_option],
    ascending=False
).reset_index(drop=True)


# ==========================================
# 13. 남은 규칙 개수
# ==========================================

st.write(
    f"현재 조건에 해당하는 연관 규칙은 총 **{len(filtered_df)}개**입니다."
)


# ==========================================
# 14. 연관 규칙 표
# ==========================================

st.subheader("📋 메뉴 연관 규칙 표")

st.caption(
    "A → B는 A가 나온 날 B도 함께 나온 비율입니다. "
    "반대 방향의 규칙도 별도로 표시합니다."
)

if not filtered_df.empty:

    display_df = filtered_df.style.format({
        "지지도": "{:.2%}",
        "신뢰도": "{:.2%}",
        "향상도": "{:.3f}"
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )

else:
    st.warning(
        "조건에 맞는 연관 규칙이 없습니다. "
        "메뉴를 바꾸거나 최소 동시 일수를 낮춰 보세요."
    )


# ==========================================
# 15. 향상도 상위 10개 그래프
# ==========================================

st.divider()
st.header("📈 향상도 상위 10개 메뉴 규칙")

st.caption(
    "향상도가 높을수록 두 메뉴가 독립적으로 등장할 때보다 "
    "실제로 함께 등장하는 경향이 강합니다."
)

if not filtered_df.empty:

    top10 = filtered_df.sort_values(
        by=["향상도", "신뢰도", "동시"],
        ascending=False
    ).head(10).copy()

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    plot_df = top10.sort_values(
        "향상도",
        ascending=True
    ).copy()

    fig = px.bar(
        plot_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text=plot_df["향상도"].round(2),
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

    fig.update_traces(textposition="outside")

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:
    st.warning("그래프로 나타낼 규칙이 없습니다.")


# ==========================================
# 16. 함께 나온 적 없는 짝
# ==========================================

st.divider()
st.header("🚫 함께 나온 적 없는 짝")

st.caption(
    "선택한 메뉴와 같은 날 한 번도 함께 나오지 않았지만, "
    "혼자서는 10일 이상 등장한 메뉴를 찾아봅니다."
)


# ==========================================
# 17. 별도의 메뉴 선택
# ==========================================

selected_base_menu = st.selectbox(
    "기준 메뉴 선택 (함께 나온 적 없는 짝 찾기)",
    options=all_menus,
    key="never_together_menu"
)


# ==========================================
# 18. 함께 나온 적 없는 메뉴 찾기
# ==========================================

if selected_base_menu:

    # 선택한 메뉴의 등장 일수
    base_menu_days = menu_count[selected_base_menu]

    never_together = []

    for other_menu in all_menus:

        # 자기 자신 제외
        if other_menu == selected_base_menu:
            continue

        # 10일 미만 등장한 메뉴 제외
        if menu_count[other_menu] < 10:
            continue

        # 두 메뉴의 조합
        pair = tuple(sorted([
            selected_base_menu,
            other_menu
        ]))

        together_days = pair_count.get(pair, 0)

        # 한 번도 함께 나오지 않은 메뉴
        if together_days == 0:

            never_together.append({
                "메뉴": other_menu,
                "등장 일수": menu_count[other_menu]
            })

    # 등장 일수 내림차순 정렬
    never_df = pd.DataFrame(
        never_together,
        columns=["메뉴", "등장 일수"]
    )

    never_df = never_df.sort_values(
        by="등장 일수",
        ascending=False
    ).reset_index(drop=True)


    # ======================================
    # 19. 결과 표시
    # ======================================

    st.write(
        f"선택한 메뉴 **{selected_base_menu}**는 "
        f"총 **{base_menu_days}일** 등장했습니다."
    )

    st.write(
        f"함께 나온 적이 없는 메뉴 중 "
        f"10일 이상 등장한 메뉴는 **{len(never_df)}개**입니다."
    )

    if not never_df.empty:

        st.dataframe(
            never_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "조건에 맞는 메뉴가 없습니다. "
            "다른 기준 메뉴를 선택해 보세요."
        )


# ==========================================
# 20. 연관 규칙 지표 설명
# ==========================================

st.divider()
st.header("💡 연관 규칙 지표 이해하기")

with st.expander("지지도, 신뢰도, 향상도란?"):

    st.markdown("**① 지지도 (Support)**")
    st.write(
        "전체 급식일 중 두 메뉴가 함께 등장한 날의 비율입니다."
    )

    st.markdown("**② 신뢰도 (Confidence)**")
    st.write(
        "조건 메뉴가 등장했을 때 결과 메뉴도 함께 등장한 비율입니다."
    )

    st.markdown("**③ 향상도 (Lift)**")
    st.write(
        "두 메뉴가 독립적으로 등장한다고 가정했을 때보다 "
        "실제로 함께 등장하는 정도가 얼마나 높은지 나타냅니다."
    )

    st.write("- 향상도 > 1 : 함께 등장하는 경향이 있음")
    st.write("- 향상도 = 1 : 독립적으로 등장하는 것과 비슷함")
    st.write("- 향상도 < 1 : 함께 등장하는 경향이 적음")

    st.warning(
        "향상도가 높더라도 함께 등장한 횟수가 적을 수 있으므로 "
        "지지도와 동시 등장 횟수도 함께 확인하는 것이 좋습니다."
    )
