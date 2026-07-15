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

## 📍 いまのフェーズ（2026-07-15 更新）

| 項目 | 現在 |
|---|---|
| **いまの段階** | [docs/ROADMAP.md](docs/ROADMAP.md) の **Step 4a 完了 → Step 4b（Hardcore に速度報酬を導入）は仕切り直し**。先生の評価サイトの実機テストで Classic は14秒完走、Hardcore は3秒転倒。調査の結果、提出物は `sparkling-dew-15`（run `pf8e9dqb`、vel_coef=0）由来で、Hardcore 完走率は20シード再測定で **11/20（55%）**。3秒転倒は「約45%の確率で起きる想定内のランダムコース失敗」。ただし55%はまだ低く、速度（vel_coef=1）を追う前に完走率を底上げすべき局面。直近の vel_coef=1 の run `0chynjib` は学習曲線が不安定で **resume 起点にしない**。あわせて best_model 未回収の資産管理バグを `src/train.py` で修正済み。調査の詳細は [docs/BEST_CONFIG.md §7](docs/BEST_CONFIG.md#7-追記2026-07-15-hardcore実機テストの調査) |
| **提出候補モデル** | 提出は**班で1つの zip を両モード採点**なので、1つの系譜を育てる。現候補は `sparkling-dew-15`（run `pf8e9dqb`。Classic 5/5 ＋ Hardcore 11/20=55%・reward_mean 183.5） |
| **各自やること** | ① Hardcore 完走率の底上げ: `configs/hardcore_next_run.yaml` は `pf8e9dqb` を resume 元に vel_coef=0 へ戻し済み。[notebooks/kaggle_hardcore_finetune.ipynb](notebooks/kaggle_hardcore_finetune.ipynb) を Save & Run All。② vel_coef の効果測定（Step 3 兼レポート素材）: [notebooks/kaggle_train_config.ipynb](notebooks/kaggle_train_config.ipynb) を Save & Run All |

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
