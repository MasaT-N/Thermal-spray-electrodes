import streamlit as st
from datetime import datetime
import time
import polars as pl
from util import get_db_engine, supabase_read_sql, supabase_execute_sql, fetch_user_roles, conn_str


def main():

    st.set_page_config(
        page_title="溶射電極出荷状況更新",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("溶射電極出荷状況更新")
    st.subheader("溶射電極の出荷状況をファイルのアップロードで更新します。")

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
        role = user_roles_df["role"][0]
        can_read = user_roles_df["can_read"][0]
        can_write = user_roles_df["can_write"][0]
        email_confirmed_at = user_roles_df["email_confirmed_at"][0]
        if email_confirmed_at is None:
            st.warning("メールアドレスが確認されていません。確認メールを再送信してください。")
            time.sleep(2)
            st.switch_page("sign_in.py")
            return
        if role not in ["nagatsu", "admin"] or can_write == False:  
            st.warning("このページにアクセスする権限がありません。  \n- 管理者に権限付与を申請してください。\n- この機能は基本的に長津グループ専用です。")
            return
        
        syukka_file = st.file_uploader("出荷シリアルデータ(専用のTSVファイル)をアップロードして下さい", type="tsv", accept_multiple_files=False,width="stretch")
        if syukka_file:
            try:
                with syukka_file as f:
                    df = pl.read_csv(f, separator="\t", has_header=True)
                    st.dataframe(df, width="stretch")
            except Exception as e:
                st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
                return


if __name__ == "__main__":
    main()