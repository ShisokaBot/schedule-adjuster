import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("3月末〜5月末 スケジュール回答")

# メンバーリスト
MEMBERS = [f"奏者{i}" for i in range(1, 16)]

# --- 日付リストの作成 ---
# 曜日を日本語に変換する辞書
wd_ja = ["月", "火", "水", "木", "金", "土", "日"]

date_objects = []  # 内部計算用（日付型）
date_labels = []   # 画面表示用（文字列型）

curr = datetime(2026, 3, 30)
end_date = datetime(2026, 5, 31)

while curr <= end_date:
    if curr.weekday() < 5:  # 平日のみ
        date_objects.append(curr.date()) # date型で保存
        # 「3/30(月)」の形式を作成
        label = f"{curr.month}/{curr.day}({wd_ja[curr.weekday()]})"
        date_labels.append(label)
    curr += timedelta(days=1)

# ラベルと日付オブジェクトを紐付けた辞書（送信時に使用）
date_map = dict(zip(date_labels, date_objects))

user_name = st.selectbox("あなたの名前を選択してください", ["選択してください"] + MEMBERS)

if user_name != "選択してください":
    st.subheader(f"{user_name} さんの入力画面")
    
    # 入力用の表を作成（インデックスに日本語表記を使用）
    df_input = pd.DataFrame("", index=date_labels, columns=["午前", "午後", "夜間"])
    
    # 画面上での編集
    edited_df = st.data_editor(
        df_input,
        use_container_width=True,
        column_config={
            "午前": st.column_config.SelectboxColumn(options=["", "❌"]),
            "午後": st.column_config.SelectboxColumn(options=["", "❌"]),
            "夜間": st.column_config.SelectboxColumn(options=["", "❌"]),
        }
    )

    if st.button("この内容で送信する"):
        new_rows = []
        for label, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                if row[slot] == "❌":
                    new_rows.append({
                        "name": user_name,
                        "date": date_map[label],  # ここで「日付型」に変換して送信
                        "slot": slot,
                        "status": "❌"
                    })
        
        if new_rows:
            try:
                sheetNM = "奏者予定表"
                existing_data = conn.read(worksheet=sheetNM)
                new_df = pd.DataFrame(new_rows)
                
                # 日付型として比較・結合を行うために型を合わせる（念のため）
                if not existing_data.empty and "name" in existing_data.columns:
                    existing_data['date'] = pd.to_datetime(existing_data['date']).dt.date
                    clean_existing = existing_data[existing_data["name"] != user_name]
                    updated_df = pd.concat([clean_existing, new_df], ignore_index=True)
                else:
                    updated_df = new_df
                
                # スプレッドシートを更新
                conn.update(worksheet=sheetNM, data=updated_df)
                
                st.success("全ての回答を送信しました！")
                st.balloons()
            except Exception as e:
                st.error(f"送信エラーが発生しました: {e}")
        else:
            st.warning("❌が一つも入力されていません。")
