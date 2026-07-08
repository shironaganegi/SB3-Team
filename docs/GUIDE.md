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

Kaggle は、自分のPCを長時間占有せずにクラウドのCPUで学習・sweep を回すために使います。イメージとしては「Kaggle のサイト上で Jupyter ノートブックを開き、実行ボタンを押すと、自分のPCを閉じてもクラウド側で計算が続く」というものです。

やることは大きく分けて2段階です。**(A) 初回だけの準備**と、**(B) sweep を回すたびにやる手順**。順に説明します。

### 6-A. 初回だけの準備（アカウント作成〜Secrets登録）

1. **Kaggle に無料登録する。** https://www.kaggle.com からメールアドレスで登録します。
2. **電話番号認証をする。** Kaggle のプロフィール → Settings を開き、「Phone verification」の「Get phone verified」から自分の電話番号を認証します。**これをやらないとノートブックでインターネット接続が使えず、`git clone` も `pip install` もできません。**必ず最初に済ませてください。
3. **W&B の API キーを手に入れる。** W&B に登録（次の §7 参照）してから https://wandb.ai/authorize を開くと、長い英数字のキーが表示されるのでコピーしておきます。
4. **キーを Kaggle に登録する。** Kaggle でノートブックを開いた状態で、上部メニューの **Add-ons → Secrets** を選び、「Add secret」で次のように入力します。
   - Label（名前）: `WANDB_API_KEY` （この通りに、大文字・アンダースコアまで正確に）
   - Value（値）: さっきコピーした W&B のキー
   登録したら、その Secret の**チェックボックスを On** にしてノートに紐付けます（登録しただけでは読めません）。

ここまでやれば準備完了です。2回目以降は不要です。

> なお、このリポジトリは Public（誰でも見られる公開設定）なので、GitHub のトークンやパスワードは一切不要です。ノートが勝手に clone してくれます。

### 6-B. sweep を回すたびにやる手順

1. **sweep ID をもらう。** sweep はチームの誰か1人が手元で作ります（作り方は §7）。作った人から `entity/project/sweep_id` という形式のID（例: `taro/bipedal-timetrial/abc123xy`）を教えてもらってください。すでに動いている sweep に相乗りする場合も、同じIDを使うだけでOKです。
2. **ノートブックを Kaggle にアップロードする。** Kaggle のトップから **Create → New Notebook** を開き、**File → Import Notebook** で、このリポジトリの [`notebooks/kaggle_commit.ipynb`](../notebooks/kaggle_commit.ipynb)（自分のPCに clone してあるもの）を選んでアップロードします。
3. **右側の設定パネル（Session options）を確認する。**
   - **Accelerator** … **None（CPU）** のままでよい。GPU は選ばない（GPU 枠を消費しないため）。
   - **Internet** … **On** にする（電話番号認証が済んでいないとここが選べません）。
4. **Secrets が紐付いているか確認する。** Add-ons → Secrets で `WANDB_API_KEY` のチェックが On になっているか見ます（6-A で登録済みのはず）。
5. **最後のセルの `<...>` を書き換える。** ノートの一番下のセルにある

   ```
   !wandb agent --count <N> <entity/project/sweep_id>
   ```

   の `<N>` を回す本数（CPUなので 3〜5 程度が目安）、`<entity/project/sweep_id>` を手順1でもらったIDに書き換えます。山かっこ `<>` ごと消して実際の値を書くことに注意してください。
6. **「Save & Run All (Commit)」を押す。** 画面右上の **Save Version** ボタン → **Save & Run All (Commit)** を選んで保存すると、クラウド側でノートが最初から最後まで自動実行されます。**この後はブラウザを閉じてもPCの電源を切っても計算は続きます。**これが「放置実行」です。
7. **進み具合を見る。** 実行中のログは Kaggle のノートページの「View Active Events」や Version 画面から見られます。学習の中身（各 run の成績）は W&B のダッシュボード（§7）で確認するのが分かりやすいです。

**よくあるつまずき:**

- `git clone` や `pip install` で失敗する → Internet が Off のままか、電話番号認証がまだ。手順 6-A-2 と 6-B-3 を確認。
- `Secret not found` のようなエラー → Secrets の名前が `WANDB_API_KEY` と完全一致しているか、チェックボックスが On かを確認。
- セルを1個ずつ手で実行して途中で止まる → 手動実行はセッションを閉じると止まります。放置したいなら必ず「Save & Run All (Commit)」を使ってください。

---

## 7. W&B（Weights & Biases）の使い方

W&B は、学習の進捗や sweep（ハイパラ探索）の結果をブラウザのダッシュボードで見える化するサービスです。Kaggle で回した学習の結果が自動でここに集まってくるので、チーム全員が同じ画面で「どの設定が良さそうか」を眺められます。

### 7-A. 登録とAPIキーの取得（全員がやる）

1. **学術メール（大学のメール）で Academic ライセンスを申請**します（https://wandb.ai/site/research）。クレジットカード登録が必要な Org トライアルのほうは使いません。
2. ログイン後、https://wandb.ai/authorize を開くと自分の **API キー**が表示されます。これをコピーして、§6-A の手順4の通り Kaggle の Secrets に登録します。
3. **キーをコードやノートに直接書かないこと。**ノートは Secrets から読み込む作りになっています。キーを書いたままノートやコードを公開すると、他人があなたのアカウントで書き込めてしまいます。

### 7-B. sweep の作り方（誰か1人だけがやる）

sweep とは「ハイパーパラメータの組み合わせを変えながら学習を何本も回し、良い設定を探す仕組み」です。sweep 自体の作成は、チームの誰か1人が自分のPC（このリポジトリの仮想環境に入った状態）で1回だけやれば済みます。

```bash
wandb sweep sweeps/classic_sweep.yaml
```

実行すると出力の中に `wandb agent entity/project/sweep_id` という行が表示されます。この `entity/project/sweep_id` の部分（例: `taro/bipedal-timetrial/abc123xy`）が sweep のIDです。**これをチームに共有してください。**各メンバーはこのIDを §6-B の手順で Kaggle ノートに貼れば、同じ sweep の探索に参加できます。複数人・複数セッションで同じIDを指定すれば、手分けして探索が進みます。

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
