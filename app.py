import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# タイトル
st.title("2026年3月末〜5月末 スケジュール回答")

# --- 奏者リスト ---
RAW_MEMBERS = ["伊藤友馬", "宇佐見優", "岩崎花保", "小野江良太", "近藤圭", "志村樺奈", "篠嶋祐希", "竹之下滉", "長谷川太郎", "西宥介", "西部圭亮", "舟久保優貴", "布施砂丘彦", "前田優紀"]
MEMBERS = sorted(list(set(RAW_MEMBERS)))

# --- 日付リストの作成 ---
wd_ja = ["月", "火", "水", "木", "金", "土", "日"]
date_objects, date_labels = [], []
curr, end_date = datetime(2026, 3, 30), datetime(2026, 5, 31)

while curr <= end_date:
    if curr.weekday() < 5:
        date_objects.append(curr.date())
        date_labels.append(f"{curr.month}/{curr.day}({wd_ja[curr.weekday()]})")
    curr += timedelta(days=1)
date_map = dict(zip(date_labels, date_objects))

user_name = st.selectbox("あなたの名前を選択してください", ["選択してください"] + MEMBERS)

if user_name != "選択してください":
    # チェックボックス形式（True/False）で状態を管理
    if 'df_input' not in st.session_state or st.session_state.get('current_user') != user_name:
        st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])
        st.session_state.current_user = user_name

    # 説明文（改行・太字・アンダーバー）
    st.subheader(f"{user_name} さんの入力画面")
    st.markdown("下記のうち、<u>**空いていない**</u>時間帯にチェック✅を入れてください。", unsafe_allow_html=True)
    st.markdown("入力を終えたら、送信ボタンを押してください。")
    
    # 編集可能な表（チェックボックス形式）
    edited_df = st.data_editor(
        st.session_state.df_input,
        use_container_width=True,
        column_config={
            "午前": st.column_config.CheckboxColumn(default=False),
            "午後": st.column_config.CheckboxColumn(default=False),
            "夜間": st.column_config.CheckboxColumn(default=False),
        }
    )

    if st.button("この内容で送信する"):
        new_rows = []
        for label, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                # チェック（True）が入っている箇所を「❌」として送信
                if row[slot] == True:
                    new_rows.append({
                        "name": user_name,
                        "date": date_map[label],
                        "slot": slot,
                        "status": "❌"
                    })
        
        try:
            sheetNM = "予定表"
            existing_data = conn.read(worksheet=sheetNM)
            new_df = pd.DataFrame(new_rows)
            
            if not existing_data.empty and "name" in existing_data.columns:
                existing_data['date'] = pd.to_datetime(existing_data['date']).dt.date
                clean_existing = existing_data[existing_data["name"] != user_name]
                updated_df = pd.concat([clean_existing, new_df], ignore_index=True)
            else:
                updated_df = new_df
            
            conn.update(worksheet=sheetNM, data=updated_df)
            st.success(f"{user_name} さんの回答を送信しました！")
            st.balloons()
            # 送信後、現在の入力内容をセッションに保存
            st.session_state.df_input = edited_df
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
