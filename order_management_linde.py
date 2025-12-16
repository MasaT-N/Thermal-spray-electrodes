import streamlit as st
import time
import polars as pl
import datetime
from util import supabase_read_sql, supabase_execute_sql, fetch_user_roles

item_codes = []


def main():
    global item_codes
    st.set_page_config(
        page_title="受注管理 (Linde様専用)",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("受注管理 (Linde様専用)")

    # --- 認証と権限チェック ---
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(1)
        st.switch_page("sign_in.py")
        return

    user_email = st.session_state.get("user_email", "不明なユーザー")
    user_roles_df = fetch_user_roles(email=user_email)

    if user_roles_df.is_empty() or not user_roles_df["can_write"][0]:
        st.error("このページにアクセスする権限がありません。")
        return

    # 品目リストをデータベースから取得 (キャッシュを活用)
    @st.cache_data(ttl=10)  # 10秒キャッシュ
    def get_item_codes():
        df = supabase_read_sql(
            "SELECT DISTINCT item_code FROM public.electrode_status ORDER BY item_code"
        )
        if not df.is_empty():
            return df["item_code"].to_list()
        return []

    item_codes = get_item_codes()

    # --- UIの定義 (タブの代わりにst.radioを使用して状態を維持) ---
    tab_options = ["新規受注登録", "新規受注CSV登録", "受注編集・削除"]
    
    # セッションステートでアクティブなタブを管理
    if "order_management_active_tab" not in st.session_state:
        st.session_state.order_management_active_tab = tab_options[0]

    selected_tab = st.radio(
        "メニュー",
        options=tab_options,
        key="order_management_active_tab",
        horizontal=True,
        label_visibility="collapsed"
    )

    if selected_tab == "新規受注登録":
        render_new_order_form()
    elif selected_tab == "新規受注CSV登録":
        render_new_ordercsv_form()
    elif selected_tab == "受注編集・削除":
        render_edit_order_form()

def render_new_order_form():
    """新規受注登録フォームをレンダリングする"""
    st.header("新規受注登録")

    input_mode = st.toggle("品目を手入力", value=False, key="input_mode")
    if input_mode:
        item_code = st.text_input(
            "品目*", help="必須項目です。", placeholder="品目を入力して下さい。"
        )
    else:
        item_code = st.selectbox(
            "品目*",
            options=item_codes,
            index=None,
            placeholder="品目を選択してください",
        )

    with st.form("new_order_form"):
        st.markdown("##### 新規受注情報を入力してください")
        giga_order_num = st.text_input("ギガ注番*", help="必須項目です。")
        giga_due_date = st.date_input("ギガ納期*", value=datetime.date.today())
        order_qty = st.number_input("受注数*", min_value=1, value=1, step=1)
        linde_order_num = st.text_input("リンデ注番 (任意)")

        submitted = st.form_submit_button("新規登録実行", type="primary")

        if submitted:
            if is_giga_order_exist(giga_order_num):
                st.error(
                    f"ギガ注番 `{giga_order_num}` は既に登録されています。別の注番を指定してください。"
                )
                return

            # --- 入力値のバリデーション ---
            if not all([giga_order_num, item_code, giga_due_date, order_qty]):
                st.error("必須項目 (*) をすべて入力してください。")
                return

            # --- 登録処理 ---
            queries = []
            base_sql_columns = "giga_order_num, item_code, giga_due_date, edaban"
            base_sql_values = ":giga_order_num, :item_code, :giga_due_date, :edaban"
            base_params = {
                "giga_order_num": giga_order_num,
                "item_code": item_code,
                "giga_due_date": giga_due_date,
            }

            # リンデ注番がある場合、SQLとパラメータに追加
            if linde_order_num:
                sql_columns = f"linde_order_num, {base_sql_columns}"
                sql_values = f":linde_order_num, {base_sql_values}"
                base_params["linde_order_num"] = linde_order_num
            else:
                sql_columns = base_sql_columns
                sql_values = base_sql_values

            # 受注数の回数だけINSERT文を生成
            for i in range(order_qty):
                params = base_params.copy()
                params["edaban"] = i + 1
                sql = f"""
                    INSERT INTO public.electrode_status ({sql_columns})
                    VALUES ({sql_values});
                """
                queries.append({"sql": sql, "params": params})

            # トランザクションで一括実行
            with st.spinner("データベースに登録しています..."):
                success = supabase_execute_sql(queries, use_transaction=True)

            if success:
                st.success(f"{order_qty}件の受注データを正常に登録しました。")
                st.balloons()
            else:
                st.error("登録処理中にエラーが発生しました。")

    if item_code:
        electrode_status_df = fetch_electrode_status_list(item_code=item_code)
        st.subheader(f" {item_code} の溶射電極状況一覧")
        st.dataframe(electrode_status_df, width="stretch")

def render_new_ordercsv_form():
    """新規受注CSV登録フォームをレンダリングする"""
    st.header("新規受注CSV登録")

    st.info("専用フォーマットのCSVファイルをアップロードして、一括で受注データを登録します。  \n- 下記のサンプルCSVダウンロードボタンでフォーマットを確認してください。")
    sample_csv = "ギガ注番,品目,ギガ納期,受注数,リンデ注番\nGIGA12345,ITEM001,2024-07-15,10,LINDE67890\nGIGA12346,ITEM002,2024-07-20,5,\n"
    st.download_button("サンプルCSVダウンロード", type="primary", data=sample_csv.encode("cp932"), file_name="sample_order_format.csv", mime="text/csv")

    csvfile = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"], help="CSVファイルには、ギガ注番、品目、ギガ納期、受注数、リンデ注番の列が必要です。")
    if csvfile is not None:
        try:
            import pandas as pd

            df = pd.read_csv(csvfile, header=0, encoding="cp932")
            required_columns = ["ギガ注番", "品目", "ギガ納期", "受注数"]
            for col in required_columns:
                if col not in df.columns:
                    st.error(f"CSVファイルに必須列 '{col}' が含まれていません。")
                    return
            st.success("CSVファイルを正常に読み込みました。内容を確認してください。")
            st.dataframe(df, width="stretch")
        # csvのエンコードエラー対策
        except UnicodeDecodeError as e:
            st.error(f"CSVファイルのエンコードに問題があります。Shift-JISまたはCP932形式のファイルをアップロードしてください: {e}")
            return
        except Exception as e:
            st.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            return
        
        insert_button = st.button("CSVデータを登録する", type="primary")
        if insert_button:
            # --- 登録処理 ---

            queries = []
            for _, row in df.iterrows():
                giga_order_num = row["ギガ注番"]
                item_code = row["品目"]
                giga_due_date = row["ギガ納期"]
                order_qty = int(row["受注数"])
                linde_order_num = row.get("リンデ注番", None)

                if is_giga_order_exist(giga_order_num):
                    st.warning(f"ギガ注番 `{giga_order_num}` は既に登録されています。スキップします。")
                    continue

                base_sql_columns = "giga_order_num, item_code, giga_due_date, edaban"
                base_sql_values = ":giga_order_num, :item_code, :giga_due_date, :edaban"
                base_params = {
                    "giga_order_num": giga_order_num,
                    "item_code": item_code,
                    "giga_due_date": giga_due_date,
                }

                if linde_order_num:
                    sql_columns = f"linde_order_num, {base_sql_columns}"
                    sql_values = f":linde_order_num, {base_sql_values}"
                    base_params["linde_order_num"] = linde_order_num
                else:
                    sql_columns = base_sql_columns
                    sql_values = base_sql_values

                for i in range(order_qty):
                    params = base_params.copy()
                    params["edaban"] = i + 1
                    sql = f"""
                        INSERT INTO public.electrode_status ({sql_columns})
                        VALUES ({sql_values});
                    """
                    queries.append({"sql": sql, "params": params})

            with st.spinner("データベースに登録しています..."):
                success = supabase_execute_sql(queries, use_transaction=True)

            if success:
                st.success(f"{len(queries)}件の受注データを正常に登録しました。")
                st.balloons()
            else:
                st.error("登録処理中にエラーが発生しました。")

def render_edit_order_form():
    """受注編集・削除フォームをレンダリングする"""
    st.header("受注編集・削除")

    # --- 検索フォーム ---
    st.markdown("##### 編集・削除したい受注を検索してください")
    search_item = st.selectbox(
        "品目で検索",
        options=item_codes,
        index=None,
        placeholder="品目を選択してください",
    )

    if not search_item:
        st.info("品目を選択してください。")
        return

    # --- 検索実行 ---
    with st.spinner("受注データを検索中..."):
        search_df = fetch_electrode_status_list(item_code=search_item, limit=100)

    if search_df.is_empty():
        st.warning("品番に一致する受注データは見つかりませんでした。")
        return

    # --- 検索結果表示と行選択 ---
    st.markdown("##### 検索結果")
    st.info("編集または削除したい行を選択してください。")

    # 日付列を文字列に変換して表示
    display_df = search_df.with_columns(pl.col("ギガ納期").dt.strftime("%Y-%m-%d"))

    # セッションステートに行選択イベントを保存
    if "selected_order" not in st.session_state:
        st.session_state.selected_order = {"rows": []}

    event = st.dataframe(
        display_df,
        on_select="rerun",
        selection_mode="single-row",
        key="search_results_df",
    )
    st.session_state.selected_order = event.selection

    # --- 編集・削除フォーム ---
    if st.session_state.selected_order["rows"]:
        selected_row_index = st.session_state.selected_order["rows"][0]
        selected_order = search_df[selected_row_index]

        giga_order_num = selected_order["ギガ注番"][0]
        item_code = selected_order["品目"][0]

        st.markdown("---")
        st.markdown(f"##### 以下の受注を編集・削除します")
        st.write(f"**ギガ注番:** `{giga_order_num}`")
        st.write(f"**品目:** `{item_code}`")

        with st.form("edit_order_form"):
            # 編集可能な項目
            new_giga_due_date = st.date_input(
                "ギガ納期", value=selected_order["ギガ納期"][0]
            )
            new_linde_order_num = st.text_input(
                "リンデ注番", value=selected_order["リンデ注番"][0] or ""
            )

            # フォームのボタンを横並びに配置
            col1, col2, _ = st.columns([1, 1, 4])
            with col1:
                update_submitted = st.form_submit_button("データ更新", type="primary")
            with col2:
                delete_submitted = st.form_submit_button("データ削除", type="secondary")

            if update_submitted:
                # --- 更新処理 ---
                update_query = {
                    "sql": """
                        UPDATE public.electrode_status
                        SET giga_due_date = :giga_due_date, linde_order_num = :linde_order_num
                        WHERE giga_order_num = :giga_order_num AND item_code = :item_code;
                    """,
                    "params": {
                        "giga_due_date": new_giga_due_date,
                        "linde_order_num": (
                            new_linde_order_num if new_linde_order_num else None
                        ),
                        "giga_order_num": giga_order_num,
                        "item_code": item_code,
                    },
                }
                with st.spinner("データを更新しています..."):
                    success = supabase_execute_sql(
                        [update_query], use_transaction=False
                    )

                if success:
                    if not "modified" in st.session_state:
                        st.session_state.modified = True
                        st.rerun()
                else:
                    st.error("更新処理中にエラーが発生しました。")

                if "modified" in st.session_state:
                    st.success("受注データを更新しました。")
                    st.session_state.pop("modified")

            if delete_submitted:
                # --- 削除処理 ---
                delete_query = {
                    "sql": """
                        DELETE FROM public.electrode_status
                        WHERE giga_order_num = :giga_order_num AND item_code = :item_code;
                    """,
                    "params": {
                        "giga_order_num": giga_order_num,
                        "item_code": item_code,
                    },
                }
                with st.spinner("データを削除しています..."):
                    success = supabase_execute_sql(
                        [delete_query], use_transaction=False
                    )

                if success:
                    if not "deleted" in st.session_state:
                        # 選択をクリアしてフォームを非表示にする
                        st.session_state.selected_order = {"rows": []}
                        st.session_state["deleted"] = True
                        st.rerun()
                else:
                    st.error("削除処理中にエラーが発生しました。")

                if "deleted" in st.session_state:
                    st.success("受注データを削除しました。")
                    st.session_state.pop("deleted")


def fetch_electrode_status_list(
    item_code: str, limit: int = 50, params: dict = None
) -> pl.DataFrame:
    """
    user_rolesテーブルからデータを取得し、Polars DataFrameとして返す
    Args:
        item_code (str): 品目コード
    Returns:
        pl.DataFrame: Polarsデータフレーム
    """
    parameters = {"item_code": item_code, "limit": limit}
    if params is not None:
        listWheres = []
        for key in params.keys():
            strWhere = f"AND {key} = :{key}"
            listWheres.append(strWhere)
        strWheres = " \n".join(listWheres)
        parameters = parameters | params
    else:
        strWheres = ""

    query = f"""
    -- 通常の電極ステータス (不具合登録されていないもの)
    SELECT
        linde_order_num AS "リンデ注番",
        giga_order_num AS "ギガ注番",
        item_code AS "品目",
        giga_due_date AS "ギガ納期",
        status AS "状況",
        count(*) AS 受注数,
        (CASE WHEN es.sirial_num IS NULL THEN 0 ELSE 1 END) AS "sn有"
    FROM
        public.electrode_status es
    WHERE
        es.item_code = :item_code
        AND COALESCE(es.status, '') not in ('判定中', '廃棄', '保留')
        {strWheres}
    GROUP BY
        linde_order_num,
        giga_order_num,
        item_code,
        giga_due_date,
        status,
        (CASE WHEN es.sirial_num IS NULL THEN 0 ELSE 1 END)
    ORDER BY
        (CASE WHEN es.sirial_num IS NULL THEN 0 ELSE 1 END),
        giga_due_date DESC,
        giga_order_num DESC
    LIMIT :limit
    """
    df = supabase_read_sql(query, parameters=parameters)
    return df


def is_giga_order_exist(giga_order_num: str) -> bool:
    """
    指定されたギガ注番と品目コードの組み合わせが存在するか確認する
    Args:
        giga_order_num (str): ギガ注番
    Returns:
        bool: 存在する場合はTrue、存在しない場合はFalse
    """
    query = """
    SELECT COUNT(*) AS order_count
    FROM public.electrode_status
    WHERE giga_order_num = :giga_order_num;
    """
    params = {"giga_order_num": giga_order_num}
    df = supabase_read_sql(query, parameters=params)
    if not df.is_empty() and df["order_count"][0] > 0:
        return True
    return False


if __name__ == "__main__":
    main()
