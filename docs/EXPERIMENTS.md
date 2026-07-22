# 実験の回し方（ローカル / Kaggle / 命名規則）

このページは「実験を回したい」「どのファイルを触ればいいか分からない」に答える1枚です。ほかの困りごとの入口は [README のドキュメント地図](../README.md) を見てください。

**目次:**
[1. ローカルでの回し方](#1-ローカルでの回し方) ｜ [2. 実験の地図](#2-実験の地図何を変えたいときどこを編集するか) ｜ [3. Kaggleでのsweep](#3-kaggleコミットでの-sweep-の回し方) ｜ [4. モデル命名規則](#4-モデル命名規則)

## 1. ローカルでの回し方

まず配管確認です。`configs/smoke.yaml` は `total_timesteps` を数千に絞ってあるので、学習から保存・評価までが通るかを短時間で確認できます（環境構築がまだの人は [GUIDE.md](GUIDE.md) から）。

```bash
python src/train.py --config configs/smoke.yaml
python src/evaluate.py models/<保存されたモデル>.zip
```

配管が通ったら、`configs/classic_baseline.yaml`（`vel_coef=0` の素のTQC）で本格的に完走方策を学習します。学習が終わったら、同じく `src/evaluate.py` に最終モデルを渡して、完走率とゴール到達ステップ数を確認します。チェックポイントから再開したい場合は `python src/train.py --config <config> --resume checkpoints/<ckpt>.zip` を使います。ただし**再開時のハイパラはチェックポイント保存時点の値が引き継がれ、YAML でハイパラを変えても反映されません**（変えて試したいときは新規学習で）。実行時にもその旨の注意が表示されます。

**パラメータを変えて実験するときは、共有の config を直接書き換えず、自分の個人フォルダ `members/<自分の番号>/configs/` にコピーして編集してください**（コンフリクト防止のため。ルールの詳細は [members/README.md](../members/README.md)）。共有の `configs/`・`sweeps/` を変えたいときは PR で提案します。学習の成果物（`models/`・`checkpoints/`・`results/`）は Git 管理外で、結果の共有は W&B で行います。例外として最終提出候補のモデルだけ `models/final/` にコミットできます。

## 2. 実験の地図（何を変えたいとき、どこを編集するか）

「実験したいけど、どのファイルを触ればいいのか分からない」となったら、まずこの2つの表を見てください。

**表A: やりたいこと別の編集場所**

| やりたいこと | 編集する場所 | 補足 |
|---|---|---|
| 用意された設定でそのまま学習を回す | **編集不要** | 下の表Bから config を選んで `python src/train.py --config <それ>` |
| ハイパラ（`learning_rate`・`seed` など）を変えて試す | `members/<自分の番号>/configs/` にコピーした YAML | 共有の `configs/` は直接書き換えない（[§1](#1-ローカルでの回し方)） |
| 新しいハイパラ項目（例: `ent_coef`）を試す | 自分の YAML に **1行足すだけ** | `src/train.py` の編集は不要。TQC が受け取れる名前なら自動で渡る |
| sweep の探索範囲（候補値・レンジ）を変える | `members/<自分の番号>/sweeps/` にコピーした YAML の `parameters:` | 共有の `sweeps/` を変えたいときは PR で提案 |
| Kaggle で回す本数・参加する sweep を変える | `notebooks/kaggle_commit.ipynb` 最終セルの変数 `SWEEP_ID` と `N_RUNS` | 書き換えるのはこの2行だけ（[§3](#3-kaggleコミットでの-sweep-の回し方)） |
| Hardcore（障害物コース）で追加学習する | **編集不要** | `python src/train.py --config configs/hardcore_finetune.yaml --resume checkpoints/<Basicのzip>`（[ROADMAP.md](ROADMAP.md)） |
| 報酬整形（速度ボーナス以外の工夫）を足す | [src/wrappers.py](../src/wrappers.py) | 共有資産なので PR で提案。**学習にしか使わない**こと（評価は素の環境） |
| 完走判定・評価のやり方を変える | [src/evaluate.py](../src/evaluate.py) | 全員の最終選抜に影響するので、**チーム合意が必須** |

**表B: 用意された config / sweep の使い分け**

| ファイル | 何のためのものか | いつ使うか |
|---|---|---|
| `configs/smoke.yaml` | 配管確認（数千ステップで一周） | 環境構築の直後、コードを変えた後の動作確認 |
| `configs/classic_baseline.yaml` | `vel_coef=0` の素のTQC。**本命** | まず完走方策を固めるとき（今はここ） |
| `configs/classic_speed.yaml` | `vel_coef=2` の軽い速度ボーナス | baseline が完走できるようになった後 |
| `configs/classic_fast.yaml` | `vel_coef=4` + `time_penalty` の速さ重視 | 速度チューニング段階（やり込みは後回し、[ROADMAP.md](ROADMAP.md)） |
| `configs/hardcore_smoke.yaml` | Hardcore 環境の配管確認（数千ステップ） | Hardcore に着手する前の動作確認 |
| `configs/hardcore_finetune.yaml` | `vel_coef=0`。Basic のベストモデルを Hardcore へ追加学習（完走優先） | Basic で完走方策が固まった後（[ROADMAP.md](ROADMAP.md) Step 4a。**必ず `--resume` で使う**） |
| `configs/hardcore_finetune_velcoef.yaml` | `vel_coef=1`。Hardcore で完走が出た後、速度報酬を導入 | Hardcore 完走が出た後（[ROADMAP.md](ROADMAP.md) Step 4b。**必ず `--resume` で使う**） |
| `sweeps/baseline_sweep.yaml` | `vel_coef=0` 固定で seed・学習率を探索 | **いま使うのはこちら**（[ROADMAP.md](ROADMAP.md) の方針に対応） |
| `sweeps/classic_sweep.yaml` | `vel_coef` も含めて探索 | baseline 確立後の速度チューニング段階 |

## 3. Kaggleコミットでの sweep の回し方

sweep は手元で一度だけ作成します（いまの段階では baseline 専念の `baseline_sweep.yaml` を使います。使い分けは [§2](#2-実験の地図何を変えたいときどこを編集するか) 表B）。

```bash
wandb sweep sweeps/baseline_sweep.yaml
```

この出力に `entity/project/sweep_id` が表示されるので控えておきます。あとは `notebooks/kaggle_commit.ipynb` を Kaggle にアップロードし、ノート冒頭の注意書き（CPUセッション・インターネット接続・APIキーはSecrets）に従って、セルを上から順に埋めます。具体的には、(1) リポジトリの clone（Public なのでトークン不要）、(2) `pip install -r requirements.txt`、(3) Secrets からの `WANDB_API_KEY` 読み込みと `wandb login`、(4) 最終セルの変数 `SWEEP_ID`（チームの sweep が既定値で入っている）と `N_RUNS`（回す本数）を確認して、「Save & Run All（Commit）」で放置実行します。実測では1本の学習に6〜10時間かかるため、`N_RUNS` は **1** のままにしてください（2以上にすると、2本目がセッション上限の約12時間に達して強制終了され、Crashed になります）。

Kaggle の画面操作を1ステップずつ知りたい人は [GUIDE.md §6](GUIDE.md#6-kaggle-の使い方sweep-を放置で回す) に詳しい手順があります。

**Kaggleを使わず自分のPCだけで手早く試したいとき**は、`wandb login` で一度ログインし、config で `use_wandb: true` にしてから `python src/train.py --config <config>` を普通に実行するだけでW&Bに結果が送られます。sweepも `wandb agent <entity/project/sweep_id>` を手元のターミナルで直接実行すれば参加できます（放置はできず、ターミナルを閉じると止まる点だけ注意）。詳しい手順は [GUIDE.md §7-C](GUIDE.md#7-wbweights--biasesの使い方) を参照してください。

## 4. モデル命名規則

最終モデルは次の規則で `models/` に保存します。

```
bipedalwalker_[hardcore_]tqc_velcoef{n}[_timepen{p}]_seed{n}_{steps}_{evalreward}.zip
```

`hardcore` は Hardcore 環境で学習したときだけ名前に入ります（Basic なら省略）。`velcoef` は速度ボーナス係数、`timepen` は時間ペナルティ（`time_penalty` を使ったときだけ名前に入る。0 なら省略）、`seed` は乱数シード、`steps` は学習総ステップ数、`evalreward` は評価報酬（EvalCallback のベスト）です。この名前は `src/train.py` が保存時に自動で付けるので、手で付ける必要はありません。
