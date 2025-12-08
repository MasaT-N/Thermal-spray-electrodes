import streamlit as st
import time
import polars as pl
from util import fetch_user_roles, supabase_read_sql, supabase_execute_sql
from datetime import datetime

def fetch_unique_item_codes() -> list[str]:
    """
    electrode_statusテーブルからユニークな品目コードのリストを取得する
    """
    query = "SELECT DISTINCT item_code FROM public.electrode_status ORDER BY item_code"
    df = supabase_read_sql(query)
    if df.is_empty():
        return []
    return df["item_code"].to_list()

def fetch_defective_electrodes() -> pl.DataFrame:
    """
    defective_electrodesテーブルから全データを取得する
    """
    query = """
    SELECT
        de.id,
        de.item_code AS "品目",
        de.serial_num AS "シリアル",
        de.defect_date AS "不具合発生日時",
        de.defect_status AS "不具合状況",
        de.defect_description AS "不具合内容",
        de.linde_remarks AS "リンデ備考",
        de.created_at AS "登録日時", -- UTC
        COALESCE(ur.user_name, de.created_by) AS "登録者"
    FROM
        public.defective_electrodes de
    LEFT JOIN public.user_roles ur ON de.created_by = ur.email
    ORDER BY de.created_at DESC
    """
    df = supabase_read_sql(query)

    df = df.with_columns(
        pl.col("不具合発生日時").dt.strftime("%Y-%m-%d"),
        pl.col("登録日時")
        .dt.replace_time_zone("UTC")          # 元のデータがUTCであることを指定
        .dt.convert_time_zone("Asia/Tokyo")   # 日本時間に変換
        .dt.replace_time_zone(None)           # タイムゾーン情報を削除
        .dt.strftime("%Y-%m-%d %H:%M:%S"),
    )   
    return df

