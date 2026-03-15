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
RAW_MEMBERS = ["伊藤友馬", "宇佐見優", "岩崎花保", "小野江良太", "近藤圭", "志村樺奈", "篠嶋祐希", "竹之下滉", "長谷川太郎", "西宥介", "西部圭亮", "舟久保優貴", "布施砂丘彦", "前田優紀","三國浩平"]
MEMBERS = sorted(list(set(RAW_MEMBERS)))

# --- 日付リスト ---
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
    # 安全装置
    if 'df_input' not in st.session_state:
        st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    if 'current_user' not in st.session_state or st.session_state.current_user != user_name:
        st.session_state.current_user = user_name
        
        try:
            sheetNM = "収集用"
            df_existing = conn.read(worksheet=sheetNM, ttl=0)
            new_input_df = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])
            
            if not df_existing.empty and "name" in df_existing.columns:
                # 【論理削除対応】DlFlgが 1 以外のデータのみを「有効な回答」として読み込む
                # 文字列か数値か不明なため、1でないことを判定
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
        except Exception as e:
            st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    # 入力画面
    st.subheader(f"{user_name} さんの入力画面")
    st.markdown("下記のうち、<u>**空いていない**</u>時間帯にチェック✅を入れてください。", unsafe_allow_html=True)

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
        
        # 新しく登録するデータ（DlFlg=0）
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
                        "DlFlg": 0  # 有効データ
                    })
        
        try:
            sheetNM = "収集用"
            existing_all = conn.read(worksheet=sheetNM, ttl=0)
            
            if not existing_all.empty:
                # 【論理削除ロジック】自分の既存データのDlFlgをすべて 1 に更新
                existing_all.loc[existing_all["name"] == user_name, "DlFlg"] = 1
                
                # 更新された既存データ ＋ 今回の新規データ
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
