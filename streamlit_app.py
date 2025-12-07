import streamlit as st
import streamlit.components.v1 as components
import json

# マニフェストの定義（ここでアプリ名をカスタム）
manifest = {
    "name": "溶射電極管理システム",  # ホーム画面に表示されるフルネーム
    "short_name": "溶射電極",  # ホーム画面アイコンの下の短い名前
    "start_url": "/",  # 起動時のURL（デフォルトでOK）
    "display": "standalone",  # フルスクリーン表示
    "background_color": "#ffffff",  # 背景色
    "theme_color": "#000000",  # テーマ色（ステータスバーなど）
    "icons": [  # アイコン（少なくとも192x192と512x512を推奨。画像ファイルをリポジトリに置いてパス指定、または外部URL）
        {
            "src": "https://github.com/MasaT-N/Thermal-spray-electrodes/blob/main/icons/electrode192_192.png",  # アイコンURLを置き換え（例: GitHub raw URL）
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "https://github.com/MasaT-N/Thermal-spray-electrodes/blob/main/icons/electrode512_512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}

# JSONを文字列化
manifest_json = json.dumps(manifest)

# JavaScriptで<head>に<link rel="manifest">を追加（height=0で非表示）
js_code = f"""
<script>
    const link = document.createElement('link');
    link.rel = 'manifest';
    link.href = 'data:application/manifest+json,{manifest_json}';
    document.head.appendChild(link);
</script>
"""
components.html(js_code, height=0)
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