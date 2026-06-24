# チーム作業ガイド（GitHub / Kaggle / W&B のはじめ方）

このページは「Git も GitHub も初めて」という人でも、この `SB3-Team` プロジェクトに参加して作業できるようになることを目的にしたガイドです。上から順に読めば、環境構築から自分のブランチでの作業、Pull Request の出し方までひと通り分かります。技術的な仕様そのものは [メインの README](../README.md) にあるので、こちらは「操作のやり方」に絞っています。

---

## 0. まず全体像をつかむ

このプロジェクトでは3つのWebサービスを使い分けます。役割を最初に押さえておくと迷いません。

- **GitHub** … みんなのコード（このリポジトリ）を置いて共有する場所。「コードの保管庫＋共同編集の仕組み」。
- **Kaggle** … 自分のPCを占有せずに、クラウドのCPUで学習やsweepを放置実行させるための場所。
- **Weights & Biases（W&B）** … 学習の結果やsweep（ハイパラ探索）の進捗をブラウザで見える化・管理する場所。

流れとしては「**GitHub にコードを置く → Kaggle がそれを取ってきて学習を回す → 結果を W&B に送って全員で眺める**」という関係になっています。

---

## 1. Git と GitHub の超ミニ用語集

操作の前に、これだけ知っていれば読み進められる言葉を並べておきます。完璧に覚える必要はなく、「そういうものがある」と分かれば十分です。

- **リポジトリ（repository / repo）** … プロジェクト1つ分のフォルダ。今回の `SB3-Team` がそれ。
- **クローン（clone）** … GitHub 上のリポジトリを、自分のPCに丸ごとコピーしてくること。最初に1回だけやる。
- **ブランチ（branch）** … 作業用の枝分かれ。`main` が本流で、各自は `member/01`〜`member/05` という自分専用の枝で作業する。お互いの作業がぶつからないための仕組み。
- **コミット（commit）** … 変更に「ここまでの区切り」として名前（メッセージ）を付けて記録すること。セーブポイントのようなもの。
- **プッシュ（push）** … 自分のPCで作ったコミットを GitHub 側に送って反映すること。
- **プル（pull）** … 逆に、GitHub 側の最新の変更を自分のPCに取り込むこと。
- **プルリクエスト（Pull Request / PR）** … 「自分のブランチの変更を `main` に取り込んでください」とお願いする依頼。チームでレビューしてから合流させる。
- **マージ（merge）** … PR が承認されて、変更が実際に `main` に合流すること。
- **コンフリクト（conflict）** … 同じ場所を2人が別々に編集したときに起きる「どっちを採用する？」という衝突。あとで対処法を書きます。

---

## 2. 最初のセットアップ（各自、最初の1回だけ）

### 2-1. GitHub アカウントと招待

GitHub アカウントを持っていない人は https://github.com で無料登録します。登録できたら、自分の **GitHub ユーザー名** をチームのリポジトリ管理者（`shironaganegi`）に伝えてください。管理者があなたを Collaborator（共同編集者）として招待すると、登録メールに招待が届くので、その中のリンクから「Accept（承認）」します。これで初めて、あなたはこの Private リポジトリにアクセスできるようになります。

### 2-2. 必要なツールのインストール（Mac の場合）

ターミナルを開いて、Homebrew（パッケージ管理ツール）が入っているか確認します。

```bash
brew --version
```

入っていなければ https://brew.sh の手順に従って入れてください。Homebrew があれば、Git と GitHub CLI を入れます。

```bash
brew install git gh
```

（Windows の人は https://git-scm.com と https://cli.github.com からそれぞれインストーラーで入れてください。）

### 2-3. GitHub にログイン（認証）

このリポジトリは Private なので、クローンや push にはログインが必要です。GitHub CLI を使うのが一番ラクです。

```bash
gh auth login
```

聞かれたら次のように答えます。

- What account do you want to log into? → **GitHub.com**
- What is your preferred protocol …? → **HTTPS**
- Authenticate Git with your GitHub credentials? → **Y**
- How would you like to authenticate? → **Login with a web browser**

すると8桁のコードが表示されるので、それを控えてブラウザの認証画面に入力し、「Authorize」を押します。`Logged in as <あなたのユーザー名>` と出れば成功です。一度やればこのPCでは記憶されるので、次回以降は不要です。

