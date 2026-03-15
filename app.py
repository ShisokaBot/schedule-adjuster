import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- ページ設定 ---
st.set_page_config(page_title="スケジュール調整", layout="wide")

# --- スプレッドシート接続 ---
# Secretsに設定した情報を使って接続します
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("4月〜5月 スケジュール回答")
st.write("※入力した内容は他のメンバーからは見えません。")

# メンバーリスト（必要に応じて書き換えてください）
MEMBERS = [f"奏者{i}" for i in range(1, 16)]

# 4月〜5月の平日リスト作成
date_list = []
curr = datetime(2026, 4, 1)
while curr <= datetime(2026, 5, 31):
    if curr.weekday() < 5:  # 月〜金
        date_list.append(curr.strftime("%m/%d(%a)"))
    curr += timedelta(days=1)

# --- 入力セクション ---
user_name = st.selectbox("あなたの名前を選択してください", ["選択してください"] + MEMBERS)

if user_name != "選択してください":
    st.subheader(f"{user_name} さんの入力画面")
    st.info("❌：予定あり（対応不可） / 無印：対応可能")

    # 入力用の空の表を作成
    df = pd.DataFrame("", index=date_list, columns=["午前", "午後", "夜間"])
    
    # 編集可能な表を表示
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        column_config={
            "午前": st.column_config.SelectboxColumn(options=["", "❌"]),
            "午後": st.column_config.SelectboxColumn(options=["", "❌"]),
            "夜間": st.column_config.SelectboxColumn(options=["", "❌"]),
        }
    )

    # --- 送信ボタン ---
    if st.button("送信（スプレッドシートに保存）する"):
        # ❌がついたデータだけを抜き出してリストにする
        new_data = []
        for date, row in edited_df.iterrows():
            for slot in ["午前", "午後", "夜間"]:
                if row[slot] == "❌":
                    new_data.append({
                        "name": user_name,
                        "date": date,
                        "slot": slot,
                        "status": "❌"
                    })
        
        if new_data:
            try:
                # 現在のスプレッドシートの内容を読み込む
                # ※シート名が "奏者予定表" であることを確認してください
                sheetNM = "予定表"
                existing_data = conn.read(worksheet=sheetNM)
                
                # 新しいデータを結合
                updated_df = pd.concat([existing_data, pd.DataFrame(new_data)], ignore_index=True)
                
                # スプレッドシートを更新
                conn.update(worksheet=sheetNM, data=updated_df)
                
                st.success(f"回答を保存しました！スプレッドシートを確認してください。")
                st.balloons() # 成功のお祝い
            except Exception as e:
                st.error(f"保存中にエラーが発生しました: {e}")
        else:
            st.warning("❌が一つも入力されていません。")
