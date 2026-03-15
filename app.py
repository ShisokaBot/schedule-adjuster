import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="スケジュール調整", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("4月〜5月 スケジュール回答")

# メンバーリスト
MEMBERS = [f"ミュージシャン{i}" for i in range(1, 16)]

# 日付リスト（4/1〜5/31の平日）
date_list = []
curr = datetime(2026, 3, 30)
while curr <= datetime(2026, 5, 31):
    if curr.weekday() < 5:
        date_list.append(curr.strftime("%m/%d(%a)"))
    curr += timedelta(days=1)

user_name = st.selectbox("あなたの名前を選択してください", ["選択してください"] + MEMBERS)

if user_name != "選択してください":
    st.subheader(f"{user_name} さんの入力画面")
    st.info("❌を入れた箇所が「NG（対応不可）」として保存されます。入力後、一番下の送信ボタンを押してください。")

    # 入力用の表を作成（最初は空）
    df_input = pd.DataFrame("", index=date_list, columns=["午前", "午後", "夜間"])
    
    # 画面上での編集（この時点ではまだどこにも送信されません）
    edited_df = st.data_editor(
        df_input,
        use_container_width=True,
        column_config={
            "午前": st.column_config.SelectboxColumn(options=["", "❌"]),
            "午後": st.column_config.SelectboxColumn(options=["", "❌"]),
            "夜間": st.column_config.SelectboxColumn(options=["", "❌"]),
        }
    )

    # --- ここが「送信」ボタン。押すまで何もしない ---
    if st.button("この内容で送信する"):
        # ❌がついたデータだけをリストにまとめる
        new_rows = []
        for date, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                if row[slot] == "❌":
                    new_rows.append({
                        "name": user_name,
                        "date": date,
                        "slot": slot,
                        "status": "❌"
                    })
        
        if new_rows:
            try:
                sheetNM = "奏者予定表"
                # 現在のデータを読み込む
                existing_data = conn.read(worksheet=sheetNM)
                
                # 今回の入力データをDataFrameに変換
                new_df = pd.DataFrame(new_rows)
                
                # 同じ名前の古いデータがあれば消して、新しいのをくっつける（上書き処理）
                if not existing_data.empty and "name" in existing_data.columns:
                    clean_existing = existing_data[existing_data["name"] != user_name]
                    updated_df = pd.concat([clean_existing, new_df], ignore_index=True)
                else:
                    updated_df = new_df
                
                # スプレッドシートに一括保存
                conn.update(worksheet=sheetNM, data=updated_df)
                
                st.success("全ての回答を送信しました！ありがとうございます。")
                st.balloons()
            except Exception as e:
                st.error(f"送信エラーが発生しました: {e}")
        else:
            st.warning("❌が一つも入力されていません。")
