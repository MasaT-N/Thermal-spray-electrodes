import streamlit as st
from supabase import create_client, Client
import time

# メール送信用ライブラリ
import smtplib
from email.mime.text import MIMEText

import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- Supabase クライアントの初期化 ---
# .envから設定を取得
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# クライアントの作成
@st.cache_resource
def init_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)

supabase: Client = init_supabase_client(supabase_url, supabase_key)

# --- Streamlit UI の実装 ---

def send_notification_email(to_addrs: list[str], new_user_email: str):
    """管理者に新規ユーザー登録を通知するメールを送信する"""
    try:
        # .envからメール設定を取得
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        from_addr = smtp_user

        subject = "【溶射電極管理システム】新規ユーザー登録通知"
        body = f"""
管理者の皆様

新しいユーザーがシステムに登録されました。
内容を確認し、必要に応じて権限の付与を行ってください。

登録メールアドレス: {new_user_email}

溶射電極管理システム
"""

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = ", ".join(to_addrs)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
    except Exception as e:
        st.warning(f"管理者への通知メール送信中にエラーが発生しました: {e}")


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
    st.warning("- **アカウントを作成**ボタンを押すとそのメールアドレスにアカウントユーザー認証メールが送信されます。  \
               \n- 迷惑メールに分類されないように`noreply@mail.app.supabase.io`を受信許可してください。  \
               \n- アカウントが作成されると長津グループの管理者に**自動でメール通知**されます。   \
               \n- 新規アカウント登録及びメール認証後、サインインは可能になりますがデータへのアクセスはできません。   \
               \n- 長津グループの管理者の承認でデータへのアクセスが使用可能になります。")
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

                # 管理者に通知メールを送信
                try:
                    # RLSをバイパスするため、サービスロールキーでクライアントを一時的に作成
                    supabase_service = init_supabase_client(
                        os.getenv("SUPABASE_URL"), 
                        os.getenv("SUPABASE_SERVICE_KEY")
                    )
                    admin_users_response = supabase_service.table("user_roles").select("email").eq("role", "admin").execute()
                    if admin_users_response.data:
                        admin_emails = [user['email'] for user in admin_users_response.data]
                        send_notification_email(admin_emails, email)
                        st.info("管理者に新規登録が通知されました。")
                except Exception as e:
                    st.warning(f"管理者情報の取得中にエラーが発生しました: {e}")

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