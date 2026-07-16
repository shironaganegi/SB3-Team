# BipedalWalker タイムトライアル（TQC / CPU / 5人チーム）

`BipedalWalker-v3`（Classic）のタイムトライアル課題に5人チームで取り組むリポジトリです。**最終目標は、Classic を最速で完走し、Hardcore（`BipedalWalkerHardcore-v3`）でも完走したうえでタイムを縮めること**です（採点は両モードで行われ、完走できれば平均ステップ数=速さで順位づけされるため。詳細は [docs/EVALUATION.md](docs/EVALUATION.md)）。アルゴリズムは sb3-contrib の TQC（採用理由は [docs/ALGORITHM.md](docs/ALGORITHM.md)）、計算は各自のPCのCPU（`device="cpu"`）で回します。GPUは使いません。最終的な勝敗は、共通評価スクリプト `src/evaluate.py` による完走率とゴール到達ステップ数だけで判断します。

## 🗺️ ドキュメント地図（困ったらまずここ）

「知りたいことがどこに書いてあるか分からない」ときは、この表から飛んでください。

| 困りごと | 読む場所 |
|---|---|
| Git / GitHub / Kaggle / W&B が初めて。環境構築・ブランチ・PRのやり方を知りたい | [docs/GUIDE.md](docs/GUIDE.md) |
| 実験を回したい。どのファイルを触ればいいか分からない | [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) |
| モデルの良し悪しをどう測る? 最終課題の採点ルールは? | [docs/EVALUATION.md](docs/EVALUATION.md) |
| 全体の進め方（提出までの5ステップ）を知りたい | [docs/ROADMAP.md](docs/ROADMAP.md) |
| チームのルール・約束事を確認したい | [docs/RULES.md](docs/RULES.md) |
| 専門用語（seed・ハイパラ・sweep など）が分からない | [docs/GLOSSARY.md](docs/GLOSSARY.md) |
| なぜ TQC を使うのか（レポート素材） | [docs/ALGORITHM.md](docs/ALGORITHM.md) |
| sweep の結果とベスト設定の選定理由（レポート素材） | [docs/BEST_CONFIG.md](docs/BEST_CONFIG.md) |
| 個人フォルダ `members/` の使い方 | [members/README.md](members/README.md) |

## 📍 いまのフェーズ（2026-07-16 更新）

| 項目 | 現在 |
|---|---|
| **いまの段階** | [docs/ROADMAP.md](docs/ROADMAP.md) の **Step 4a（Hardcore 完走率の底上げ）を継続中**。`pf8e9dqb` から vel_coef=0 で再学習した4周目は、並行して2本走っていた。1本目（run `jp5jwddi` / mild-lion-18）は eval 報酬がピーク **243.5** まで伸びて好調だったが 3.69M step 時点で **NaN クラッシュ**（gSDE の数値爆発）し、ピークのモデルは回収できなかった。`src/train.py` に対策3点（発散防止・NaN 時の安全停止・ベスト更新のたびに即アップロード）を追加済み。もう1本（run `75glj5ue` / light-hill-20）はクラッシュせず完走し、20シード採点再現で **Hardcore完走 65%（13/20）・goal_steps_mean 877.0**、**Classic 100%（5/5）** と resume元の `pf8e9dqb`（Hardcore 55%）から明確に改善（Classic劣化なし）。同runの最終モデル（model.zip）は完走60%とbest_model.zipより劣っており、ベスト到達点の回収が引き続き重要と確認できた。合わせて [notebooks/kaggle_hardcore_finetune.ipynb](notebooks/kaggle_hardcore_finetune.ipynb) を修正し、resume時に model.zip ではなく best_model.zip を優先取得するようにした。完走率はまだ伸びしろがあるため、vel_coef=1（Step 4b）に戻すのはもう1周分の様子を見てから判断する。詳細は [docs/BEST_CONFIG.md §8-§9](docs/BEST_CONFIG.md#8-追記2026-07-15-mild-lion-18-の-nan-クラッシュ調査) |
| **提出候補モデル** | 提出は**班で1つの zip を両モード採点**なので、1つの系譜を育てる。`models/final/team25_tqc_sb3_env1_random.zip` を `sparkling-dew-15`（`pf8e9dqb`、Hardcore 55%）から `light-hill-20`（run `75glj5ue` の `best_model.zip`、Classic 100%＝5/5・Hardcore 65%＝13/20・goal_steps_mean 877.0）に更新済み |
| **各自やること** | ① Hardcore 完走率の底上げ（継続）: `configs/hardcore_next_run.yaml` の `resume_run_path` を `75glj5ue` に更新済み・`config_path` は引き続き `configs/hardcore_finetune.yaml`（vel_coef=0）。NaN対策込みの `src/train.py` で [notebooks/kaggle_hardcore_finetune.ipynb](notebooks/kaggle_hardcore_finetune.ipynb) を Save & Run All。② vel_coef の効果測定（Step 3 兼レポート素材）: [notebooks/kaggle_train_config.ipynb](notebooks/kaggle_train_config.ipynb) を Save & Run All |

Step が進んだら、気づいた人がこの表と更新日を PR で書き換えてください。

## 🗂️ リポジトリ構成

```
├── README.md            # この玄関ページ（現在地とドキュメント地図）
├── docs/                # 各種ドキュメント（上の地図から飛ぶ）
├── configs/             # チーム公式の学習設定（直接書き換えず PR で提案）
├── sweeps/              # チーム公式の sweep 定義（同上）
├── src/                 # 学習・評価・録画スクリプト（train.py / evaluate.py / ...）
├── notebooks/           # Kaggle で放置実行するためのノートブック
├── members/<番号>/       # 各メンバーの個人実験場（自由にコミット可）
├── models/final/        # 最終提出候補のモデルだけ置ける（他の成果物は Git 管理外）
└── requirements.txt     # 依存ライブラリ（セットアップは docs/GUIDE.md §2-5）
```
