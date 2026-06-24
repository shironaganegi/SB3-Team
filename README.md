# BipedalWalker タイムトライアル（TQC / CPU / 5人チーム）

## 1. プロジェクト概要

このリポジトリは、`BipedalWalker-v3`（classic）のタイムトライアル課題に5人チームで取り組むための作業基盤です。アルゴリズムは sb3-contrib の TQC を使い、計算は各自のPCのCPU（`device="cpu"`）で回します。GPUは使いません。まず目指すのは「学習 → 保存 → 評価 → sweep → Kaggle コミット」という配管が端から端まで一周回ることで、方策の作り込み（速度チューニングなど）は後回しです。最終的な勝敗は、後述の共通評価スクリプト `src/evaluate.py` による完走率とゴール到達ステップ数だけで判断します。

## 2. 使うWebサービスと登録手順

**GitHub。** このリポジトリで全員が作業します。リポジトリ管理者は Settings → Collaborators から、チーム5人を Collaborator として招待してください。課題提出までの間はリポジトリを Private にしておきます。

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

配管が通ったら、`configs/classic_baseline.yaml`（`vel_coef=0` の素のTQC）で本格的に完走方策を学習します。学習が終わったら、同じく `src/evaluate.py` に最終モデルを渡して、完走率とゴール到達ステップ数を確認します。チェックポイントから再開したい場合は `python src/train.py --config <config> --resume checkpoints/<ckpt>.zip` を使います。

## 5. Kaggleコミットでの sweep の回し方

sweep は手元で一度だけ作成します。

```bash
wandb sweep sweeps/classic_sweep.yaml
```

この出力に `entity/project/sweep_id` が表示されるので控えておきます。あとは `notebooks/kaggle_commit.ipynb` を Kaggle にアップロードし、ノート冒頭の注意書き（CPUセッション・インターネット接続・APIキーはSecrets）に従って、セルを上から順に埋めます。具体的には、(1) リポジトリの clone URL、(2) `pip install -r requirements.txt`、(3) Secrets からの `WANDB_API_KEY` 読み込みと `wandb login`、(4) `wandb agent --count <N> <entity/project/sweep_id>` の `<...>` を実埋めし、「Save & Run All（Commit）」で放置実行します。CPUなので `--count` は控えめにしてください。

## 6. 共通評価プロトコル

最終選抜は `src/evaluate.py` だけで行います。評価は必ず**素の環境**（学習時の `SpeedReward` を被せない）で、`deterministic=True`、**複数シード**で実施します。出すのは (1) 完走率と、(2) 完走したエピソードのゴール到達ステップ数（平均・中央値）です。完走の判定は頑健に作ってあり、転倒（報酬 -100 で終了）したエピソードは成功に数えません（判定ロジックとしきい値の根拠は `src/evaluate.py` のコメント参照）。1本の好成績で勝ちを決めず、必ず複数シードで安定して出ることを確認してください。

## 7. 進め方

最初は classic baseline（`vel_coef=0`）で、配管とTQCの完走方策を固めます。それができたら `configs/classic_speed.yaml`（`vel_coef=2`）で軽く速度ボーナスを乗せ、タイムが短くなりつつ完走率を保てるかを確認します。`vel_coef` の本格的なスイープや hardcore への投資は、最終課題の対象が確定してからにします。**速度チューニングを今の段階でやり込みすぎない**のが方針です。

## 8. 未確認事項

ステップカウントが「エージェントの判断ステップ」なのか「物理シミュレーションのステップ」なのかが未確認です。これはフレームスキップの有効性を左右する重要な点なので、担当を一人決めて確定させてください。

## 9. モデル命名規則

最終モデルは次の規則で `models/` に保存します。

```
bipedalwalker_tqc_velcoef{n}_seed{n}_{steps}_{evalreward}.zip
```

`velcoef` は速度ボーナス係数、`seed` は乱数シード、`steps` は学習総ステップ数、`evalreward` は評価報酬（EvalCallback のベスト）です。
