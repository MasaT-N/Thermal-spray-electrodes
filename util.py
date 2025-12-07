import streamlit as st
import polars as pl
from sqlalchemy import create_engine, exc, text
import pandas as pd
from collections.abc import Mapping
from typing import Any
# st.secretsからデータベース設定を取得(psycopg2用)
postgre_uid = st.secrets["postgre"]["uid"]
postgre_pwd = st.secrets["postgre"]["pwd"]
postgre_host = st.secrets["postgre"]["host"]
postgre_port = st.secrets["postgre"]["port"]
postgre_db = st.secrets["postgre"]["db"]

# データベース接続文字列
conn_str = f"postgresql://{postgre_uid}:{postgre_pwd}@{postgre_host}:{postgre_port}/{postgre_db}"

@st.cache_resource
def get_db_engine(conn_string: str):
    """SQLAlchemyのエンジンを作成し、キャッシュする"""
    # pool_pre_ping=True は、プールから接続を取得する前に、
    # その接続がまだ有効かテストするための「ping」を発行します。
    # これにより、ネットワークの問題やタイムアウトで切断された接続を再利用しようとするのを防ぎます。
    return create_engine(conn_string, pool_pre_ping=True)

def supabase_read_sql(query: str, parameters: dict = None) -> pl.DataFrame:
    """SupabaseのPostgreSQLデータベースからSQLクエリを実行し、Polars DataFrameとして返す
    Args:
        query (str): 実行するSQLクエリ
        parameters (dict, optional): クエリパラメータ。デフォルトはNone。
    Returns:
        pl.DataFrame: Polarsデータフレーム
    """
    try:
        engine = get_db_engine(conn_str)
        # Pandasで読み込み、Polarsに変換する
        pandas_df = pd.read_sql(query, engine, params=parameters)
        return pl.from_pandas(pandas_df)
    except exc.SQLAlchemyError as e:
        st.error(f"データベースからのデータ取得中にエラーが発生しました: {e}")
        return pl.DataFrame()
def supabase_execute_sql(
    queries: list[Mapping[str, Any]], use_transaction: bool = True
) -> bool:
    """SupabaseのPostgreSQLデータベースにSQLクエリを実行する
    Args:
        queries (list[Mapping[str, Any]]): 実行するSQLクエリ
            各要素は {"sql": str, "params": dict} の形式の辞書。
            "params"キーはオプショナル。
        use_transaction (bool, optional): トランザクションを使用するかどうか。デフォルトはTrue。
    Returns:
        bool: クエリが成功したかどうかを示すブール値
    
    """
    # クエリの事前チェック
    for i, query in enumerate(queries):
        if not isinstance(query, Mapping) or "sql" not in query:
            msg = f"Invalid query format at index {i}. Each query must be a dict with a 'sql' key."
            st.error(msg)
            return False
    try:
        engine = get_db_engine(conn_str)
        with engine.connect() as connection:
            if use_transaction:
                with connection.begin():  # トランザクションを開始
                    for query in queries:
                        sql = query["sql"]
                        params = query.get("params")
                        connection.execute(text(sql), params)
            else:
                # 自動コミットモードで実行
                conn_autocommit = connection.execution_options(isolation_level="AUTOCOMMIT")
                for query in queries:
                    sql = query["sql"]
                    params = query.get("params")
                    conn_autocommit.execute(text(sql), params)

        print(f"All {len(queries)} queries executed successfully.")
        return True
    except Exception as e:
        # 接続エラーや実行エラーが発生した場合、トランザクションは自動的にロールバックされる
        failed_sql = getattr(e, "statement", "N/A")
        failed_params = getattr(e, "params", "N/A")
        st.error(
            f"Failed to execute queries. Transaction was rolled back. "
            f"Error on SQL: {failed_sql}, Params: {failed_params}. Error: {e}",
        )
        return False
    