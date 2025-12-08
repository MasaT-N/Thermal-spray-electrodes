import streamlit as st
from supabase import create_client, Client
import time


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

# --- Supabase クライアントの初期化 ---
# st.secretsから設定を取得
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["key"]

# クライアントの作成
@st.cache_resource
def init_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)

supabase: Client = init_supabase_client(supabase_url, supabase_key)

# --- Streamlit UI の実装 ---




def login_view():
    """サインインフォームを表示する関数"""
    st.header("サインイン")
    
    with st.form(key='login_form'):
        email = st.text_input("メールアドレス", key="login_email")
        password = st.text_input("パスワード", type="password", key="login_password")
        
        submit_button = st.form_submit_button("サインイン")

        if submit_button:
            if not email or not password:
                st.error("メールアドレスとパスワードを入力してください。")
                return
            
            try:
                # Supabaseのサインインメソッド呼び出し
                response = supabase.auth.sign_in_with_password({
                    "email": email, 
                    "password": password
                })
                # 成功したらセッション状態を更新してリロード
                st.session_state['authenticated'] = True
                st.session_state['user_email'] = response.user.email
                st.switch_page(st.Page("main_contents.py", title="Main_content"))
            except Exception as e:
                error_message = str(e)
                if "Invalid login credentials" in error_message:
                    st.error("メールアドレスまたはパスワードが間違っています。")
                elif "Email not confirmed" in error_message:
                    st.error("メールアドレスが確認されていません。  \n- 確認メールからのリンクを送信してください。  \n- 迷惑メールに分類された場合は、`@mail.app.supabase.io`を許可してください。")
                else:
                    st.error(f"サインイン中にエラーが発生しました: {error_message}")

def signup_view():
    """新規ユーザー登録フォームを表示する関数"""
    st.header("新規アカウント登録")
    
    # 新規アカウント登録フォーム
    with st.form(key='signup_form'):
        email = st.text_input("メールアドレス", key="signup_email")
        password = st.text_input("パスワード", type="password", key="signup_password")
        password_confirm = st.text_input("パスワード（確認）", type="password", key="signup_password_confirm")
        
        submit_button = st.form_submit_button("アカウントを作成")

        if submit_button:
            # 入力値のバリデーション
            if not email or not password or not password_confirm:
                st.error("すべてのフィールドを入力してください。")
                return

            if password != password_confirm:
                st.error("パスワードが一致しません。")
                return
            
            # パスワードの強度の確認 (任意)
            if len(password) < 6:
                st.error("パスワードは6文字以上である必要があります。")
                return

            # --- Supabaseのサインアップメソッド呼び出し ---
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            # --- レスポンス内容の判定 ---
            # 成功パターン1: メール確認が必要な場合 (userは存在するがsessionはNone)
            if response.user and not response.session:
                st.success(f"新規アカウント登録が完了しました！**{email}**宛に確認メールを送信しました。メール内のリンクをクリックしてアカウントを有効にしてください。")
                time.sleep(3)
                st.rerun()
            # 失敗パターン: userが存在しない場合 (既に登録済みなど)
            elif not response.user:
                st.error("このメールアドレスは既に登録されているか、登録できません。")
def main(): 
    st.set_page_config(
        page_title="溶射電極管理システム- サインイン",
        page_icon="🏠",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    st.title("🛡️ 溶射電極管理システム")               
    # --- メインロジック ---
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False    

    if st.session_state.authenticated:
        # サインイン済みの場合はメインコンテンツへリダイレクト
        st.switch_page("main_contents.py")
    else:
        # ページ選択ラジオボタン
        page = st.radio("メニュー", ('サインイン', '新規アカウント登録'), key="page_selection", label_visibility="collapsed", horizontal=True)

        if page == 'サインイン':
            login_view()
        elif page == '新規アカウント登録':
            signup_view()
            
if __name__ == "__main__":
    main()