def main():
    st.set_page_config(
        page_title="不具合電極登録",
        page_icon="⚠️",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    st.title("⚠️ 不具合電極登録")
    st.subheader("電極の不具合情報を登録します。")

    # --- 認証と権限チェック ---
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return

    user_email = st.session_state.get('user_email')
    if not user_email:
        st.error("ユーザー情報が取得できませんでした。再度サインインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return

    user_roles_df = fetch_user_roles(email=user_email)
    if user_roles_df.is_empty() or not user_roles_df["can_write"][0]:
        st.warning("このページにアクセスする権限がありません。書き込み権限が必要です。")
        return
    
    user_name = user_roles_df["user_name"][0]
    st.info(f"登録者: {user_name}")
    st.divider()

    tab1, tab2 = st.tabs(["✍️ 不具合登録", "📋 履歴の表示・修正"])

    # --- Tab1: 不具合登録 ---
    with tab1:
        st.subheader("新規登録フォーム")
        # 品目リストを取得
        existing_items = fetch_unique_item_codes()
        
        # 品目入力（既存リストからの選択と新規入力）
        item_selection_method = st.radio("品目選択方法", ["既存の品目から選択", "新しい品目を入力"], horizontal=True, key="new_item_method")

        with st.form(key="defect_form", clear_on_submit=True):
            st.write("不具合情報を入力してください。")

            if item_selection_method == "既存の品目から選択":
                item_code = st.selectbox("品目", options=existing_items, index=None, placeholder="品目を選択してください")
            else:
                item_code = st.text_input("新しい品目名")

            serial_num = st.number_input("シリアル", min_value=1, step=1, value=None, format="%d")
            defect_date = st.date_input("不具合発生日時", value=datetime.now())
            defect_status = st.radio("不具合状況", ["判定中", "廃棄"], horizontal=True)
            defect_description = st.text_area("不具合内容")
            linde_remarks = st.text_area("リンデ備考", help="この項目は主に協力企業（リンデ）が使用します。")
            
            submit_button = st.form_submit_button("登録する", type="primary")
            
        # --- フォーム送信処理 ---
        if submit_button:
            # バリデーション
            if not all([item_code, serial_num, defect_description]):
                st.error("すべての項目を入力してください。")
            else:
                try:
                    # 登録クエリの作成
                    query = {
                        "sql": """
                            INSERT INTO public.defective_electrodes 
                            (item_code, serial_num, defect_date, defect_status, defect_description, linde_remarks, created_by)
                            VALUES (:item_code, :serial_num, :defect_date, :defect_status, :defect_description, :linde_remarks, :created_by)
                        """,
                        "params": {
                            "item_code": item_code.strip(),
                            "serial_num": str(serial_num),
                            "defect_date": defect_date,
                            "defect_status": defect_status,
                            "defect_description": defect_description.strip(),
                            "linde_remarks": linde_remarks.strip(),
                            "created_by": user_name
                        }
                    }

                    # SQL実行
                    if supabase_execute_sql([query]):
                        st.success("不具合情報を正常に登録しました。")
                    else:
                        st.error("データベースへの登録中にエラーが発生しました。")

                except Exception as e:
                    st.error(f"登録処理中に予期せぬエラーが発生しました: {e}")

    # --- Tab2: 履歴の表示・修正 ---
    with tab2:
        st.subheader("登録履歴")
        
        # データ取得
        defects_df = fetch_defective_electrodes()

        if defects_df.is_empty():
            st.info("登録されている不具合情報はありません。")
        else:
            # データフレーム表示
            st.info("修正したい行を選択してください。")
            # on_select="rerun"で、行選択時にアプリを再実行させる
            # selection_mode="single-row"で単一行選択を有効にする
            st.dataframe(defects_df, key="defects_df", on_select="rerun", selection_mode="single-row", hide_index=True)

            # 選択された行の情報を取得
            selection = st.session_state.get("defects_df")
            if selection and selection["selection"]["rows"]:
                selected_row_index = selection["selection"]["rows"][0]
                selected_record = defects_df.row(selected_row_index, named=True)

                st.divider()
                st.subheader(f"ID: {selected_record['id']} のデータを修正")

                with st.form(key="update_defect_form"):
                    updated_item_code = st.text_input("品目", value=selected_record["品目"])
                    updated_serial_num = st.text_input("シリアル", value=selected_record["シリアル"])
                    
                    # 日付の型変換
                    current_defect_date = selected_record["不具合発生日時"]
                    if isinstance(current_defect_date, str):
                        current_defect_date = datetime.strptime(current_defect_date, "%Y-%m-%d").date()

                    updated_defect_date = st.date_input("不具合発生日時", value=current_defect_date)
                    
                    status_options = ["判定中", "廃棄"]
                    current_status_index = status_options.index(selected_record["不具合状況"])
                    updated_defect_status = st.radio("不具合状況", options=status_options, index=current_status_index, horizontal=True)
                    
                    updated_defect_description = st.text_area("不具合内容", value=selected_record["不具合内容"])
                    updated_linde_remarks = st.text_area("リンデ備考", value=selected_record.get("リンデ備考", ""))

                    # 更新ボタンと削除ボタンを横に並べる
                    col1, col2, _ = st.columns([1, 1, 5])
                    with col1:
                        update_button = st.form_submit_button("更新する", type="primary")
                    with col2:
                        delete_button = st.form_submit_button("削除する", type="secondary")

                # --- 更新処理 ---
                if update_button:
                    if not all([updated_item_code, updated_serial_num, updated_defect_description]):
                        st.error("品目、シリアル、不具合内容は必須です。")
                    else:
                        update_query = {
                            "sql": """
                                UPDATE public.defective_electrodes
                                SET item_code = :item_code, 
                                    serial_num = :serial_num, 
                                    defect_date = :defect_date, 
                                    defect_status = :defect_status, 
                                    defect_description = :defect_description,
                                    linde_remarks = :linde_remarks
                                WHERE id = :id
                            """,
                            "params": {
                                "id": selected_record["id"],
                                "item_code": updated_item_code.strip(),
                                "serial_num": updated_serial_num.strip(),
                                "defect_date": updated_defect_date,
                                "defect_status": updated_defect_status,
                                "defect_description": updated_defect_description.strip(),
                                "linde_remarks": updated_linde_remarks.strip()
                            }
                        }
                        if supabase_execute_sql([update_query]):
                            st.success(f"ID: {selected_record['id']} のデータを更新しました。")
                            time.sleep(1)
                            st.rerun() # 画面を再読み込みして変更を反映
                        else:
                            st.error("データの更新に失敗しました。")

                # --- 削除処理 ---
                if delete_button:
                    delete_query = {
                        "sql": "DELETE FROM public.defective_electrodes WHERE id = :id",
                        "params": {"id": selected_record["id"]}
                    }
                    if supabase_execute_sql([delete_query]):
                        st.success(f"ID: {selected_record['id']} のデータを削除しました。")
                        time.sleep(1)
                        st.rerun() # 画面を再読み込みして変更を反映
                    else:
                        st.error("データの削除に失敗しました。")


if __name__ == "__main__":
    main()