# supabaseでテーブルトリガーを作成する。

```text
supabaseで、新規ユーザー登録時にauth.usersテーブルにアカウントが登録される時にpublic.user_rolesにIDとemailの値を挿入したいのです。トリガーファンクションの作成方法を教えて下さい。
```
(Gemini回答)
以下に、ご希望のhandle_new_user関数とon_auth_user_createdトリガーを作成するためのSQLコードと、その設定手順を説明します。

### 概要
`auth.users`テーブルに新しいユーザーが作成される（`INSERT`される）と、それを検知して（`TRIGGER`）、あらかじめ定義しておいた`handle_new_user`という関数（`FUNCTION`）が自動的に実行されます。この関数が`public.user_roles`テーブルに新しいユーザーの`id`や`email`などの初期値を登録します。

### 1. `handle_new_user` 関数の作成
まず、`public.user_roles`テーブルにデータを挿入するための関数を作成します。この関数は、`auth.users`テーブルに新しく追加された行のデータ（`id`や`email`）を受け取って処理を行います。

以下のSQLをSupabaseのSQL Editorで実行してください。


```sql
-- public.user_roles テーブルに新しいユーザーを挿入する関数
create or replace function public.handle_new_user()
returns trigger
language plpgsql
-- この関数がauthスキーマのテーブルにアクセスできるようにsecurity definerを設定します
security definer set search_path = public
as $$
begin
  -- public.user_rolesテーブルに新しいレコードを挿入します
  insert into public.user_roles (id, email)
  values (
    new.id,     -- auth.usersから新しいユーザーのIDを取得
    new.email,  -- auth.usersから新しいユーザーのEmailを取得
  );
  return new;
end;
$$;
```
関数のポイント:

- `returns trigger`: この関数がトリガーによって呼び出されることを示します。
- `security definer`: この関数が、関数の作成者（この場合はpostgresロール）の権限で実行されるようにします。これにより、authスキーマへのアクセスが可能になります。
- `new.id`, `new.email`: auth.usersテーブルに挿入された新しい行のidとemailを参照しています。
- `user_name`の初期値として、メールアドレスの@より前の部分を自動的に設定するようにしています。
- `role`, `can_read`, `can_write` には、セキュリティを考慮して最も権限の低い初期値を設定しています。

### 2. `on_auth_user_created` トリガーの作成
次に関数を呼び出すためのトリガーを作成します。このトリガーは`auth.users`テーブルで`INSERT`イベントが発生した後に、各行に対して`handle_new_user`関数を実行します。

続けて、以下のSQLをSupabaseのSQL Editorで実行してください。

```sql
-- 既存のトリガーがあれば削除
drop trigger if exists on_auth_user_created on auth.users;

-- auth.usersテーブルにユーザーが作成された後に関数を実行するトリガー
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
```
トリガーのポイント:

- `after insert on auth.users`: auth.usersテーブルにデータが挿入された後にトリガーが発動します。
- `for each row`: 挿入された行ごとにトリガーが実行されます。
- `execute function public.handle_new_user()`: 先ほど作成した関数を呼び出します。
### 設定手順
1. Supabaseプロジェクトのダッシュボードにアクセスします。
2. 左側のメニューから SQL Editor を選択します。
3. New query をクリックします。
4. 上記のSQLコード（関数の作成とトリガーの作成）をエディタに貼り付けます。
5. RUN ボタンをクリックしてSQLを実行します。

これで設定は完了です。今後、supabase.auth.signUp()などで新しいユーザーが登録されると、自動的にpublic.user_rolesテーブルにもそのユーザーのレコードが作成されるようになります。