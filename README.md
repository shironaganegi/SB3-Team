# BipedalWalker タイムトライアル（TQC / CPU / 5人チーム）

> **GitHub / Kaggle / W&B の使い方が初めての人は、まず [docs/GUIDE.md（チーム作業ガイド）](docs/GUIDE.md) を読んでください。** 環境構築からブランチ作業・Pull Request の出し方まで初心者向けに手順をまとめています。この README は技術仕様が中心です。

## 1. プロジェクト概要

このリポジトリは、`BipedalWalker-v3`（classic）のタイムトライアル課題に5人チームで取り組むための作業基盤です。アルゴリズムは sb3-contrib の TQC を使い、計算は各自のPCのCPU（`device="cpu"`）で回します。GPUは使いません。まず目指すのは「学習 → 保存 → 評価 → sweep → Kaggle コミット」という配管が端から端まで一周回ることで、方策の作り込み（速度チューニングなど）は後回しです。最終的な勝敗は、後述の共通評価スクリプト `src/evaluate.py` による完走率とゴール到達ステップ数だけで判断します。

## 2. 使うWebサービスと登録手順

**GitHub。** このリポジトリで全員が作業します。リポジトリは Public です。

**Kaggle。** 無料登録後、初回に電話番号認証が必須です。注意したいのは、GPUだけでなく**インターネット接続**（`git clone`・`pip install`・wandb 同期に必要）も、電話番号認証を済ませないと有効化できない点です。設定パネルの「Get phone verified」で認証したうえで、ノートブックの Settings → Internet を connected にしてください。今回はGPUではなく**CPUセッション**で回します。Kaggle コミット（Save & Run All）の手順は §5 を参照してください。

**Weights & Biases（W&B）。** sweep の管理に使います。学術メールで Academic ライセンスを申請してください（https://wandb.ai/site/research）。カード登録が必要な Org トライアルは使いません。APIキーは、コードに直書きせず、Kaggle の Add-ons → Secrets に `WANDB_API_KEY` という名前で登録します。

## 3. セットアップ

Python は 3.12 を前提にしています（box2d / PyTorch / sb3-contrib のホイール事情が安定しているため）。仮想環境を作って依存をインストールしてください。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`gymnasium[box2d]` は Box2D 物理エンジンに依存します。多くの環境ではホイールで入りますが、ソースからビルドが必要になった場合は **SWIG** が要ります（macOS なら `brew install swig`、Ubuntu なら `sudo apt-get install swig build-essential`）。ビルド系のエラーが出たら、まず SWIG が入っているかを確認してください。

## 4. ローカルでの回し方

まず配管確認です。`configs/smoke.yaml` は `total_timesteps` を数千に絞ってあるので、学習から保存・評価までが通るかを短時間で確認できます。

```bash
python src/train.py --config configs/smoke.yaml
python src/evaluate.py models/<保存されたモデル>.zip
```

配管が通ったら、`configs/classic_baseline.yaml`（`vel_coef=0` の素のTQC）で本格的に完走方策を学習します。学習が終わったら、同じく `src/evaluate.py` に最終モデルを渡して、完走率とゴール到達ステップ数を確認します。チェックポイントから再開したい場合は `python src/train.py --config <config> --resume checkpoints/<ckpt>.zip` を使います。ただし**再開時のハイパラはチェックポイント保存時点の値が引き継がれ、YAML でハイパラを変えても反映されません**（変えて試したいときは新規学習で）。実行時にもその旨の注意が表示されます。

**パラメータを変えて実験するときは、共有の config を直接書き換えず、自分の個人フォルダ `members/<自分の番号>/configs/` にコピーして編集してください**（コンフリクト防止のため。ルールの詳細は [members/README.md](members/README.md)）。共有の `configs/`・`sweeps/` を変えたいときは PR で提案します。学習の成果物（`models/`・`checkpoints/`・`results/`）は Git 管理外で、結果の共有は W&B で行います。例外として最終提出候補のモデルだけ `models/final/` にコミットできます。

## 4.5 実験の地図（何を変えたいとき、どこを編集するか）

「実験したいけど、どのファイルを触ればいいのか分からない」となったら、まずこの2つの表を見てください。

