# BipedalWalker タイムトライアル（TQC / CPU / 5人チーム）

> **GitHub / Kaggle / W&B の使い方が初めての人は、まず [docs/GUIDE.md（チーム作業ガイド）](docs/GUIDE.md) を読んでください。** 環境構築からブランチ作業・Pull Request の出し方まで初心者向けに手順をまとめています。この README は技術仕様が中心です。

## 📍 いまのフェーズ（2026-07-13 更新）

| 項目 | 現在 |
|---|---|
| **いまの段階** | [§7](#7-進め方提出までの5ステップ) の **Step 4a（Hardcore 追加学習）進行中**。1回目（W&B run `chocolate-yogurt-12`）が完了: Hardcore eval 報酬 -71→160、採点再現は完走 0/5・reward 61.2（あと一歩）。同モデルは Classic では完走 5/5（576→744.6 ステップと遅くなる副作用あり）。Step 2 のベスト設定選定は [docs/BEST_CONFIG.md](docs/BEST_CONFIG.md) で完了済み |
| **提出候補モデル** | 提出は **班で1つの zip を両モード採点**（[§2.5](#25-最終課題の採点ルール要点)）なので、Classic 用と Hardcore 用を別々に作るのではなく1つの系譜を育てる。現候補は `chocolate-yogurt-12`（run `an3wpjb5`、Classic 5/5 ＋ Hardcore 報酬 61.2） |
| **各自やること** | ① Hardcore 続行: [notebooks/kaggle_hardcore_finetune.ipynb](notebooks/kaggle_hardcore_finetune.ipynb) を Save & Run All（既定値が続行用に設定済み・編集不要）。② vel_coef の効果測定（Step 3 兼レポート素材）: [notebooks/kaggle_train_config.ipynb](notebooks/kaggle_train_config.ipynb) を Save & Run All |

Step が進んだら（例: Basic で完走が出て Step 3 に移る）、気づいた人がこの表と更新日を PR で書き換えてください。

**目次:**
[1. プロジェクト概要](#1-プロジェクト概要) ｜ [2. 使うWebサービス](#2-使うwebサービスと登録手順) ｜ [2.5 採点ルール](#25-最終課題の採点ルール要点) ｜ [3. セットアップ](#3-セットアップ) ｜ [4. ローカルでの回し方](#4-ローカルでの回し方) ｜ [4.5 実験の地図](#45-実験の地図何を変えたいときどこを編集するか) ｜ [5. Kaggleでのsweep](#5-kaggleコミットでの-sweep-の回し方) ｜ [6. 共通評価プロトコル](#6-共通評価プロトコル) ｜ [7. 提出までの5ステップ](#7-進め方提出までの5ステップ) ｜ [8. ステップカウント](#8-ステップカウントについて確認済み) ｜ [9. モデル命名規則](#9-モデル命名規則) ｜ [10. チームの約束事](#10-チームの約束事) ｜ [11. 用語集](#11-用語集)

## 1. プロジェクト概要

このリポジトリは、`BipedalWalker-v3`（classic）のタイムトライアル課題に5人チームで取り組むための作業基盤です。**最終目標は、Classic（`BipedalWalker-v3`）を最速で完走し、Hardcore（`BipedalWalkerHardcore-v3`）でも完走したうえでタイムを縮めることです**（採点は両モードで行われ、完走できれば平均ステップ数=速さで順位づけされるため。[§2.5](#25-最終課題の採点ルール要点)）。アルゴリズムは sb3-contrib の TQC を使い（採用理由・仕組みは [docs/ALGORITHM.md](docs/ALGORITHM.md) 参照）、計算は各自のPCのCPU（`device="cpu"`）で回します。GPUは使いません。着手順としては、まず「学習 → 保存 → 評価 → sweep → Kaggle コミット」という配管が端から端まで一周回ることを確認し、速度チューニングはそのあと（後回しにするのは順番の話で、最終目標はあくまで速さです）。最終的な勝敗は、後述の共通評価スクリプト `src/evaluate.py` による完走率とゴール到達ステップ数だけで判断します。

強化学習の専門用語（seed・ハイパラ・sweep など）が分からなくなったら、[§11 の用語集](#11-用語集)を見てください。

## 2. 使うWebサービスと登録手順

**GitHub。** このリポジトリで全員が作業します。リポジトリは Public です。

**Kaggle。** 無料登録後、初回に電話番号認証が必須です。注意したいのは、GPUだけでなく**インターネット接続**（`git clone`・`pip install`・wandb 同期に必要）も、電話番号認証を済ませないと有効化できない点です。設定パネルの「Get phone verified」で認証したうえで、ノートブックの Settings → Internet を connected にしてください。今回はGPUではなく**CPUセッション**で回します。Kaggle コミット（Save & Run All）の手順は [§5](#5-kaggleコミットでの-sweep-の回し方) を参照してください。

**Weights & Biases（W&B）。** sweep の管理に使います。学術メールで Academic ライセンスを申請してください（https://wandb.ai/site/research）。カード登録が必要な Org トライアルは使いません。APIキーは、コードに直書きせず、Kaggle の Add-ons → Secrets に `WANDB_API_KEY` という名前で登録します。

## 2.5 最終課題の採点ルール（要点）

課題資料（実世界コンピューティングプロジェクト1 最終課題）から、モデル作りに直結するルールを抜き出したものです。

| 項目 | 内容 |
|---|---|
| 提出物① | **個人レポート**（A4 8枚以上・7章構成・PDF）。成績の主役はこちら |
| 提出物② | **タイムトライアル用モデルの zip（班で1つ）** を Classroom のフォームへ |
| モデルの採点環境 | **Basic / Hardcore の両モード**で評価される |
| 採点方法 | 1モデルにつきランダムコースで**5回評価し平均** |
| 順位づけ | ゴールできた場合=「ゴールまでの平均ステップ数」（少ないほど良い）。できない場合=「最大ステップ数における平均Reward」 |
| TT成績の扱い | 加点要素（上位10チームに加点）。完走できなくても、なぜ失敗したかの考察が深ければレポートで高評価が取れる |

この採点を手元で再現するコマンドは [§6](#6-共通評価プロトコル) を参照してください。レポートに関する注意も2つ:

- **レポートは自分の言葉で書くこと。** 生成AIで作った文章は採点時にチェックされます（班員間のコピペも禁止）。このリポジトリが出すデータ（`results/*.json`、W&B の学習曲線）は、あくまで根拠・素材として使ってください。
- **グラフや表はスクリーンショット貼付だと評価対象外になります。** W&B や `results/*.json` から数値を取り出し、**自分でプロットし直した**グラフを載せてください。

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
| ハイパラ（`learning_rate`・`seed` など）を変えて試す | `members/<自分の番号>/configs/` にコピーした YAML | 共有の `configs/` は直接書き換えない（[§4](#4-ローカルでの回し方)） |
| 新しいハイパラ項目（例: `ent_coef`）を試す | 自分の YAML に **1行足すだけ** | `src/train.py` の編集は不要。TQC が受け取れる名前なら自動で渡る |
| sweep の探索範囲（候補値・レンジ）を変える | `members/<自分の番号>/sweeps/` にコピーした YAML の `parameters:` | 共有の `sweeps/` を変えたいときは PR で提案 |
| Kaggle で回す本数・参加する sweep を変える | `notebooks/kaggle_commit.ipynb` 最終セルの変数 `SWEEP_ID` と `N_RUNS` | 書き換えるのはこの2行だけ（[§5](#5-kaggleコミットでの-sweep-の回し方)） |
| Hardcore（障害物コース）で追加学習する | **編集不要** | `python src/train.py --config configs/hardcore_finetune.yaml --resume checkpoints/<Basicのzip>`（[§7](#7-進め方提出までの5ステップ)） |
| 報酬整形（速度ボーナス以外の工夫）を足す | [src/wrappers.py](src/wrappers.py) | 共有資産なので PR で提案。**学習にしか使わない**こと（評価は素の環境） |
| 完走判定・評価のやり方を変える | [src/evaluate.py](src/evaluate.py) | 全員の最終選抜に影響するので、**チーム合意が必須** |

**表B: 用意された config / sweep の使い分け**

| ファイル | 何のためのものか | いつ使うか |
|---|---|---|
| `configs/smoke.yaml` | 配管確認（数千ステップで一周） | 環境構築の直後、コードを変えた後の動作確認 |
| `configs/classic_baseline.yaml` | `vel_coef=0` の素のTQC。**本命** | まず完走方策を固めるとき（今はここ） |
| `configs/classic_speed.yaml` | `vel_coef=2` の軽い速度ボーナス | baseline が完走できるようになった後 |
| `configs/classic_fast.yaml` | `vel_coef=4` + `time_penalty` の速さ重視 | 速度チューニング段階（やり込みは後回し、[§7](#7-進め方提出までの5ステップ)） |
| `configs/hardcore_smoke.yaml` | Hardcore 環境の配管確認（数千ステップ） | Hardcore に着手する前の動作確認 |
| `configs/hardcore_finetune.yaml` | Basic のベストモデルを Hardcore へ追加学習 | Basic で完走方策が固まった後（[§7](#7-進め方提出までの5ステップ) Step 4。**必ず `--resume` で使う**） |
| `sweeps/baseline_sweep.yaml` | `vel_coef=0` 固定で seed・学習率を探索 | **いま使うのはこちら**（[§7](#7-進め方提出までの5ステップ) の方針に対応） |
| `sweeps/classic_sweep.yaml` | `vel_coef` も含めて探索 | baseline 確立後の速度チューニング段階 |

## 5. Kaggleコミットでの sweep の回し方

sweep は手元で一度だけ作成します（いまの段階では baseline 専念の `baseline_sweep.yaml` を使います。使い分けは [§4.5](#45-実験の地図何を変えたいときどこを編集するか) 表B）。

```bash
wandb sweep sweeps/baseline_sweep.yaml
```

この出力に `entity/project/sweep_id` が表示されるので控えておきます。あとは `notebooks/kaggle_commit.ipynb` を Kaggle にアップロードし、ノート冒頭の注意書き（CPUセッション・インターネット接続・APIキーはSecrets）に従って、セルを上から順に埋めます。具体的には、(1) リポジトリの clone（Public なのでトークン不要）、(2) `pip install -r requirements.txt`、(3) Secrets からの `WANDB_API_KEY` 読み込みと `wandb login`、(4) 最終セルの変数 `SWEEP_ID`（チームの sweep が既定値で入っている）と `N_RUNS`（回す本数）を確認して、「Save & Run All（Commit）」で放置実行します。実測では1本の学習に6〜10時間かかるため、`N_RUNS` は **1** のままにしてください（2以上にすると、2本目がセッション上限の約12時間に達して強制終了され、Crashed になります）。

**Kaggleを使わず自分のPCだけで手早く試したいとき**は、`wandb login` で一度ログインし、config で `use_wandb: true` にしてから `python src/train.py --config <config>` を普通に実行するだけでW&Bに結果が送られます。sweepも `wandb agent <entity/project/sweep_id>` を手元のターミナルで直接実行すれば参加できます（放置はできず、ターミナルを閉じると止まる点だけ注意）。詳しい手順は [docs/GUIDE.md §7-C](docs/GUIDE.md) を参照してください。

## 6. 共通評価プロトコル

最終選抜は `src/evaluate.py` だけで行います。評価は必ず**素の環境**（学習時の `SpeedReward` を被せない）で、`deterministic=True`、**複数シード**で実施します。出すのは (1) 完走率、(2) 完走したエピソードのゴール到達ステップ数（平均・中央値）、(3) 全エピソードの平均報酬（`reward_mean`）です。完走の判定は頑健に作ってあり、転倒（報酬 -100 で終了）したエピソードは成功に数えません（判定ロジックとしきい値の根拠は `src/evaluate.py` のコメント参照）。1本の好成績で勝ちを決めず、必ず複数シードで安定して出ることを確認してください。

**最終課題の採点（[§2.5](#25-最終課題の採点ルール要点)）を手元で再現するには**、シードを5つ変えて1エピソードずつ回します（=ランダムコース5回の平均）。両モードで測ってください:

```bash
python src/evaluate.py models/<候補>.zip --seeds 0 1 2 3 4 --episodes 1
python src/evaluate.py models/<候補>.zip --env-id BipedalWalkerHardcore-v3 --seeds 0 1 2 3 4 --episodes 1
```

候補の優劣は課題の採点式に合わせて判断します: まず**完走率が高いものを優先**し（5回中3回完走のような部分完走は、完走率が高いほど本番で「平均ステップ数」で採点される側に入りやすい）、完走率が同じなら `goal_steps_mean` が小さいもの、完走ゼロ同士なら `reward_mean` が大きいものを選びます。学習中に自動保存される `models/best_model.zip` は「学習中のまぐれ当たり」の可能性があるため（課題資料でも同じ警告あり）、必ずこの5回平均で選抜してください。

## 7. 進め方（提出までの5ステップ）

最終課題の採点ルール（[§2.5](#25-最終課題の採点ルール要点)）が確定したので、提出までの道のりを5段階に分けます。各段階は前の段階の結果を土台にします。

**Step 1: Basic のベースラインを作る。** `configs/classic_baseline.yaml` で、複数人がそれぞれ別の `seed`（0〜4）を担当して回します。乱数の当たり外れが大きいため、複数シードで回すこと自体が探索になります（レポートの根拠にも使えます）。完了の目安は `evaluate.py` で完走が出始めること。BipedalWalker-v3 は TQC なら 100万ステップ前後で「解けた」（平均報酬300）に届くのが相場です。

**Step 2: ハイパラ探索（Step 1 と並行）。** `sweeps/baseline_sweep.yaml` の sweep に Kaggle から全員で参加します（[§5](#5-kaggleコミットでの-sweep-の回し方)）。当たり値が見つかったら classic_baseline に反映して Step 1 を上回るのが目標です。公式 sweep の結果とベスト設定の選定理由は [docs/BEST_CONFIG.md](docs/BEST_CONFIG.md) にまとめてあります（レポートに転記できる形式）。

**Step 3: タイム短縮。** `configs/classic_speed.yaml`（`vel_coef=2`）や `classic_fast.yaml` で報酬整形を乗せます。`vel_coef` を上げるほど平均ステップ数は減る方向に行きますが、上げすぎると転倒が増えて完走率が落ちるトレードオフがあります。baseline との比較は、そのままレポートの「結果」の章のグラフになります。

**Step 4: Hardcore への追加学習（カリキュラム学習）。** 採点は Basic / Hardcore の両モードで行われ、**Hardcore も完走できれば「平均ステップ数」（=速さ）で採点される**ため、Hardcore は完走して終わりではありません。2段階で進めます。

**(4a) まず完走させる。** Step 1〜3 のベストモデルのチェックポイントから Hardcore で追加学習します:

```bash
python src/train.py --config configs/hardcore_finetune.yaml --resume checkpoints/<ベストのzip>
```

Hardcore をゼロから学習するのは CPU の予算ではほぼ無理ですが、観測・行動の次元は Basic と同一なので、「歩ける」モデルに障害物対応だけ追加学習させるのが定石です。最初の目安は、Hardcore の評価で `reward_mean` が「その場で転ぶ」水準（約 -100）を明確に上回ること。その先の目標は完走が出ることです。

**(4b) 完走が出たら、Hardcore でもタイム短縮。** やり方は Step 3 と同じ発想です。`configs/hardcore_finetune.yaml` を `members/<自分の番号>/configs/` にコピーして `vel_coef` を軽く（例: 2）入れ、完走率が落ちていないかを [§6](#6-共通評価プロトコル) の採点再現コマンド（Hardcore側）で確認しながら詰めます。Basic と同様、速さを欲張って完走率を落とすと本番で「平均Reward採点」側に落ちて大損するので、**完走率優先**は変わりません。

**Step 5: 提出モデルの選抜。** 候補モデルを [§6](#6-共通評価プロトコル) の「採点再現コマンド」で両モード測定し、課題の採点式（完走なら平均ステップ最小、非完走なら平均Reward最大）で1つ選び、班で1つの zip として Classroom フォームへ提出します。

## 8. ステップカウントについて（確認済み）

`BipedalWalker-v3` では、エージェントの判断ステップと物理シミュレーションのステップは **1:1** です（gymnasium のソースで確認済み: `env.step()` 1回につき物理エンジンの `world.Step(1/50秒)` がちょうど1回実行される。フレームスキップなし）。つまり物理は 50 FPS で進み、エピソード上限 1600 ステップ = ゲーム内時間 32 秒に相当します。この 1:1 が保証されているので、`evaluate.py` が出すゴール到達ステップ数はそのまま「タイム」として比較できます。なお Hardcore（`BipedalWalkerHardcore-v3`）はコースが長く難しいぶん、エピソード上限が **2000 ステップ**（40 秒）に延びています。

## 9. モデル命名規則

最終モデルは次の規則で `models/` に保存します。

```
bipedalwalker_[hardcore_]tqc_velcoef{n}[_timepen{p}]_seed{n}_{steps}_{evalreward}.zip
```

`hardcore` は Hardcore 環境で学習したときだけ名前に入ります（Basic なら省略）。`velcoef` は速度ボーナス係数、`timepen` は時間ペナルティ（`time_penalty` を使ったときだけ名前に入る。0 なら省略）、`seed` は乱数シード、`steps` は学習総ステップ数、`evalreward` は評価報酬（EvalCallback のベスト）です。この名前は `src/train.py` が保存時に自動で付けるので、手で付ける必要はありません。

## 10. チームの約束事

このプロジェクトで全員が守るルールを、理由とセットでまとめます。迷ったらここに立ち返ってください。

- **評価（`src/evaluate.py`）に `SpeedReward` を絶対に被せない。** 報酬整形は学習を助けるための道具で、評価まで整形すると「速く見えるだけの方策」を選んでしまい、公平な比較ができなくなるためです。
- **学習は `device="cpu"` 固定。** 全員が同じ条件で回すことで結果を比較可能に保ち、Kaggle の限りある GPU 枠も温存します。
- **ハイパラの変更は YAML に書くだけ。`src/train.py` は書き換えない。** TQC の引数と同じ名前なら YAML に1行足すだけで自動で渡ります（[§4.5](#45-実験の地図何を変えたいときどこを編集するか) 表A）。スクリプトを各自がいじり始めると、誰の実験も再現できなくなります。
- **共有の `configs/`・`sweeps/`・`src/` を直接書き換えない。** 実験は `members/<自分の番号>/` で行い、チームのベースラインにしたい変更だけ PR で提案します（コンフリクト防止。詳細は [members/README.md](members/README.md)）。
- **config ファイルの中身が似ていても、共通化・include はしない（わざと重複させている）。** 「そのファイル1枚を見れば、その実験で使った値がすべて分かる」状態を保つためです。DRY にしたくなっても提案しないでください。
- **`main` に直接コミットしない。** 自分の `member/<番号>` ブランチで作業し、PR を通して合流します（理由は [docs/GUIDE.md §4](docs/GUIDE.md)）。GitHub のブランチ保護でも強制してあり、`main` への直接 push はエラーになります（PR のマージは今まで通り誰でもできます）。
- **APIキー・トークンをコードやノートに直書きしない。** Kaggle は Secrets、手元は `wandb login` を使います（[§2](#2-使うwebサービスと登録手順)）。
- **モデルの名前は [§9](#9-モデル命名規則) の命名規則（`train.py` が自動で付ける）に任せる。** ファイル名だけで「どの設定の成果物か」を全員が判別できるようにするためです。
- **コードや設定にコメントを書くときは、初心者向けの日本語で「なぜ」を書く。** このリポジトリは全員が Kaggle・W&B・SB3 初心者である前提で作られています。「何をするか」だけでなく「なぜそうするか」が書いてあると、次に読む人が迷いません。

## 11. 用語集

この README とコード・設定に出てくる専門用語のまとめです。分からない言葉が出てきたら、まずここに戻ってください。

| 用語 | 意味 |
|---|---|
| **エージェント** | 学習して動く側=二足歩行ロボットのこと。「モデル」とほぼ同じ意味で使われる |
| **環境（env）** | ロボットが歩くシミュレーション世界。Basic（`BipedalWalker-v3`）=平地メイン、Hardcore（`BipedalWalkerHardcore-v3`）=穴・階段・障害物あり |
| **ステップ（step）** | ロボットが関節を1回動かす最小単位。1秒=50ステップ（[§8](#8-ステップカウントについて確認済み)）。「平均ステップ数」はゴールまでの所要時間のこと |
| **エピソード** | スタートからゴール（または転倒・時間切れ）までの1回の試走 |
| **報酬（Reward）** | 環境がロボットに返す点数。前進すると+、転ぶと-100。学習は「報酬の合計を最大化する」方向に進む |
| **seed（シード）** | 乱数の「種」。コンピュータの乱数は種が同じなら毎回同じ列になる。学習は乱数だらけ（ネットの初期値・行動のゆらぎ・コース生成）なので、**seed を変える=同じ設定でもう1回ガチャを引く**こと。当たり外れが大きいので複数 seed で回す |
| **ハイパーパラメータ（ハイパラ）** | 学習の挙動を決める、人間が決める設定値（`learning_rate` など）。モデル自身が学習で獲得する値（重み）とは別物 |
| **learning_rate（学習率）** | 1回の更新でどれだけ大きく学ぶか。歩幅のようなもの。大きい=速く学ぶが不安定、小さい=着実だが遅い |
| **TQC / PPO / SAC** | 強化学習アルゴリズムの名前。授業の基本は PPO。このチームはより新しい TQC（サンプル効率が良く、CPU の少ない試行回数でも伸びやすい）を採用している。詳しくは [docs/ALGORITHM.md](docs/ALGORITHM.md) |
| **SB3（Stable-Baselines3）** | これらのアルゴリズムが実装済みの Python ライブラリ。自前でアルゴリズムを書かずに済む。TQC は拡張パッケージ sb3-contrib に入っている |
| **W&B（Weights & Biases）** | 実験記録の Web サービス。学習曲線が自動で溜まり、班全員の結果を1画面で比較できる（[§2](#2-使うwebサービスと登録手順)） |
| **sweep（スイープ）** | W&B の自動ハイパラ探索。「`learning_rate` は 0.0001〜0.001 の間で探して」と範囲を渡すと、良さそうな値を賢く（ベイズ最適化で）選んで試していく（[§5](#5-kaggleコミットでの-sweep-の回し方)） |
| **チェックポイント** | 学習途中のモデルの保存ファイル（`checkpoints/`）。ここから学習を再開（`--resume`）できる |
| **カリキュラム学習** | 簡単な環境（Basic）で学んでから難しい環境（Hardcore）に進ませる学習法。人間の学年制と同じ発想（[§7](#7-進め方提出までの5ステップ) Step 4） |
| **報酬整形（vel_coef / time_penalty）** | 元の報酬に「速いとボーナス」「1ステップごとに罰金」を足して、速く歩く方向へ誘導するこのチーム独自の工夫（`src/wrappers.py`）。**評価のときは外す**（公平な比較のため。[§10](#10-チームの約束事)） |
| **完走率（completion_rate）** | 試走のうちゴールまで歩き切れた割合。`evaluate.py` が出す第1指標 |
| **deterministic（決定的）評価** | 行動のランダムなゆらぎを止めて「一番自信のある行動」だけで走らせる評価方法。実力を安定して測れる |