### 2-4. リポジトリをクローン

作業を置きたい場所（例：ホームの `dev` フォルダなど）に移動してから、クローンします。

```bash
cd ~/dev          # 好きな置き場所に移動（フォルダが無ければ mkdir ~/dev で作る）
git clone https://github.com/shironaganegi/SB3-Team.git
cd SB3-Team
```

`SB3-Team` というフォルダができ、その中に入れれば準備OKです。

### 2-5. Python 環境をつくる

ここから先（仮想環境の作成と依存インストール）は [メイン README の §3「セットアップ」](../README.md) に手順があります。要点だけ書くと、

```bash
python3.12 -m venv .venv
source .venv/bin/activate      # 以降このターミナルでは .venv が有効
pip install -r requirements.txt
```

です。`source .venv/bin/activate` はターミナルを開き直すたびに実行が必要です（プロンプトの先頭に `(.venv)` と出ていれば有効な状態）。

---

## 3. 毎回の作業フロー（自分のブランチで進める）

ここが日々のメインです。「自分のブランチに移る → 編集する → コミットする → push する → PR を出す」の繰り返しになります。例として `member/01` を使いますが、自分の番号に読み替えてください。

### 3-1. 自分のブランチに切り替える

```bash
git fetch origin                 # GitHub 側の最新のブランチ情報を取得
git switch member/01             # 自分のブランチに移動
```

今どのブランチにいるかは `git branch` で確認できます（`*` が付いているのが現在地）。

### 3-2. 作業して、こまめにコミット

ファイルを編集したら、変更内容を確認して記録します。

```bash
git status                       # 何を変更したかの一覧
git add -A                       # 変更を全部「記録対象」に入れる
git commit -m "学習configのlearning_rateを調整"   # メッセージを付けて記録
```

コミットメッセージは「何をしたか」が後で分かるように、短くて具体的な日本語で構いません。作業がひと区切りつくたびにコミットしておくと、あとで戻りやすくなります。

### 3-3. GitHub に push

自分のコミットを GitHub に送ります。

```bash
git push origin member/01
```

これで GitHub 上の自分のブランチに反映されます。`git push` だけで済むこともありますが、最初は `origin ブランチ名` まで書いておくと確実です。

### 3-4. main の最新を取り込む（ときどき）

他の人の変更が `main` に入っていくので、自分のブランチが古くなりすぎないように、ときどき最新を取り込みます。

```bash
git fetch origin
git merge origin/main            # main の最新を自分のブランチに合流
```

ここでコンフリクト（衝突）が出ることがあります。対処は §5 を見てください。

### 3-5. Pull Request（PR）を出して main に合流させる

自分の作業がまとまって「`main` に入れてよい」状態になったら、PR を出します。コマンドでも作れます。

```bash
gh pr create --base main --head member/01 --title "member01: 学習configの調整" --body "learning_rateを7.3e-4から調整した"
```

ブラウザで作りたい場合は、GitHub のリポジトリページを開くと「`member/01` had recent pushes — Compare & pull request」という黄色いバナーが出るので、それを押して内容を書いて「Create pull request」でもOKです。

PR を出したら、チームの誰かに見てもらい（レビュー）、問題なければ GitHub の PR ページの「Merge pull request」ボタンで `main` に合流させます。マージ後は、自分のブランチで再び §3-1 から繰り返します。

---

## 4. ブランチ運用の考え方（なぜ直接 main を触らないのか）

`main` はチーム共通の「正」のコードです。ここを全員が直接いじると、誰かの未完成な変更で全体が壊れたり、お互いの編集が衝突して収拾がつかなくなります。そこで「各自は自分のブランチで自由に試し、完成したものだけ PR を通して `main` に入れる」という流れにしています。これにより、`main` は常に動く状態を保ちやすく、変更がレビューを通るので品質も保てます。最初は遠回りに感じますが、これが事故を防ぐ一番の近道です。

---

## 5. よくあるトラブルと対処

**push したら `rejected` と言われた。** たいていは「GitHub 側に自分がまだ持っていない変更がある」状態です。`git pull origin member/01` で取り込んでから、もう一度 push してください。

