import streamlit as st
from datetime import datetime
import time
import polars as pl
from util import get_db_engine, supabase_read_sql, fetch_user_roles, conn_str


def main():

    st.set_page_config(
        page_title="溶射電極状況表示",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("溶射電極状況表示")
    # 認証されていない、またはセッション状態が存在しない場合
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return
    else:
        # 認証されている場合
        user_email = st.session_state.get('user_email', '不明なユーザー')
        user_roles_df = fetch_user_roles(email=user_email)
        user_name = user_roles_df["user_name"][0]
        last_sign_in = user_roles_df["last_sign_in_at"][0].strftime("%Y-%m-%d %H:%M:%S")
        created_at = user_roles_df["created_at"][0].strftime("%Y-%m-%d %H:%M:%S")
        can_read = user_roles_df["can_read"][0]
        can_write = user_roles_df["can_write"][0]
        email_confirmed_at = user_roles_df["email_confirmed_at"][0]
        if email_confirmed_at is None:
            st.warning("メールアドレスが確認されていません。確認メールを再送信してください。")
            time.sleep(2)
            st.switch_page("sign_in.py")
            return
        st.success(f"""
##### ようこそ、{user_name}さんとしてログインしています。   
- 最終ログイン日時: {last_sign_in}
- 登録日時: {created_at}
- 読み取り権限: {'あり' if can_read else 'なし'}
- 書き込み権限: {'あり' if can_write else 'なし'}
                """)
        if can_read == False:
            st.warning("読み取り権限がありません。  \n- 長津グループの管理者に権限付与を申請して下さい。  ")
            return
        
        st.divider()

        item_list = fetch_item_list()
        item_code = st.selectbox("品目を選択してください", options=item_list, key="item_code")
        if item_code:
            # 検索条件の入力欄をExpander内に配置
            with st.expander("検索条件で絞り込む", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    giga_due_date_from = st.date_input("ギガ納期 (From)", value=None)
                    giga_due_date_to = st.date_input("ギガ納期 (To)", value=None)
                with col2:
                    shiped_date = st.date_input("出荷実績日", value=None)
                with col3:
                    serial_from = st.text_input("シリアル (From)", "")
                    serial_to = st.text_input("シリアル (To)", "")

            # 品目コードでデータを取得
            electrode_status_df = fetch_electrode_status_list(item_code=item_code)

            # 検索条件に基づいてDataFrameをフィルタリング
            # st.date_inputはdateオブジェクトを返すため、datetimeに変換してから比較する
            if giga_due_date_from and giga_due_date_to:
                start_datetime = datetime.combine(giga_due_date_from, datetime.min.time())
                end_datetime = datetime.combine(giga_due_date_to, datetime.max.time())
                electrode_status_df = electrode_status_df.filter(pl.col("ギガ納期").is_between(start_datetime, end_datetime))
            elif giga_due_date_from:
                start_datetime = datetime.combine(giga_due_date_from, datetime.min.time())
                electrode_status_df = electrode_status_df.filter(pl.col("ギガ納期") >= start_datetime)
            elif giga_due_date_to:
                end_datetime = datetime.combine(giga_due_date_to, datetime.max.time())
                electrode_status_df = electrode_status_df.filter(pl.col("ギガ納期") <= end_datetime)

            if shiped_date:
                target_datetime = datetime.combine(shiped_date, datetime.min.time())
                electrode_status_df = electrode_status_df.filter(pl.col("出荷実績日").dt.date() == target_datetime.date())
            
            if serial_from and serial_to:
                electrode_status_df = electrode_status_df.filter(pl.col("シリアル").is_between(serial_from, serial_to))

            # 表示用に日付列を YYYY-MM-DD 形式の文字列に変換する
            date_columns_to_format = ["ギガ納期", "出荷予定日", "出荷実績日", "台帳反映日"]
            for col_name in date_columns_to_format:
                # DataFrameに列が存在し、かつ日付/日時型である場合のみ変換を試みる
                if col_name in electrode_status_df.columns and electrode_status_df[col_name].dtype in [pl.Date, pl.Datetime]:
                    electrode_status_df = electrode_status_df.with_columns(
                        pl.col(col_name).dt.strftime("%Y-%m-%d").alias(col_name)
                    )

            st.subheader(f"選択された品目: {item_code} の溶射電極状況一覧")
            st.dataframe(electrode_status_df, width="stretch")

engine = get_db_engine(conn_str)

def fetch_item_list() -> list[str]:
    """
    品目リストビューからデータを取得し、Polars DataFrameとして返す
    """

    query = """
SELECT
    item_code                                   -- item_code
FROM
    public.v_item_list 
    """
    df = supabase_read_sql(query)
    return list(df["item_code"])


def fetch_electrode_status_list(item_code: str) -> pl.DataFrame:
    """
    user_rolesテーブルからデータを取得し、Polars DataFrameとして返す
    Args:
        item_code (str): 品目コード
    Returns:
        pl.DataFrame: Polarsデータフレーム
    """

    query = """
SELECT
    id                                          -- ID
    , linde_order_num                           as リンデ注番
    , giga_order_num                            as ギガ注番
    , item_code                                 as 品目
    , giga_due_date                             as ギガ納期
    , sirial_num                                as シリアル
    , status                                    as 状況
    , remarks                                   as 備考
    , ship_plan                                 as 出荷予定日
    , shiped_date                               as 出荷実績日
    , daicho_haneibi                            as 台帳反映日
    , linde_remarks                             as リンデ備考
FROM
    public.electrode_status 
WHERE
    item_code = %(item_code)s
ORDER BY
    (case when sirial_num is null then 0 else 1 end)
    , sirial_num desc
    , giga_due_date desc
    , giga_order_num desc
    """
    parameters = {"item_code": item_code}
    # sirial_numは数値と文字列が混在する可能性があるため、String型として読み込む
    electrode_status_list = supabase_read_sql(query, parameters=parameters)

    return electrode_status_list

if __name__ == "__main__":
    main()