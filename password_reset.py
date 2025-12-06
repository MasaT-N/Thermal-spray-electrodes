import streamlit as st
from supabase import create_client, Client
import time


# Supabaseクライアントを初期化
@st.cache_resource
def init_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)

supabase: Client = init_supabase_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

st.title("パスワード変更")

def password_reset_view():
    """パスワード変更フォームを表示する関数"""
    st.header("新しいパスワードを設定")

    with st.form(key='password_reset_form'):
        new_password = st.text_input("新しいパスワード", type="password", key="new_password")
        new_password_confirm = st.text_input("新しいパスワード（確認）", type="password", key="new_password_confirm")

        submit_button = st.form_submit_button("パスワードを変更")

        if submit_button:
            if not new_password or not new_password_confirm:
                st.error("すべてのフィールドを入力してください。")
                return

            if new_password != new_password_confirm:
                st.error("パスワードが一致しません。")
                return
            
            if len(new_password) < 6:
                st.error("パスワードは6文字以上である必要があります。")
                return

            try:
                # Supabaseのユーザー情報更新メソッドを呼び出し
                supabase.auth.update_user({"password": new_password})
                st.success("パスワードが正常に変更されました。")
            except Exception as e:
                st.error(f"パスワードの変更中にエラーが発生しました: {e}")

def main():
    # 認証されていない場合はサインインページにリダイレクト
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("このページにアクセスするにはサインインが必要です。")
        time.sleep(2)
        st.switch_page("sign_in.py")
    else:
        password_reset_view()

if __name__ == "__main__":
    main()