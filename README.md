# JPX 銘柄別信用取引残高検索 Windows版

## Windows実行ファイルを作る方法

このZIPにはWindows用プログラムのソースと、GitHub Actionsで `.exe` を自動生成する設定が入っています。**このZIPそのものには `.exe` は入っていません。**

1. GitHubで新規リポジトリを作ります。
2. ZIP内の `main.py`、`requirements.txt`、`.github/workflows/build-windows.yml` をフォルダ構造のままアップロードします。
3. リポジトリの **Actions** → **Build Windows App** → **Run workflow** を実行します。
4. ビルド成功後、実行履歴の **Artifacts** にある **JPX-Windows-EXE** をダウンロードします。
5. 展開した `.exe` をWindowsでダブルクリックすると起動します。Pythonは不要です。

初回はWindowsのセキュリティ警告が出る可能性があります。発行元未署名のため、信頼できるファイルであることを確認してください。

## 検証状況・注意

- 添付された2026年10月8日申込分PDFの形式に合わせた解析です。
- JPXのページから最新PDFを自動取得する部分は、実環境で未検証です。
- GitHub ActionsでのWindowsビルドも未実行です。環境の更新やPopplerのインストール状況により調整が必要な場合があります。
- 最新PDFの公開形式が変わると動かなくなる可能性があります。
- 誤読防止のため、抽出件数が1,000件未満なら結果を表示しません。
