# Linde様によるギガフォトン受注オーダの登録画面

### 溶射電極オーダの新規受注登録画面と編集画面

#### 新規受注登録画面
- 新規受注登録画面では受注が発生した際に、public.electrode_statusに新規レコードを追加する。
#### 受注修正画面
- public.electrode_statusに登録済のオーダを修正する。

### 新規受注登録画面に必要な項目
- リンデ注番(linde_order_num)
    この項目は新規登録では必須ではない。しかし後に追記を可能とする。
- ギガ注番(giga_order_num)
- 品目(item_code)
- ギガ納期(giga_due_date)
- 受注数(この数に応じてレコードを追加する)

###　新規登録画面の項目
- リンデ注番(linde_order_num) -- テキストボックスで入力
  - この項目は新規登録では必須ではない。しかし後に追記を可能とする。
- ギガ注番(giga_order_num) -- テキストボックスで入力
  - 必須項目
- 品目(item_code) -- セレクトボックスで入力
  - 必須項目
- ギガ納期(giga_due_date) -- 日付入力ボックスで入力
  - 必須項目
- 受注数(この数に応じてレコードを追加する) -- 数字入力ボックスで入力
  - 必須項目
- 新規登録ボタン
  - ボタン押下で新規登録処理が処理され結果が表示される。

### 新規登録処理の流れ
- 画面からの入力情報を元に、public.electrode_statusに新規レコードを追加する。
- 受注数の回数だけ次のSQLを実行する。edabanは1から始まる変数として1ずつ増加する。
- リンデ注番(linde_order_num)は必須ではないので、未入力の場合はINSERT文に含めない。
```sql
    INSERT INTO public.electrode_status (
        linde_order_num,
        giga_order_num,
        item_code,
        giga_due_date,
        edaban
    )
    VALUES (
        :linde_order_num,
        :giga_order_num,
        :item_code,
        :giga_due_date
        :edaban
    );
```


###　受注編集画面の構成
次の項目でpublic.electorode_statusテーブルを検索してdf表示する。
- ギガ注番(giga_order_num) -- テキストボックスで入力
- 品目(item_code) -- セレクトボックスで入力
- ギガ納期(giga_due_date) -- 日付入力ボックスで入力
- リンデ注番(linde_order_num) -- テキストボックスで入力

  
表示されるdfは、ギガのオーダ毎に1レコードとする。
つまりデータ表示用SQLは以下の様なものとする。
```sql
    SELECT
        giga_order_num,
        item_code,
        giga_due_date,
        linde_order_num,
        count(*) AS qty
    FROM
        public.electrode_status
    where
        giga_order_num = :giga_order_num
        and item_code = :item_code
        and giga_due_date = :giga_due_date
        and linde_order_num = :linde_order_num
    group by
        linde_order_num,
        giga_order_num,
        item_code,
        giga_due_date
```
dfは選択可能として、行選択されると、編集フォームが表示される。

### 受注編集・削除フォーム
-　ギガ注番(giga_order_num) -- 編集不可
-　品目(item_code) -- 編集不可
-　リンデ注番(linde_order_num) -- テキストボックスで入力
-  ギガ納期(giga_due_date) -- 日付入力ボックスで入力(既定値は現状のテーブルから取得)

データ更新ボタンとデータ削除ボタンが用意されていて、押下でデータが更新される。