**表A: やりたいこと別の編集場所**

| やりたいこと | 編集する場所 | 補足 |
|---|---|---|
| 用意された設定でそのまま学習を回す | **編集不要** | 下の表Bから config を選んで `python src/train.py --config <それ>` |
| ハイパラ（`learning_rate`・`seed` など）を変えて試す | `members/<自分の番号>/configs/` にコピーした YAML | 共有の `configs/` は直接書き換えない（§4） |
| 新しいハイパラ項目（例: `ent_coef`）を試す | 自分の YAML に **1行足すだけ** | `src/train.py` の編集は不要。TQC が受け取れる名前なら自動で渡る |
| sweep の探索範囲（候補値・レンジ）を変える | `members/<自分の番号>/sweeps/` にコピーした YAML の `parameters:` | 共有の `sweeps/` を変えたいときは PR で提案 |
| Kaggle で回す本数・参加する sweep を変える | `notebooks/kaggle_commit.ipynb` 最終セルの変数 `SWEEP_ID` と `N_RUNS` | 書き換えるのはこの2行だけ（§5） |
| 報酬整形（速度ボーナス以外の工夫）を足す | [src/wrappers.py](src/wrappers.py) | 共有資産なので PR で提案。**学習にしか使わない**こと（評価は素の環境） |
| 完走判定・評価のやり方を変える | [src/evaluate.py](src/evaluate.py) | 全員の最終選抜に影響するので、**チーム合意が必須** |

**表B: 用意された config / sweep の使い分け**

| ファイル | 何のためのものか | いつ使うか |
|---|---|---|
| `configs/smoke.yaml` | 配管確認（数千ステップで一周） | 環境構築の直後、コードを変えた後の動作確認 |
| `configs/classic_baseline.yaml` | `vel_coef=0` の素のTQC。**本命** | まず完走方策を固めるとき（今はここ） |
| `configs/classic_speed.yaml` | `vel_coef=2` の軽い速度ボーナス | baseline が完走できるようになった後 |
| `configs/classic_fast.yaml` | `vel_coef=4` + `time_penalty` の速さ重視 | 速度チューニング段階（やり込みは後回し、§7） |
| `sweeps/baseline_sweep.yaml` | `vel_coef=0` 固定で seed・学習率を探索 | **いま使うのはこちら**（§7 の方針に対応） |
| `sweeps/classic_sweep.yaml` | `vel_coef` も含めて探索 | baseline 確立後の速度チューニング段階 |

## 5. Kaggleコミットでの sweep の回し方

sweep は手元で一度だけ作成します（いまの段階では baseline 専念の `baseline_sweep.yaml` を使います。使い分けは §4.5 表B）。

```bash
wandb sweep sweeps/baseline_sweep.yaml
```

この出力に `entity/project/sweep_id` が表示されるので控えておきます。あとは `notebooks/kaggle_commit.ipynb` を Kaggle にアップロードし、ノート冒頭の注意書き（CPUセッション・インターネット接続・APIキーはSecrets）に従って、セルを上から順に埋めます。具体的には、(1) リポジトリの clone（Public なのでトークン不要）、(2) `pip install -r requirements.txt`、(3) Secrets からの `WANDB_API_KEY` 読み込みと `wandb login`、(4) 最終セルの変数 `SWEEP_ID`（チームの sweep が既定値で入っている）と `N_RUNS`（回す本数）を確認して、「Save & Run All（Commit）」で放置実行します。CPUなので `N_RUNS` は 3〜5 程度に控えめにしてください。

**Kaggleを使わず自分のPCだけで手早く試したいとき**は、`wandb login` で一度ログインし、config で `use_wandb: true` にしてから `python src/train.py --config <config>` を普通に実行するだけでW&Bに結果が送られます。sweepも `wandb agent <entity/project/sweep_id>` を手元のターミナルで直接実行すれば参加できます（放置はできず、ターミナルを閉じると止まる点だけ注意）。詳しい手順は [docs/GUIDE.md §7-C](docs/GUIDE.md) を参照してください。

## 6. 共通評価プロトコル

