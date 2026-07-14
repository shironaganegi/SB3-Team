# ベースライン sweep の結果とベスト設定の選定理由

最終レポート（個人レポートの実験章）にそのまま転記できるよう、公式 sweep の結果・選定基準・選定理由をまとめたものです。数値はすべて W&B の記録から取得しています（2026-07-11 時点）。

## 1. 実験の目的と設計

**目的:** 速度チューニング（`vel_coef`）に入る前に、「素の報酬で安定して完走できる」ベースライン方策と、その学習率（`learning_rate`）の当たり範囲を確定させる（README [§7](../README.md#7-進め方提出までの5ステップ) Step 1〜2）。

**設計**（[sweeps/baseline_sweep.yaml](../sweeps/baseline_sweep.yaml)）:

| 項目 | 値 | 理由 |
|---|---|---|
| アルゴリズム | TQC（sb3-contrib） | 採用理由は [docs/ALGORITHM.md](ALGORITHM.md) |
| 探索方法 | ベイズ最適化（`method: bayes`） | 少ない試行数で当たり領域に寄せるため |
| `learning_rate` | 1e-4 〜 1e-3（対数一様） | TQC の BipedalWalker 定番値 7.3e-4 を挟む1桁の範囲 |
| `seed` | {0, 1, 2} | 乱数の当たり外れと分離するため複数シードで確認 |
| `vel_coef` | 0 固定 | baseline 専念（報酬整形なし＝素の環境と同じ報酬で学習） |
| 学習ステップ | 100万 | TQC が BipedalWalker を「解く」相場（README §7 Step 1） |
| 代理指標 | `eval/mean_reward`（10エピソード平均） | 探索の目安。**最終選抜には使わない**（§3参照） |

実行は Kaggle CPU セッション（[notebooks/kaggle_commit.ipynb](../notebooks/kaggle_commit.ipynb)）で分担した。

## 2. 結果（sweep `ksgu0vds`・全9 run）

eval/mean_reward の降順。crashed はセッション上限（約12時間）による途中終了で、学習自体の失敗ではない（詳細は §5）。

| run | 状態 | learning_rate | seed | eval報酬 | 評価エピソード長 | 到達ステップ |
|---|---|---|---|---|---|---|
| **drawn-sweep-5** | **finished** | **4.43e-4** | **1** | **336.2** | **576.6** | 100万 |
| peach-sweep-7 | crashed | 2.08e-4 | 2 | 336.1 | 581.8 | 95.1万 |
| different-sweep-1 | finished | 6.60e-4 | 2 | 335.4 | 574.6 | 100万 |
| dazzling-sweep-3 | finished | 1.33e-4 | 2 | 334.7 | 594.4 | 100万 |
| dark-sweep-4 | finished | 4.99e-4 | 1 | 334.4 | 582.5 | 100万 |
| rosy-sweep-2 | finished | 9.47e-4 | 1 | 332.4 | 577.1 | 100万 |
| hopeful-sweep-8 | crashed | 2.04e-4 | 2 | 331.5 | 648.1 | 48.8万 |
| atomic-sweep-9 | crashed | 1.08e-4 | 0 | 316.5 | 725.8 | 28.7万 |
| elated-sweep-6 | crashed | 5.77e-4 | 2 | 211.6 | 559.4 | 17.1万 |

**読み取れること:**

- 100万ステップ到達した6本（finished 5本 + 95万まで進んだ peach-sweep-7）は**すべて eval 報酬 331〜336** に収束しており、探索した学習率の範囲（1e-4〜1e-3）全体で BipedalWalker-v3 は安定して「解けた」（平均報酬300超）。つまり **TQC はこの課題に対して学習率にかなり頑健**。
- 学習率による差が出るのは**収束の速さ**で、crashed の3本（途中経過）を見ると、小さい学習率（1.08e-4）は 28.7万ステップ時点で報酬 316.5 まで来ている一方、エピソード長がまだ 725.8 と長い（歩けるが遅い）。
- 評価エピソード長（=速さの代理値）は最終的に 575〜595 に集まり、設定間の差は小さい。**速さを大きく縮めるにはハイパラではなく報酬設計（`vel_coef`）が必要**という Step 3 の前提が裏付けられた。

## 3. 選定基準

チームの取り決め（README [§6](../README.md#6-共通評価プロトコル)）どおり:

1. sweep の `eval/mean_reward` は**探索用の代理指標**であり、最終判断には使わない。
2. 最終選抜は `src/evaluate.py` による**採点ルール再現**（素の環境・deterministic・シード5種×1エピソード = ランダムコース5回の平均）で行う。
3. 優先順位は **完走率 → 完走時の平均ステップ数 → 平均報酬**（採点式と同じ）。
4. 追加学習（Hardcore への resume）の起点に使うため、**モデルファイル(zip)が回収できる run** であること（crashed run は W&B に model.zip が残らない）。

## 4. 選定結果: drawn-sweep-5（lr 4.43e-4 / seed 1）

sweep 上位のうち、**完走モデルの zip が W&B に残っている finished run の中で eval 報酬が最大**の drawn-sweep-5 を選定した。手元での採点再現結果（`python src/evaluate.py <model.zip> --seeds 0 1 2 3 4 --episodes 1`）:

| 指標 | 値 |
|---|---|
| 完走率（Basic） | **80%（5コース中4回完走）** |
| 完走時の平均ゴールステップ | **576.8**（中央値 577.0） |
| 全エピソード平均報酬 | 296.3 |

2位の peach-sweep-7（eval 336.1）はほぼ同成績だが、12時間上限で crashed したためモデルが回収できず、候補から外した。

**このモデルの位置づけ:**

- Hardcore 追加学習（README §7 Step 4a/4b、[notebooks/kaggle_hardcore_finetune.ipynb](../notebooks/kaggle_hardcore_finetune.ipynb)）の起点。
  - 1周目（run `an3wpjb5` / chocolate-yogurt-12、vel_coef=0、+100万ステップ）: Hardcore eval 報酬 -71→160・採点再現 完走0/5・reward_mean 61.2、Classic 採点は完走 5/5・goal_steps_mean 744.6。
  - 2周目（run `pf8e9dqb` / sparkling-dew-15、vel_coef=0継続、+100万ステップ）: Hardcore 採点再現で**初めて完走（3/5）**・goal_steps_mean 847.0・reward_mean 177.0、Classic は完走 5/5・goal_steps_mean 766.0（悪化なし、誤差範囲）。Step 4a のゲート（完走）達成（2026-07-13 時点）。
  - 3周目（Step 4b、進行中）: 完走が取れたので `configs/hardcore_finetune_velcoef.yaml`（vel_coef=1）に切り替えて速度報酬を導入。ノートの `RESUME_RUN_PATH` 既定値は `pf8e9dqb`、`CONFIG_PATH` 既定値はこの velcoef config。
- Classic 速度チューニング（Step 3）のベース設定。学習率は当たり値 4.43e-4 を引き継ぎ、`vel_coef` を振る。
- 完走率 80% はまだ改善余地がある（5回中1回転倒）。速度チューニングと並行して、失敗コースの観察（動画）から原因を特定する。

## 5. 付記: crashed run の原因

crashed 4本はすべて Kaggle セッションの実行時間上限（約12時間）による強制終了で、各セッションの「finished + crashed の実行時間合計」が約11時間59分に一致することから確認した（コード側の異常ではない）。1 run に実測 6〜10 時間かかるため、ノートブックの `N_RUNS` は 1 に固定した（README [§5](../README.md#5-kaggleコミットでの-sweep-の回し方)）。

## 6. 再現方法

```bash
# ベストモデルの取得（wandb login 済みの環境で）
python -c "
import wandb
run = wandb.Api().run('sai3desuyo-/bipedal-timetrial/xsrplaip')
[f for f in run.files() if f.name == 'model.zip'][0].download(root='models', replace=True)
"

# 採点ルール再現（Basic / Hardcore）
python src/evaluate.py models/model.zip --seeds 0 1 2 3 4 --episodes 1
python src/evaluate.py models/model.zip --env-id BipedalWalkerHardcore-v3 --seeds 0 1 2 3 4 --episodes 1

# 走りの動画を作る
python src/record_video.py models/model.zip --seed 1
```