**コンフリクト（conflict）が出た。** 同じ箇所を別々に編集したときに起きます。該当ファイルを開くと `<<<<<<<`, `=======`, `>>>>>>>` という印で「自分の変更」と「相手の変更」が並んでいます。どちらを残すか（または両方をうまく統合するか）を手で編集し、その印の行を消したら、`git add <ファイル>` → `git commit` で解決完了です。分からなくなったら無理に進めず、チームに相談してください。

**認証エラーで clone / push できない。** §2-3 の `gh auth login` をやり直してください。`gh auth status` で今ログインできているか確認できます。

**変更を間違えた、コミット前の編集を捨てたい。** まだコミットしていない変更は `git restore <ファイル>` で元に戻せます。直前のコミット自体をやり直したいときは `git commit --amend` が使えますが、push 済みのものを書き換えるとややこしくなるので、その場合はチームに相談を。

---

## 6. Kaggle の使い方（sweep を放置で回す）

Kaggle は、自分のPCを長時間占有せずにクラウドのCPUで学習・sweep を回すために使います。

最初に **無料登録 → 電話番号認証** を済ませてください。ここが重要で、GPU だけでなく**インターネット接続**（`git clone`・`pip install`・W&B との通信に必要）も、電話番号認証をしないと有効化できません。設定画面の「Get phone verified」から認証します。

実際に回すときは、リポジトリの [`notebooks/kaggle_commit.ipynb`](../notebooks/kaggle_commit.ipynb) を Kaggle にアップロードして使います。ノートを開いたら、右側の設定パネルで次を確認します。

- **Accelerator** … 今回は GPU ではなく **CPU**（None）でよい。GPU 枠は消費しない。
- **Internet** … **On（connected）** にする（電話番号認証済みでないと選べません）。

そのうえで、ノート内の Secrets（後述の W&B キーや GitHub トークン）を登録し、上のセルから順に実行 → 最後に「**Save & Run All（Commit）**」を押すと、セッションを閉じてもクラウド側で最後まで走り切ります。これが「放置実行」です。

Private リポジトリを Kaggle から clone するには GitHub のトークンが要ります。GitHub の Settings → Developer settings → Personal access tokens で `repo` 権限のトークンを作り、Kaggle の Add-ons → Secrets に `GITHUB_TOKEN` という名前で登録してください（ノートの clone セルがそれを使う作りになっています）。

---

## 7. W&B（Weights & Biases）の使い方

W&B は、学習の進捗や sweep の結果をブラウザのダッシュボードで見るためのサービスです。

登録は、**学術メール（大学のメール）で Academic ライセンスを申請**します（https://wandb.ai/site/research）。クレジットカード登録が必要な Org トライアルのほうは使いません。

ログイン後、自分の **API キー**（https://wandb.ai/authorize で確認）を、Kaggle の Add-ons → Secrets に `WANDB_API_KEY` という名前で登録します。**キーをコードに直接書かないこと**。ノートが Secrets から読み込む作りになっています。

sweep（ハイパラ探索）は、誰か1人が手元で1回だけ作成します。

```bash
wandb sweep sweeps/classic_sweep.yaml
```

この出力に `entity/project/sweep_id` が表示されるので、それを Kaggle ノートの最後のセル（`wandb agent` の行）に貼って実行すると、その sweep の探索を Kaggle 側で進められます。複数人・複数セッションで同じ sweep ID を指定すれば、手分けして探索を進められます。

> 注意：sweep の代理指標（`eval/mean_reward`）はあくまで「当たりを付ける」ためのものです。**最終的な良し悪しは必ず `src/evaluate.py`（素の環境での完走率とゴール到達ステップ数）で判断**します。

---

## 8. このリポジトリでよく使うコマンド早見表

```bash
# 自分のブランチに移って最新化
git fetch origin
git switch member/01
git merge origin/main

# 変更を記録して送る
git add -A
git commit -m "やったことを短く"
git push origin member/01

# main に取り込むお願い（PR）
gh pr create --base main --head member/01

# 学習と評価（メインREADME §4 参照）
source .venv/bin/activate
python src/train.py --config configs/smoke.yaml          # まず配管確認
python src/evaluate.py models/<保存されたモデル>.zip      # 完走率とステップ数
```

分からないことがあれば、自己判断で `main` を直接いじらず、まずチームに聞くのが安全です。
