import streamlit as st
from supabase import create_client, Client
import time
import polars as pl
from sqlalchemy import create_engine, exc
from util import get_db_engine, supabase_read_sql

# st.secretsからデータベース設定を取得(psycopg2用)
postgre_uid = st.secrets["postgre"]["uid"]
postgre_pwd = st.secrets["postgre"]["pwd"]
postgre_host = st.secrets["postgre"]["host"]
postgre_port = st.secrets["postgre"]["port"]
postgre_db = st.secrets["postgre"]["db"]

# データベース接続文字列
conn_str = f"postgresql://{postgre_uid}:{postgre_pwd}@{postgre_host}:{postgre_port}/{postgre_db}"

# Supabaseクライアントを初期化
@st.cache_resource
def init_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)

@st.cache_resource
def get_db_engine(conn_string: str):
    """SQLAlchemyのエンジンを作成し、キャッシュする"""
    # pool_pre_ping=True は、プールから接続を取得する前に、
    # その接続がまだ有効かテストするための「ping」を発行します。
    # これにより、ネットワークの問題やタイムアウトで切断された接続を再利用しようとするのを防ぎます。
    return create_engine(conn_string, pool_pre_ping=True)

supabase: Client = init_supabase_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
engine = get_db_engine(conn_str)

# @st.cache_data(ttl=600) # 10分間キャッシュ
def fetch_user_roles() -> pl.DataFrame:
    """
    user_rolesテーブルからデータを取得し、Polars DataFrameとして返す
    """

    query = """
SELECT
    u.email
    , ur.role
    , u.email_confirmed_at
    , u.last_sign_in_at
    , u.created_at
    , ur.can_read
    , ur.can_write
FROM
    auth.users u
    inner join public.user_roles ur on u.id = ur.id
    """
    return supabase_read_sql(query)

st.title("メインコンテンツ")

def main():

    st.set_page_config(
        page_title="メインコンテンツ",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 認証されていない、またはセッション状態が存在しない場合
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return
    else:
        st.success(f"{st.session_state.get('user_email', 'ユーザー')}としてログインしています。")

       
        st.divider()

        st.header("ユーザー役割一覧")
        user_roles_df = fetch_user_roles()
        st.dataframe(user_roles_df, width='stretch')

if __name__ == "__main__":
    main()