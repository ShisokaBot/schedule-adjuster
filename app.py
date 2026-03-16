import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="2026年スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. データ読み込みのキャッシュ化 (API節約) ---
@st.cache_data(ttl=300)
def fetch_existing_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=300)

# --- 2. クリック2回問題を解決するコールバック関数 ---
def on_editor_change():
    # エディタの現在の状態を即座に session_state に反映させる
    key = f"data_editor_{st.session_state.current_user}"
    if key in st.session_state:
        # data_editor の中身（edited_rowsなど）から DataFrame を更新
        # Streamlitの内部挙動に合わせ、直接代入ではなくステートを維持
        pass 

def get_now_jp():
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    return datetime.now(tokyo_tz).strftime("%Y-%m-%d %H:%M:%S")

st.title("2026年3月末〜5月末 スケジュール回答")

# 奏者リスト
MEMBERS = ["岩崎花保", "宇佐見優", "小野江良太", "近藤圭", "篠嶋祐希", "竹之下滉", "西宥介", "西部圭亮", "布施砂丘彦", "前田優紀", "三國浩平", "長谷川太郎"]
OPTIONS = ["選択してください"] + MEMBERS + ["直接入力する..."]

# --- 日付リスト作成 (土日除外) ---
wd_ja = ["月", "火", "水", "木", "金", "土", "日"]
date_objects, date_labels = [], []
curr, end_date = datetime(2026, 3, 30), datetime(2026, 5, 31)
while curr <= end_date:
    if curr.weekday() < 5: # 平日のみ
        date_objects.append(curr.date())
        date_labels.append(f"{curr.month}/{curr.day}({wd_ja[curr.weekday()]})")
    curr += timedelta(days=1)
date_map = dict(zip(date_labels, date_objects))

# 名前入力
selected_option = st.selectbox("あなたの名前を選択してください", OPTIONS)
user_name = ""
if selected_option == "直接入力する...":
    user_name = st.text_input("お名前をフルネームで入力してください")
elif selected_option != "選択してください":
    user_name = selected_option

# --- メイン処理 ---
if user_name:
    # ユーザー切り替え時の初期化
    if 'current_user' not in st.session_state or st.session_state.current_user != user_name:
        st.session_state.current_user = user_name
        
        try:
            sheetNM = "収集用"
            df_existing = fetch_existing_data(sheetNM)
            new_input_df = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])
            
            if not df_existing.empty and "name" in df_existing.columns:
                user_data = df_existing[(df_existing["name"] == user_name) & (df_existing["DlFlg"].astype(str) != "1")]
                if not user_data.empty:
                    for _, row in user_data.iterrows():
                        try:
                            target_date = pd.to_datetime(row['date']).date()
                            for label, d_obj in date_map.items():
                                if d_obj == target_date:
                                    if row['slot'] in new_input_df.columns:
                                        new_input_df.at[label, row['slot']] = True
                                    break
                        except: continue
                    st.toast(f"{user_name} さんの回答を復元しました")
            st.session_state.df_input = new_input_df
        except Exception:
            st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    st.subheader(f"{user_name} さんの入力画面")
    st.info("※空いていない（NGな）時間帯にチェックを入れてください。")
    
    # 1クリックで反映させるための設定
    # keyを指定し、前回実行時の結果を反映させる
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
    
    # ここで常に最新の状態を保持
    st.session_state.df_input = edited_df

    if st.button("この内容で送信する", type="primary"):
        if not user_name:
            st.error("名前が正しく入力されていません。")
        else:
            with st.spinner("スプレッドシートを更新中..."):
                timestamp = get_now_jp()
                new_rows = []
                # 編集後のデータから「True(NG)」の行だけを抽出
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
                    # 送信時は最新が必要
                    existing_all = conn.read(worksheet=sheetNM, ttl=0)
                    
                    if not existing_all.empty:
                        # 既存のその人のデータに論理削除フラグ
                        existing_all.loc[existing_all["name"] == user_name, "DlFlg"] = 1
                        updated_df = pd.concat([existing_all, pd.DataFrame(new_rows)], ignore_index=True)
                    else:
                        updated_df = pd.DataFrame(new_rows)
                    
                    # 更新実行
                    conn.update(worksheet=sheetNM, data=updated_df)
                    
                    # キャッシュクリア（次回、他人が開いた時に最新が出るように）
                    st.cache_data.clear()
                    
                    st.success(f"送信完了しました！ ({timestamp})")
                    st.balloons()
                except Exception as e:
                    st.error(f"送信エラーが発生しました。時間を置いて再度お試しください。: {e}")
