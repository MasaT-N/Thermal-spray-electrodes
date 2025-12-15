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


def fetch_defective_electrodes(limit: int | None = 100) -> pl.DataFrame:
    """
    defective_electrodesテーブルから全データを取得する
    """
    query = """
    SELECT
        de.id
        , de.item_code AS "品目"
        , de.serial_num AS "シリアル"
        , de.defect_date AS "不具合発生日"
        , de.defect_status AS "不具合状況"
        , de.defect_description AS "不具合内容"
        , de.linde_remarks AS "リンデ備考"
        , CASE 
            WHEN de.updated_by != '' THEN ur_update.user_name
            ELSE ur_create.user_name
        END AS "登録者"
        , CASE 
            WHEN de.updated_at > de.created_at THEN de.updated_at 
            ELSE de.created_at 
        END AS "最終更新日時" -- UTC
    FROM
        public.defective_electrodes de
    LEFT JOIN public.user_roles ur_create ON de.created_by = ur_create.email
    LEFT JOIN public.user_roles ur_update ON de.updated_by = ur_update.email
    ORDER BY
        de.defect_date DESC,
        COALESCE(de.updated_at, de.created_at) DESC
    """
    query += f" LIMIT {limit}" if limit is not None else ""
    df = supabase_read_sql(query)

    # データフレームが空の場合は、後続の処理を行わずにそのまま返す
    if df.is_empty():
        return df

    # 最終更新日時列のタイムゾーン変換とフォーマットを行う式を定義
    # データベースから取得した時点ではUTCのタイムゾーン情報を持っている想定
    datetime_format_expr = (
        pl.col("最終更新日時")
        .dt.convert_time_zone("Asia/Tokyo")  # 日本時間に変換
        .dt.strftime("%Y-%m-%d %H:%M:%S")  # 文字列にフォーマット
    )

    # もし最終更新日時列が文字列型(String)なら、先にDatetime型に変換する
    if df.schema["最終更新日時"] == pl.String:
        datetime_format_expr = (
            pl.col("最終更新日時")
            .str.to_datetime()
            .pipe(lambda series: datetime_format_expr)
        )

    # 不具合発生日列のフォーマットを行う式を定義
    defect_date_format_expr = pl.col("不具合発生日").dt.strftime("%Y-%m-%d")

    # もし不具合発生日列が文字列型(String)なら、先にDatetime型に変換する
    # `strptime` を使用して、日付のみの文字列 "YYYY-MM-DD" をパースする
    if df.schema["不具合発生日"] == pl.String:
        defect_date_format_expr = (
            pl.col("不具合発生日")
            .str.strptime(pl.Date, "%Y-%m-%d")
            .dt.strftime("%Y-%m-%d")
        )

    df = df.with_columns(
        defect_date_format_expr.alias("不具合発生日"),  # 定義した式を適用
        datetime_format_expr.alias("最終更新日時"),  # 定義した式を適用
    )
    return df


