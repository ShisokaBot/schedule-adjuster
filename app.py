import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz  # 日本時間設定用
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 日本時間の取得関数
def get_now_jp():
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    return datetime.now(tokyo_tz).strftime("%Y-%m-%d %H:%M:%S")

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

# --- 名前選択 ---
user_name = st.selectbox("あなたの名前を選択してください", ["選択してください"] + MEMBERS)

if user_name != "選択してください":
    # 【追加：安全装置】まだセッションにデータがない場合は、即座に空の表を作る
    if 'df_input' not in st.session_state:
        st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    # ユーザーが切り替わった時の処理
    if 'current_user' not in st.session_state or st.session_state.current_user != user_name:
        st.session_state.current_user = user_name
        
        try:
            sheetNM = "収集用"
            df_existing = conn.read(worksheet=sheetNM, ttl=0)
            # 読み込み用の土台（一旦リセット）
            new_input_df = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])
            
            if not df_existing.empty and "name" in df_existing.columns:
                user_data = df_existing[df_existing["name"] == user_name]
                
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
                    
                    st.session_state.df_input = new_input_df
                    st.toast(f"{user_name} さんの前回の回答を復元しました 🔄")
                else:
                    # 未回答者の場合は空の表をセット
                    st.session_state.df_input = new_input_df
            
        except Exception as e:
            # エラー時も真っ白な表を維持
            st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    # 説明文
    st.subheader(f"{user_name} さんの入力画面")
    st.markdown("下記のうち、<u>**空いていない**</u>時間帯にチェック✅を入れてください。", unsafe_allow_html=True)
    st.markdown("入力を終えたら、送信ボタンを押してください。")

    # 編集可能な表
    # keyにuser_nameを含めることで、ユーザー切り替え時に表を強制リセット（再描画）する
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

    # --- 送信ボタン ---
    if st.button("この内容で送信する"):
        timestamp = get_now_jp() # 日本時間を取得
        
        new_rows = []
        for label, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                if row[slot] == True:
                    new_rows.append({
                        "name": user_name,
                        "date": date_map[label],
                        "slot": slot,
                        "status": "❌",
                        "submitted_at": timestamp
                    })
        
        try:
            sheetNM = "収集用"
            # 送信前にも最新を読み込んで他の人のデータを保持する
            existing_all = conn.read(worksheet=sheetNM, ttl=0)
            new_df = pd.DataFrame(new_rows)
            
            if not existing_all.empty and "name" in existing_all.columns:
                other_users_data = existing_all[existing_all["name"] != user_name]
                updated_df = pd.concat([other_users_data, new_df], ignore_index=True)
            else:
                updated_df = new_df
            
            conn.update(worksheet=sheetNM, data=updated_df)
            st.success(f"最新の回答を送信しました！ ({timestamp})")
            st.balloons()
            # 送信後の状態をセッションに反映
            st.session_state.df_input = edited_df
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
