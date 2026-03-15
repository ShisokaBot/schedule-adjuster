import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_now_jp():
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    return datetime.now(tokyo_tz).strftime("%Y-%m-%d %H:%M:%S")

st.title("2026年3月末〜5月末 スケジュール回答")

# --- 奏者リスト ---
RAW_MEMBERS = ["三國浩平", "宇佐見優", "岩崎花保", "小野江良太", "近藤圭", "志村樺奈", "篠嶋祐希", "竹之下滉", "長谷川太郎", "西宥介", "西部圭亮", "布施砂丘彦", "前田優紀"]
MEMBERS = sorted(list(set(RAW_MEMBERS)))
OPTIONS = ["選択してください"] + MEMBERS + ["直接入力する..."]

# --- 日付リスト作成 ---
wd_ja = ["月", "火", "水", "木", "金", "土", "日"]
date_objects, date_labels = [], []
curr, end_date = datetime(2026, 3, 30), datetime(2026, 5, 31)
while curr <= end_date:
    if curr.weekday() < 5:
        date_objects.append(curr.date())
        date_labels.append(f"{curr.month}/{curr.day}({wd_ja[curr.weekday()]})")
    curr += timedelta(days=1)
date_map = dict(zip(date_labels, date_objects))

# --- 名前入力セクション ---
selected_option = st.selectbox("あなたの名前を選択してください", OPTIONS)

user_name = ""
if selected_option == "直接入力する...":
    user_name = st.text_input("お名前をフルネームで入力してください（例：山田太郎）")
elif selected_option != "選択してください":
    user_name = selected_option

# --- メイン処理 ---
if user_name:
    # 安全装置
    if 'df_input' not in st.session_state:
        st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    # ユーザーが確定したタイミングで読み込み
    if 'current_user' not in st.session_state or st.session_state.current_user != user_name:
        st.session_state.current_user = user_name
        
        try:
            sheetNM = "収集用"
            df_existing = conn.read(worksheet=sheetNM, ttl=0)
            new_input_df = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])
            
            # DlFlgが 1 以外の有効データを検索
            if not df_existing.empty and "name" in df_existing.columns:
                user_data = df_existing[
                    (df_existing["name"] == user_name) & 
                    (df_existing["DlFlg"].astype(str) != "1")
                ]
                
                if not user_data.empty:
                    for _, row in user_data.iterrows():
                        try:
                            target_date = pd.to_datetime(row['date']).date()
                            for label, d_obj in date_map.items():
                                if d_obj == target_date:
                                    if row['slot'] in new_input_df.columns:
                                        new_input_df.at[label, row['slot']] = True
                                    break
                        except:
                            continue
                    st.toast(f"{user_name} さんの有効な回答を復元しました 🔄")
            
            st.session_state.df_input = new_input_df
        except Exception:
            st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    # --- 入力画面表示 ---
    st.subheader(f"{user_name} さんの入力画面")
    st.markdown("#### **下記のうち、<u>**空いていない**</u>時間帯にチェック✅を入れてください。**", unsafe_allow_html=True)
    st.markdown("#### **入力を終えたら、送信ボタンを押してください。**")

    edited_df = st.data_editor(
        st.session_state.df_input,
        key=f"data_editor_{user_name}",
        use_container_width=True,
        column_config={
            "午前": st.column_config.CheckboxColumn(default=False),
            "午後": st.column_config.CheckboxColumn(default=False),
            "夜間": st.column_config.CheckboxColumn(default=False),
        }
    )

    if st.button("この内容で送信する"):
        timestamp = get_now_jp()
        new_rows = []
        for label, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                if row[slot] == True:
                    new_rows.append({
                        "name": user_name,
                        "date": date_map[label],
                        "slot": slot,
                        "status": "❌",
                        "submitted_at": timestamp,
                        "DlFlg": 0
                    })
        
        try:
            sheetNM = "収集用"
            existing_all = conn.read(worksheet=sheetNM, ttl=0)
            
            if not existing_all.empty:
                # 既存の同一名データに論理削除フラグを立てる
                existing_all.loc[existing_all["name"] == user_name, "DlFlg"] = 1
                new_df = pd.DataFrame(new_rows)
                updated_df = pd.concat([existing_all, new_df], ignore_index=True)
            else:
                updated_df = pd.DataFrame(new_rows)
            
            conn.update(worksheet=sheetNM, data=updated_df)
            st.success(f"回答を更新しました！ (送信時刻: {timestamp})")
            st.balloons()
            st.session_state.df_input = edited_df
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