最終選抜は `src/evaluate.py` だけで行います。評価は必ず**素の環境**（学習時の `SpeedReward` を被せない）で、`deterministic=True`、**複数シード**で実施します。出すのは (1) 完走率と、(2) 完走したエピソードのゴール到達ステップ数（平均・中央値）です。完走の判定は頑健に作ってあり、転倒（報酬 -100 で終了）したエピソードは成功に数えません（判定ロジックとしきい値の根拠は `src/evaluate.py` のコメント参照）。1本の好成績で勝ちを決めず、必ず複数シードで安定して出ることを確認してください。

## 7. 進め方

最初は classic baseline（`vel_coef=0`）で、配管とTQCの完走方策を固めます。それができたら `configs/classic_speed.yaml`（`vel_coef=2`）で軽く速度ボーナスを乗せ、タイムが短くなりつつ完走率を保てるかを確認します。`vel_coef` の本格的なスイープや hardcore への投資は、最終課題の対象が確定してからにします。**速度チューニングを今の段階でやり込みすぎない**のが方針です。

## 8. ステップカウントについて（確認済み）

`BipedalWalker-v3` では、エージェントの判断ステップと物理シミュレーションのステップは **1:1** です（gymnasium のソースで確認済み: `env.step()` 1回につき物理エンジンの `world.Step(1/50秒)` がちょうど1回実行される。フレームスキップなし）。つまり物理は 50 FPS で進み、エピソード上限 1600 ステップ = ゲーム内時間 32 秒に相当します。この 1:1 が保証されているので、`evaluate.py` が出すゴール到達ステップ数はそのまま「タイム」として比較できます。

## 9. モデル命名規則

最終モデルは次の規則で `models/` に保存します。

```
bipedalwalker_tqc_velcoef{n}[_timepen{p}]_seed{n}_{steps}_{evalreward}.zip
```

`velcoef` は速度ボーナス係数、`timepen` は時間ペナルティ（`time_penalty` を使ったときだけ名前に入る。0 なら省略）、`seed` は乱数シード、`steps` は学習総ステップ数、`evalreward` は評価報酬（EvalCallback のベスト）です。この名前は `src/train.py` が保存時に自動で付けるので、手で付ける必要はありません。

## 10. チームの約束事

このプロジェクトで全員が守るルールを、理由とセットでまとめます。迷ったらここに立ち返ってください。

- **評価（`src/evaluate.py`）に `SpeedReward` を絶対に被せない。** 報酬整形は学習を助けるための道具で、評価まで整形すると「速く見えるだけの方策」を選んでしまい、公平な比較ができなくなるためです。
- **学習は `device="cpu"` 固定。** 全員が同じ条件で回すことで結果を比較可能に保ち、Kaggle の限りある GPU 枠も温存します。
- **ハイパラの変更は YAML に書くだけ。`src/train.py` は書き換えない。** TQC の引数と同じ名前なら YAML に1行足すだけで自動で渡ります（§4.5 表A）。スクリプトを各自がいじり始めると、誰の実験も再現できなくなります。
- **共有の `configs/`・`sweeps/`・`src/` を直接書き換えない。** 実験は `members/<自分の番号>/` で行い、チームのベースラインにしたい変更だけ PR で提案します（コンフリクト防止。詳細は [members/README.md](members/README.md)）。
- **config ファイルの中身が似ていても、共通化・include はしない（わざと重複させている）。** 「そのファイル1枚を見れば、その実験で使った値がすべて分かる」状態を保つためです。DRY にしたくなっても提案しないでください。
- **`main` に直接コミットしない。** 自分の `member/<番号>` ブランチで作業し、PR を通して合流します（理由は [docs/GUIDE.md §4](docs/GUIDE.md)）。
- **APIキー・トークンをコードやノートに直書きしない。** Kaggle は Secrets、手元は `wandb login` を使います（§2）。
- **モデルの名前は §9 の命名規則（`train.py` が自動で付ける）に任せる。** ファイル名だけで「どの設定の成果物か」を全員が判別できるようにするためです。
- **コードや設定にコメントを書くときは、初心者向けの日本語で「なぜ」を書く。** このリポジトリは全員が Kaggle・W&B・SB3 初心者である前提で作られています。「何をするか」だけでなく「なぜそうするか」が書いてあると、次に読む人が迷いません。
