import streamlit as st

pages = {
    "アカウント管理": [
        st.Page("sign_in.py", title="サインイン／サインアップ"),
        st.Page("password_reset.py", title="パスワードの変更"),
        st.Page("sign_out.py", title="サインアウト"),
    ],
    "コンテンツ": [
        st.Page("main_contents.py", title="メイン"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()