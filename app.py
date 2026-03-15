import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("2026年3月〜5月 スケジュール回答")

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
    # 名前が変わった瞬間にデータを読み込むロジック
    if 'current_user' not in st.session_state or st.session_state.current_user != user_name:
        st.session_state.current_user = user_name
        
        # 1. スプレッドシートから最新データを読み込む
        try:
            sheetNM = "収集用シート"
            df_existing = conn.read(worksheet=sheetNM)
            
            # 初期状態（すべてFalse）のデータフレーム作成
            new_input_df = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])
            
            if not df_existing.empty and "name" in df_existing.columns:
                # 選択したユーザーのデータだけ抽出
                user_data = df_existing[df_existing["name"] == user_name]
                
                # 既存の❌をチェックボックスに反映
                for _, row in user_data.iterrows():
                    # スプレッドシートの日付（date型または文字列）をラベル形式に変換して照合
                    d_obj = pd.to_datetime(row['date']).date()
                    # 逆引きしてラベルを取得
                    matching_labels = [l for l, d in date_map.items() if d == d_obj]
                    if matching_labels:
                        label = matching_labels[0]
                        if row['slot'] in new_input_df.columns:
                            new_input_df.at[label, row['slot']] = True
            
            st.session_state.df_input = new_input_df
            st.toast(f"{user_name} さんの前回の回答を読み込みました")
            
        except Exception as e:
            # 初回などデータがない場合は空の表を表示
            st.session_state.df_input = pd.DataFrame(False, index=date_labels, columns=["午前", "午後", "夜間"])

    
    # 説明文（改行・太字・アンダーバー）
    st.subheader(f"{user_name} さんの入力画面")
    st.markdown("下記のうち、<u>**空いていない**</u>時間帯にチェック✅を入れてください。", unsafe_allow_html=True)
    st.markdown("入力を終えたら、送信ボタンを押してください。")
    
    # 編集可能な表
    edited_df = st.data_editor(
        st.session_state.df_input,
        key="data_editor",
        use_container_width=True,
        column_config={
            "午前": st.column_config.CheckboxColumn(default=False),
            "午後": st.column_config.CheckboxColumn(default=False),
            "夜間": st.column_config.CheckboxColumn(default=False),
        }
    )

    # 送信ボタン
    if st.button("この内容で送信する"):
        new_rows = []
        for label, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                if row[slot] == True:
                    new_rows.append({
                        "name": user_name,
                        "date": date_map[label],
                        "slot": slot,
                        "status": "❌"
                    })
        
        try:
            sheetNM = "収集用シート"
            existing_all = conn.read(worksheet=sheetNM)
            new_df = pd.DataFrame(new_rows)
            
            # 上書きロジック：自分以外のデータ ＋ 今回の新しいデータ
            if not existing_all.empty and "name" in existing_all.columns:
                other_users_data = existing_all[existing_all["name"] != user_name]
                updated_df = pd.concat([other_users_data, new_df], ignore_index=True)
            else:
                updated_df = new_df
            
            conn.update(worksheet=sheetNM, data=updated_df)
            st.success("最新の回答として保存しました！")
            st.balloons()
            # 状態を更新
            st.session_state.df_input = edited_df
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
