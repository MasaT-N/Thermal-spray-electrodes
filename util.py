import streamlit as st
import polars as pl
from sqlalchemy import create_engine, exc

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
        pl.DataFrame: データフレーム
    """
    try:
        engine = get_db_engine(conn_str)
        df = pl.read_database(query, execute_options={"parameters": parameters}, connection=engine)
        return df
    except exc.SQLAlchemyError as e:
        st.error(f"データベースからのデータ取得中にエラーが発生しました: {e}")
        return pl.DataFrame()