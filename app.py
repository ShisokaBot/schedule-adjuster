import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="スケジュール調整", layout="wide")
st.title("4月〜5月 スケジュール回答")
st.write("※入力した内容は他のメンバーからは見えません。")

# メンバー（適宜書き換えてください）
MEMBERS = [f"奏者{i}" for i in range(1, 16)]

# 平日リスト作成
date_list = []
curr = datetime(2026, 4, 1)
while curr <= datetime(2026, 5, 31):
    if curr.weekday() < 5:
        date_list.append(curr.strftime("%m/%d(%a)"))
    curr += timedelta(days=1)

user_name = st.selectbox("あなたの名前を選択してください", ["選択してください"] + MEMBERS)

if user_name != "選択してください":
    st.subheader(f"{user_name} さんの入力")
    df = pd.DataFrame("", index=date_list, columns=["午前", "午後", "夜間"])
    
    # 編集可能な表
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        column_config={
            "午前": st.column_config.SelectboxColumn(options=["", "❌"]),
            "午後": st.column_config.SelectboxColumn(options=["", "❌"]),
            "夜間": st.column_config.SelectboxColumn(options=["", "❌"]),
        }
    )

    if st.button("送信（保存）する"):
        # ※ここに保存処理を追加予定
        st.success("回答を受け付けました！")
