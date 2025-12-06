import streamlit as st
from supabase import create_client, Client
import time

def main():
    st.title("サインアウトページ")

    if 'authenticated' in st.session_state and st.session_state.authenticated:
        st.text("以下のボタンをクリックしてサインアウトしてください。")
        if st.button("ログアウト", type="primary"):
            supabase_url = st.secrets["supabase"]["url"]
            supabase_key = st.secrets["supabase"]["key"]
            supabase: Client = create_client(supabase_url, supabase_key)
            supabase.auth.sign_out()
            st.session_state.authenticated = False
            st.success("サインアウトしました。サインインページにリダイレクトします。")
            time.sleep(2)
            st.switch_page("sign_in.py")
    else:
        st.warning("現在、サインインしていません。")
        time.sleep(1)
        st.switch_page("sign_in.py")

if __name__ == "__main__":
    main()