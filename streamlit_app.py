import streamlit as st

st.set_page_config(
        page_title="溶射電極管理システム",
        page_icon="🏠",
        initial_sidebar_state="expanded",
    )

pages = {
    "アカウント管理": [
        st.Page("sign_in.py", title="サインイン／サインアップ"),
        st.Page("password_reset.py", title="パスワードの変更"),
        st.Page("sign_out.py", title="サインアウト"),
    ],
    "コンテンツ": [
        st.Page("main_contents.py", title="溶射電極状況表示"),
        st.Page("update_syukka_status.py", title="溶射電極出荷状況更新"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()