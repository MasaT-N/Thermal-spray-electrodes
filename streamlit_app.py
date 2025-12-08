import streamlit as st


# マニフェストの定義（ここでアプリ名をカスタム）
# JavaScriptコード: <head>に<link rel="manifest">を追加（height=0で非表示）
js_code = """
<script>
  if (!document.querySelector('link[rel="manifest"]')) {
    const link = document.createElement('link');
    link.rel = 'manifest';
    link.href = '/static/manifest.json';
    document.head.appendChild(link);
  }
</script>
"""
st.components.v1.html(js_code, height=0)
st.set_page_config(
        page_title="溶射電極管理システム",
        page_icon="🏠",
        initial_sidebar_state="expanded",
    )

pages = {
    "各種コンテンツ": [
        st.Page("main_contents.py", title="溶射電極状況表示",icon="📈"),
        st.Page("recent_shipments.py", title="最新出荷データ検索", icon="🔍"),
        st.Page("update_syukka_status.py", title="溶射電極出荷状況更新 (長津専用)", icon="🚚"),
    ],
    "アカウント管理": [
        st.Page("sign_in.py", title="サインイン／サインアップ",icon="🏠"),
        st.Page("change_username.py", title="ユーザー名の変更",icon="👤"),
        st.Page("password_reset.py", title="パスワードの変更",icon="🔑"),
        st.Page("sign_out.py", title="サインアウト",icon="🚪"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()