def main():
    st.set_page_config(
        page_title="不具合電極登録",
        page_icon="⚠️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("⚠️ 不具合電極登録")
    st.subheader("電極の不具合情報を登録します。")

    # --- 認証と権限チェック ---
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return

    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("ユーザー情報が取得できませんでした。再度サインインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return

    user_roles_df = fetch_user_roles(email=user_email)
    if user_roles_df.is_empty() or not user_roles_df["can_read"][0]:
        st.warning("このページにアクセスする権限がありません。読み取り権限が必要です。")
        return

    user_name = user_roles_df["user_name"][0]
    can_write = user_roles_df["can_write"][0]

    st.info(f"登録者: {user_name}")
    st.divider()

    # 権限に応じてタブを制御
    if can_write:
        tab1, tab2 = st.tabs(["✍️ 不具合登録", "📋 履歴の表示・修正"])
    else:
        st.info("書き込み権限がないため、履歴の表示のみ可能です。")
        # タブを一つだけ作成し、tab2に割り当てる
        tab2 = st.tabs(["📋 履歴の表示"])[0]
        tab1 = None  # tab1は使わない
    # --- Tab1: 不具合登録 ---
    with tab1:
        st.subheader("新規登録フォーム")
        # 品目リストを取得
        existing_items = fetch_unique_item_codes()

        # 品目入力（既存リストからの選択と新規入力）
        item_selection_method = st.radio(
            "品目選択方法",
            ["既存の品目から選択", "新しい品目を入力"],
            horizontal=True,
            key="new_item_method",
        )

        with st.form(key="defect_form", clear_on_submit=True):
            st.write("不具合情報を入力してください。")

            if item_selection_method == "既存の品目から選択":
                item_code = st.selectbox(
                    "品目",
                    options=existing_items,
                    index=None,
                    placeholder="品目を選択してください",
                )
            else:
                item_code = st.text_input("新しい品目名")

            serial_num = st.number_input(
                "シリアル", min_value=1, step=1, value=None, format="%d"
            )
            defect_date = st.date_input("不具合発生日", value=datetime.now())
            defect_status = st.radio("不具合状況", ["判定中", "廃棄"], horizontal=True)
            defect_description = st.text_area("不具合内容")
            linde_remarks = st.text_area(
                "リンデ備考", help="この項目は主に協力企業（リンデ）が使用します。"
            )

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
                            "created_by": user_email,
                        },
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
        st.subheader("登録履歴の表示・修正")

        # --- フィルターと表示設定 ---
        # データ取得より前にウィジェットを定義する必要がある
        with st.expander("フィルターと表示設定", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                show_all = st.toggle(
                    "全件表示（デフォルトは最新100件）",
                    value=False,
                    key="show_all_toggle",
                )

            # 品目以外のフィルターを先に定義
            col1_placeholder, col2, col3 = st.columns(3)
            with col2:
                filter_serial_num = st.number_input(
                    "シリアルで絞り込み",
                    min_value=1,
                    max_value=9999,
                    step=1,
                    value=None,
                    format="%d",
                )
            with col3:
                filter_defect_date_from = st.date_input(
                    "不具合発生日 (From)", value=None
                )
                filter_defect_date_to = st.date_input("不具合発生日 (To)", value=None)

        # データ取得
        limit = None if show_all else 100
        defects_df = fetch_defective_electrodes(limit=limit)

        if defects_df.is_empty():
            st.info("登録されている不具合情報はありません。")
        else:
            # --- selectbox用の品目リストを作成 ---
            # "すべて" を先頭に追加
            item_code_options = ["すべて"] + sorted(
                defects_df["品目"].unique().to_list()
            )
            # プレースホルダーにselectboxを配置
            with col1_placeholder:
                filter_item_code = st.selectbox(
                    "品目で絞り込み", options=item_code_options, index=0
                )

            # --- フィルター適用 ---
            filtered_df = defects_df
            if filter_item_code and filter_item_code != "すべて":
                filtered_df = filtered_df.filter(pl.col("品目") == filter_item_code)
            if filter_serial_num:
                filtered_df = filtered_df.filter(
                    pl.col("シリアル").cast(pl.Int64) == filter_serial_num
                )
            if filter_defect_date_from:
                filtered_df = filtered_df.filter(
                    pl.col("不具合発生日").str.to_date("%Y-%m-%d")
                    >= filter_defect_date_from
                )
            if filter_defect_date_to:
                filtered_df = filtered_df.filter(
                    pl.col("不具合発生日").str.to_date("%Y-%m-%d")
                    <= filter_defect_date_to
                )

            # データフレーム表示
            if can_write:
                st.info("修正したい行を選択してください。")
            else:
                st.info(f"{len(filtered_df)} 件のデータが表示されています。")

            # on_select="rerun"で、行選択時にアプリを再実行させる
            # selection_mode="single-row"で単一行選択を有効にする
            st.dataframe(
                filtered_df,
                key="defects_df",
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
            )

            # 選択された行の情報を取得
            selection = st.session_state.get("defects_df")

            # 書き込み権限がある場合のみ、編集・削除フォームを表示
            if can_write and selection and selection["selection"]["rows"]:
                selected_row_index = selection["selection"]["rows"][0]
                selected_record = filtered_df.row(selected_row_index, named=True)

                st.divider()
                st.subheader(f"ID: {selected_record['id']} のデータを修正")

                with st.form(key="update_defect_form"):
                    updated_item_code = st.text_input(
                        "品目", value=selected_record["品目"]
                    )
                    updated_serial_num = st.text_input(
                        "シリアル", value=selected_record["シリアル"]
                    )

                    # 日付の型変換
                    current_defect_date = selected_record["不具合発生日"]
                    if isinstance(current_defect_date, str):
                        current_defect_date = datetime.strptime(
                            current_defect_date, "%Y-%m-%d"
                        ).date()

                    updated_defect_date = st.date_input(
                        "不具合発生日", value=current_defect_date
                    )

                    status_options = ["判定中", "廃棄"]
                    current_status_index = status_options.index(
                        selected_record["不具合状況"]
                    )
                    updated_defect_status = st.radio(
                        "不具合状況",
                        options=status_options,
                        index=current_status_index,
                        horizontal=True,
                    )

                    updated_defect_description = st.text_area(
                        "不具合内容", value=selected_record["不具合内容"]
                    )
                    updated_linde_remarks = st.text_area(
                        "リンデ備考", value=selected_record.get("リンデ備考", "")
                    )

                    # 更新ボタンと削除ボタンを横に並べる
                    col1, col2, _ = st.columns([1, 1, 5])
                    with col1:
                        update_button = st.form_submit_button(
                            "更新する", type="primary"
                        )
                    with col2:
                        delete_button = st.form_submit_button(
                            "削除する", type="secondary"
                        )

                # --- 更新処理 ---
                if update_button:
                    if not all(
                        [
                            updated_item_code,
                            updated_serial_num,
                            updated_defect_description,
                        ]
                    ):
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
                                    linde_remarks = :linde_remarks,
                                    updated_at = NOW(),
                                    updated_by = :updated_by
                                WHERE id = :id
                            """,
                            "params": {
                                "id": selected_record["id"],
                                "item_code": updated_item_code.strip(),
                                "serial_num": updated_serial_num.strip(),
                                "defect_date": updated_defect_date,
                                "defect_status": updated_defect_status,
                                "defect_description": updated_defect_description.strip(),
                                "linde_remarks": updated_linde_remarks.strip(),
                                "updated_by": user_email,
                            },
                        }
                        if supabase_execute_sql([update_query]):
                            st.success(
                                f"ID: {selected_record['id']} のデータを更新しました。"
                            )
                            time.sleep(1)
                            st.rerun()  # 画面を再読み込みして変更を反映
                        else:
                            st.error("データの更新に失敗しました。")

                # --- 削除処理 ---
                if delete_button:
                    delete_query = {
                        "sql": "DELETE FROM public.defective_electrodes WHERE id = :id",
                        "params": {"id": selected_record["id"]},
                    }
                    if supabase_execute_sql([delete_query]):
                        st.success(
                            f"ID: {selected_record['id']} のデータを削除しました。"
                        )
                        time.sleep(1)
                        st.rerun()  # 画面を再読み込みして変更を反映
                    else:
                        st.error("データの削除に失敗しました。")


if __name__ == "__main__":
    main()
