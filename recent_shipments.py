import streamlit as st
import time
import polars as pl
from util import supabase_read_sql, fetch_user_roles

def main():
    st.set_page_config(
        page_title="最新出荷データ検索",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("最新出荷データ検索")

    # 認証されていない、またはセッション状態が存在しない場合
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return
    
    # 認証されている場合
    user_email = st.session_state.get('user_email', '不明なユーザー')
    user_roles_df = fetch_user_roles(email=user_email)
    
    # ユーザー情報がない、または読み取り権限がない場合はアクセスを制限
    if user_roles_df.is_empty() or not user_roles_df["can_read"][0]:
        st.warning("このページにアクセスする権限がありません。")
        return

    # 表示件数の選択
    limit_options = [5, 10, 20, 30, 50]
    selected_limit = st.selectbox("最新の出荷実績日の表示件数を指定して下さい。", options=limit_options, index=0)

    # 出荷実績データの取得
    shipped_date_list = fetch_recent_shipment_dates(limit=selected_limit)

    if shipped_date_list:
        # フィルター用の選択肢を作成（「すべて」を追加）
        filter_options = ["すべて"] + shipped_date_list
        selected_date = st.selectbox("出荷実績日で絞り込み", options=filter_options)

        # 選択に基づいて取得する日付のリストを決定
        if selected_date == "すべて":
            target_dates = shipped_date_list
        else:
            target_dates = [selected_date]

        # 選択された日付でデータを取得
        shipment_df = fetch_shipment_data(target_dates)

        # 検索フィルター
        with st.expander("検索条件で絞り込む", expanded=False):
            search_linde_order = st.text_input("リンデ注番で絞り込み", key="search_linde")
            search_giga_order = st.text_input("ギガ注番で絞り込み", key="search_giga")
            search_item_code = st.text_input("品目で絞り込み", key="search_item")

        # フィルター適用
        filtered_df = shipment_df
        if search_linde_order:
            filtered_df = filtered_df.filter(pl.col("リンデ注番").str.contains(search_linde_order))
        if search_giga_order:
            filtered_df = filtered_df.filter(pl.col("ギガ注番").str.contains(search_giga_order))
        if search_item_code:
            filtered_df = filtered_df.filter(pl.col("品目").str.contains(search_item_code))
        
        if not filtered_df.is_empty():
            st.dataframe(filtered_df, width="stretch")
        else:
            st.info("指定された条件に一致するデータはありません。")
    else:
        st.info("表示対象の出荷データがありません。")

def fetch_recent_shipment_dates(limit: int = 5) -> list[str]:
    """
    指定された件数の最新出荷実績日を取得してリストとして返す
    Args:
        limit (int): 取得する件数. Defaults to 5.
    Returns:
        list[str]: 出荷実績日の文字列リスト
    """
    dates_query = """
    SELECT DISTINCT shiped_date
    FROM public.electrode_status
    WHERE shiped_date IS NOT NULL
    ORDER BY shiped_date DESC
    LIMIT %(limit)s
    """
    dates_df = supabase_read_sql(dates_query, parameters={"limit": limit})
    if dates_df.is_empty():
        return []
    
    return dates_df["shiped_date"].dt.strftime("%Y-%m-%d").to_list()

def fetch_shipment_data(target_dates: list[str]) -> pl.DataFrame:
    """
    指定された出荷実績日に基づいて出荷データを取得し、ギガ注番ごとにシリアルを集約して返す
    Args:
        target_dates (list[str]): 取得対象の出荷実績日リスト (YYYY-MM-DD形式)
    Returns:
        pl.DataFrame: 集計された出荷データのDataFrame
    """
    if not target_dates:
        return pl.DataFrame()

    data_query = """
    SELECT
        es.shiped_date as "出荷実績日",
        MAX(es.linde_order_num) as "リンデ注番",
        es.giga_order_num as "ギガ注番",
        MAX(es.item_code) as "品目",
        MAX(es.giga_due_date) as "ギガ納期",
        string_agg(es.sirial_num::text, ',' ORDER BY es.sirial_num) as "シリアル",
        string_agg(es.remarks, ',' ORDER BY es.sirial_num) as "備考"
    FROM
        public.electrode_status es
    WHERE
        es.shiped_date = ANY(%(target_dates)s::date[])
    GROUP BY
        es.shiped_date, es.giga_order_num
    ORDER BY
        "出荷実績日" DESC,
        "ギガ納期" DESC,
        "ギガ注番" DESC
    """
    shipped_df = supabase_read_sql(data_query, parameters={"target_dates": target_dates})

    # 日付列をYYYY-MM-DD形式に変換
    date_columns_to_format = ["出荷実績日", "ギガ納期"]
    for col_name in date_columns_to_format:
        if col_name in shipped_df.columns and shipped_df[col_name].dtype in [pl.Date, pl.Datetime]:
            shipped_df = shipped_df.with_columns(
                pl.col(col_name).dt.strftime("%Y-%m-%d").alias(col_name)
            )
    
    return shipped_df

if __name__ == "__main__":
    main()