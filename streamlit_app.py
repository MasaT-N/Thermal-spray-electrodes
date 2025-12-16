import streamlit as st

st.set_page_config(
    page_title="溶射電極管理システム",
    page_icon="🏠",
    initial_sidebar_state="expanded",
)

pages = {
    "各種コンテンツ": [
        st.Page("main_contents.py", title="溶射電極状況表示", icon="📈"),
        st.Page("recent_shipments.py", title="最新出荷データ検索", icon="🔍"),
        st.Page(
            "defective_electrode_registration.py", title="不具合電極登録", icon="⚠️"
        ),
        st.Page(
            "update_syukka_status.py",
            title="溶射電極出荷状況更新 (長津専用)",
            icon="🚚",
        ),
        st.Page("order_management_linde.py", title="受注管理 (Linde様専用)", icon="📝"),
    ],
    "アカウント管理": [
        st.Page("sign_in.py", title="サインイン／サインアップ", icon="🏠"),
        st.Page("change_username.py", title="ユーザー名の変更", icon="👤"),
        st.Page("password_reset.py", title="パスワードの変更", icon="🔑"),
        st.Page("sign_out.py", title="サインアウト", icon="🚪"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()
