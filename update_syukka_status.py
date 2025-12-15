import streamlit as st
from datetime import datetime
import time
import polars as pl
from util import (
    get_db_engine,
    supabase_read_sql,
    supabase_execute_sql,
    fetch_user_roles,
    conn_str,
)

def main():

    st.set_page_config(
        page_title="溶射電極出荷状況更新(長津専用)",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("溶射電極出荷状況更新(長津専用)")
    st.subheader("溶射電極の出荷状況をファイルのアップロードで更新します。")

    # 認証されていない、またはセッション状態が存在しない場合
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.warning("ログインしてください。")
        time.sleep(2)
        st.switch_page("sign_in.py")
        return
    else:
        # 認証されている場合
        user_email = st.session_state.get("user_email", "不明なユーザー")
        user_roles_df = fetch_user_roles(email=user_email)
        user_name = user_roles_df["user_name"][0]
        last_sign_in = user_roles_df["last_sign_in_at"][0].strftime("%Y-%m-%d %H:%M:%S")
        created_at = user_roles_df["created_at"][0].strftime("%Y-%m-%d %H:%M:%S")
        role = user_roles_df["role"][0]
        can_read = user_roles_df["can_read"][0]
        can_write = user_roles_df["can_write"][0]
        email_confirmed_at = user_roles_df["email_confirmed_at"][0]
        if email_confirmed_at is None:
            st.warning(
                "メールアドレスが確認されていません。確認メールを再送信してください。"
            )
            time.sleep(2)
            st.switch_page("sign_in.py")
            return
        if role not in ["nagatsu", "admin"] or can_write == False:
            st.warning(
                "このページにアクセスする権限がありません。  \n- 管理者に権限付与を申請してください。\n- この機能は基本的に長津グループ専用です。"
            )
            return

        syukka_file = st.file_uploader(
            "出荷シリアルデータ(専用のTSVファイル)をアップロードして下さい",
            type="tsv",
            accept_multiple_files=False,
            width="stretch",
        )
        if syukka_file:
            try:
                with syukka_file as f:
                    update_df = pl.read_csv(f, separator="\t", has_header=True)
                    # ギガ注番(giga_order_num)ごとのシリアル(sirial_num)順の連番の列を作成
                    update_df = update_df.with_columns(
                        pl.col("sirial_num")
                        .rank(method="ordinal")
                        .over("giga_order_num")
                        .alias("edaban")
                        .cast(pl.Int32)
                    )
                    update_df = fetch_electrode_status_list(update_df)
                    updatable_df = update_df.filter(pl.col("exists") == True).drop("exists")
                    not_updatable_df = update_df.filter(pl.col("exists") == False).drop("exists")
                    
                    st.text("更新対象のデータ")
                    st.dataframe(updatable_df, width="stretch")
                    if not_updatable_df.is_empty() == False:
                        st.warning(f"更新出来ないデータが{ not_updatable_df.shape(0) }件あります。")
                        st.dataframe(not_updatable_df, width="stretch")            
                    if updatable_df.is_empty() == False:
                        update_button = st.button("更新する", type="primary")
                        if update_button:
                            result = update_electrode_status_list(updatable_df)
                            if result:
                                st.success("更新が完了しました。")
                            else:
                                st.error("更新中にエラーが発生しました。")

       
            except Exception as e:
                st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
                return

def fetch_electrode_status_list(update_df: pl.DataFrame) -> pl.DataFrame:
    """読み込んだ出荷シリアルデータを元に電極状況表を更新対象のデータを取得
    Args:
        update_df (pl.DataFrame): 読み込んだ出荷シリアルデータ
    Returns:
        pl.DataFrame: 更新対象のデータ
    """
    # schema_dict = {
    #     "giga_order_num": pl.String,
    #     "edaban": pl.Int32,
    #     "exists": pl.Boolean,
    # }
    exists_df = pl.DataFrame()
    for row in update_df.to_dicts():
        try:
            params = {
                "giga_order_num": row["giga_order_num"],
                "edaban": row["edaban"],
            }
        except Exception as e:
            st.error(f"更新対象のデータの取得中にエラーが発生しました: {e}")
            return pl.DataFrame()

        query = """
SELECT
    es.id,
    es.item_code
FROM
    public.electrode_status es
WHERE
    es.giga_order_num = :giga_order_num
    AND es.edaban = :edaban
"""
        result_df = supabase_read_sql(query, parameters=params)
        if result_df.is_empty() == False:
            dict_exists={
                "giga_order_num": row["giga_order_num"],
                "edaban": row["edaban"],
                "exists": True,
            }
            exists_df = pl.concat([exists_df, pl.DataFrame([dict_exists])])
    try:
        updatable_df = update_df.join(exists_df, on=["giga_order_num", "edaban"], how="inner")
        return updatable_df
    except Exception as e:
        st.error(f"更新対象のデータの取得中にエラーが発生しました: {e}")
        return pl.DataFrame()
    

                
            



def update_electrode_status_list(update_df: pl.DataFrame) -> bool:
    """読み込んだ出荷シリアルデータを元に電極状況表を更新
    Args:
        update_df (pl.DataFrame): 読み込んだ出荷シリアルデータ
    Returns:
        bool: 更新結果の真偽値(True: 成功, False: 失敗)
    """
    queries = []
    for row in update_df.to_dicts():

        # 各種属性のパラメータの格納
        params = {
            "giga_order_num": row["giga_order_num"],
            "shiped_date": row["shiped_date"],
            "sirial_num": row["sirial_num"],
            "edaban": row["edaban"],
        }

        # 更新用クエリ
        query = """
UPDATE public.electrode_status
SET shiped_date = :shiped_date,
    sirial_num = :sirial_num,
    status = 'OK',
    update_dt = now()
WHERE 
    public.electrode_status.giga_order_num = :giga_order_num
    AND public.electrode_status.edaban = :edaban
"""
        queries.append({"sql": query, "params": params})
    result = supabase_execute_sql(queries)
    return result


if __name__ == "__main__":
    main()
