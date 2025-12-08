import streamlit as st
import time
from util import fetch_user_roles, supabase_execute_sql

def main():
    st.set_page_config(
        page_title="ユーザー名変更",
        page_icon="👤",
        initial_sidebar_state="expanded",
    )
    st.title("ユーザー名変更")
    st.subheader("溶射電極管理システムのユーザー名変更ページです。")
    
    # 認証チェック
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("このページにアクセスするにはサインインが必要です。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return

    try:
        user_email = st.session_state.get('user_email')
        if not user_email:
            st.error("ユーザー情報が取得できませんでした。再度サインインしてください。")
            time.sleep(2)
            st.switch_page("sign_in.py")
            return

        # 現在のユーザー情報を取得
        user_roles_df = fetch_user_roles(email=user_email)
        if user_roles_df.is_empty():
            st.error("ユーザープロファイルが見つかりません。")
            return
        
        current_user_name = user_roles_df["user_name"][0]

        st.info(f"現在のユーザー名: **{current_user_name}**")

        # ユーザー名変更フォーム
        with st.form(key='change_username_form'):
            new_user_name = st.text_input("新しいユーザー名", value=current_user_name)
            submit_button = st.form_submit_button("ユーザー名を変更")

            if submit_button:
                if not new_user_name.strip():
                    st.error("ユーザー名を入力してください。")
                    return
                
                # データベース更新クエリ
                query = {
                    "sql": """
                        UPDATE public.user_roles
                        SET user_name = :user_name
                        ,updated_at = NOW()
                        WHERE id = (SELECT id FROM auth.users WHERE email = :email)
                    """,
                    "params": {"user_name": new_user_name.strip(), "email": user_email}
                }

                if supabase_execute_sql([query]):
                    st.success("ユーザー名が正常に変更されました。")
                    time.sleep(3)
                    st.rerun() # ページを再読み込みして更新後の名前を表示
                else:
                    st.error("ユーザー名の変更中にエラーが発生しました。")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()