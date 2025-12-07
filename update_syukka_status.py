import streamlit as st
from datetime import datetime
import time
import polars as pl
from util import get_db_engine, supabase_read_sql, supabase_execute_sql, conn_str



def main():

    st.set_page_config(
        page_title="溶射電極出荷状況更新",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("溶射電極出荷状況更新")
    st.caption("専用のTSVファイルのアップロードで出荷状況を更新できます。")

    # 認証されていない、またはセッション状態が存在しない場合
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return
    else:
        syukka_file = st.file_uploader("出荷シリアルデータをアップロードして下さい", type="tsv", accept_multiple_files=False,width="stretch")
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