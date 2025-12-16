import streamlit as st
import polars as pl
from sqlalchemy import create_engine, exc, text
import pandas as pd
from collections.abc import Mapping
from typing import Any
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# .envからデータベース設定を取得(psycopg2用)
postgre_uid = os.getenv("POSTGRE_UID")
postgre_pwd = os.getenv("POSTGRE_PWD")
postgre_host = os.getenv("POSTGRE_HOST")
postgre_port = os.getenv("POSTGRE_PORT")
postgre_db = os.getenv("POSTGRE_DB")

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
        with engine.connect() as connection:
            # SQLAlchemy Coreのexecuteを使い、結果を直接Polars DataFrameに変換
            # これにより、:key形式のパラメータが使えるようになる
            result = connection.execute(text(query), parameters)
            pandas_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            df = pl.from_pandas(pandas_df)
            return df
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
                conn_autocommit = connection.execution_options(
                    isolation_level="AUTOCOMMIT"
                )
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


def fetch_user_roles(email: str) -> pl.DataFrame:
    """
    user_rolesテーブルからデータを取得し、Polars DataFrameとして返す
    """

    query = """
SELECT
    u.email
    , ur.user_name
    , ur.role
    , u.email_confirmed_at
    , u.last_sign_in_at
    , u.created_at
    , ur.can_read
    , ur.can_write
FROM
    auth.users u
    inner join public.user_roles ur on u.id = ur.id
where
    u.email = :email
    """
    parameters = {"email": email}
    user_roles_df = supabase_read_sql(query, parameters=parameters)
    # 日付列["email_confirmed_at", "last_sign_in_at", "created_at"]は、日本時間に変換
    for date_col in ["email_confirmed_at", "last_sign_in_at", "created_at"]:
        user_roles_df = user_roles_df.with_columns(
            [
                pl.col(date_col)
                .dt.replace_time_zone("UTC")  # 元のデータがUTCであることを指定
                .dt.convert_time_zone("Asia/Tokyo")  # 日本時間に変換
                .dt.replace_time_zone(
                    None
                )  # タイムゾーン情報を削除（+09:00を非表示にする）
                .alias(date_col)
            ]
        )
    return user_roles_df
