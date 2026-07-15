# ベースライン sweep の結果とベスト設定の選定理由

最終レポート（個人レポートの実験章）にそのまま転記できるよう、公式 sweep の結果・選定基準・選定理由をまとめたものです。数値はすべて W&B の記録から取得しています（2026-07-11 時点）。

## 1. 実験の目的と設計

**目的:** 速度チューニング（`vel_coef`）に入る前に、「素の報酬で安定して完走できる」ベースライン方策と、その学習率（`learning_rate`）の当たり範囲を確定させる（[ROADMAP.md](ROADMAP.md) Step 1〜2）。

**設計**（[sweeps/baseline_sweep.yaml](../sweeps/baseline_sweep.yaml)）:

| 項目 | 値 | 理由 |
|---|---|---|
| アルゴリズム | TQC（sb3-contrib） | 採用理由は [docs/ALGORITHM.md](ALGORITHM.md) |
| 探索方法 | ベイズ最適化（`method: bayes`） | 少ない試行数で当たり領域に寄せるため |
| `learning_rate` | 1e-4 〜 1e-3（対数一様） | TQC の BipedalWalker 定番値 7.3e-4 を挟む1桁の範囲 |
| `seed` | {0, 1, 2} | 乱数の当たり外れと分離するため複数シードで確認 |
| `vel_coef` | 0 固定 | baseline 専念（報酬整形なし＝素の環境と同じ報酬で学習） |
| 学習ステップ | 100万 | TQC が BipedalWalker を「解く」相場（[ROADMAP.md](ROADMAP.md) Step 1） |
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

チームの取り決め（[EVALUATION.md §2](EVALUATION.md#2-共通評価プロトコル)）どおり:

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

- Hardcore 追加学習（[ROADMAP.md](ROADMAP.md) Step 4a/4b、[notebooks/kaggle_hardcore_finetune.ipynb](../notebooks/kaggle_hardcore_finetune.ipynb)）の起点。
  - 1周目（run `an3wpjb5` / chocolate-yogurt-12、vel_coef=0、+100万ステップ）: Hardcore eval 報酬 -71→160・採点再現 完走0/5・reward_mean 61.2、Classic 採点は完走 5/5・goal_steps_mean 744.6。
  - 2周目（run `pf8e9dqb` / sparkling-dew-15、vel_coef=0継続、+100万ステップ）: Hardcore 採点再現で**初めて完走（3/5）**・goal_steps_mean 847.0・reward_mean 177.0、Classic は完走 5/5・goal_steps_mean 766.0（悪化なし、誤差範囲）。Step 4a のゲート（完走）達成（2026-07-13 時点）。
  - 3周目（run `0chynjib` / absurd-wildflower-17、vel_coef=1、+100万ステップ、2026-07-14完了）: `configs/hardcore_finetune_velcoef.yaml` に切り替えて速度報酬を導入したが、学習曲線が非常に不安定（raw評価で -215〜282 を乱高下、run終了時点はたまたま谷の93）だった。**resume の起点として採用せず**、[§7](#7-追記2026-07-15-hardcore実機テストの調査) の対応に切り替えた。
- Classic 速度チューニング（Step 3）のベース設定。学習率は当たり値 4.43e-4 を引き継ぎ、`vel_coef` を振る。
- 完走率 80% はまだ改善余地がある（5回中1回転倒）。速度チューニングと並行して、失敗コースの観察（動画）から原因を特定する。

## 5. 付記: crashed run の原因

crashed 4本はすべて Kaggle セッションの実行時間上限（約12時間）による強制終了で、各セッションの「finished + crashed の実行時間合計」が約11時間59分に一致することから確認した（コード側の異常ではない）。1 run に実測 6〜10 時間かかるため、ノートブックの `N_RUNS` は 1 に固定した（[EXPERIMENTS.md §3](EXPERIMENTS.md#3-kaggleコミットでの-sweep-の回し方)）。

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

## 7. 追記（2026-07-15）: Hardcore実機テストの調査

**きっかけ:** 先生の評価サイトで提出物（`models/final/team25_tqc_sb3_env1_random.zip`）を走らせたところ、Classic は14秒で完走したが Hardcore は3秒で転倒した。

**調査したこと:**

1. **提出物の由来をハッシュ照合で確認。** `team25_tqc_sb3_env1_random.zip` は本リポジトリの命名規則に沿っていない（提出用に手動リネームされたファイル）ため、直前に完了していた Step 4b の run `0chynjib`（vel_coef=1）由来だと最初は推測したが、MD5 を比較したところ **`pf8e9dqb`（sparkling-dew-15、vel_coef=0）の model.zip と完全一致**した。3周目（vel_coef=1）はまだ提出物に反映されていない。
2. **Hardcore 完走率を20シードで測り直した。** 従来の5シード（3/5=60%）は誤差が大きいため、`--seeds 0 1 ... 19 --episodes 1` で再測定したところ **11/20（55%）・goal_steps_mean 842.2・reward_mean 183.5** と、5シードの結果とほぼ一致する水準だった。3秒転倒は、モデルの劣化やバグではなく、**約45%の確率で起きる想定内のランダムコース失敗**である可能性が高い（ユーザーの「コースがランダムだから」という見立ては妥当）。
3. **W&B のrun履歴から、資産管理上の問題を発見。** `src/train.py` の `WandbCallback`（[src/train.py:260](../src/train.py#L260)）は `model_save_freq` を指定していなかったため、学習終了時点の最終モデルしか W&B にアップロードされていなかった。3周目の run `0chynjib` は raw評価で -215〜282 を乱高下しており、run終了時点（global_step=4,000,000）はたまたま谷の93（ピークは global_step=3,430,000 時点の282）。`EvalCallback` が管理するそのrunのベストモデル（`models/best_model.zip`）は Kaggle セッション内にしか残らず、W&B にも上がっていなかったため、**ピーク時点のモデルは実質的に回収不能**になっていた。

**対応:**

- `src/train.py` を修正し、学習終了時に `models/best_model.zip` も `wandb.save()` で明示的に W&B へアップロードするようにした。以後の run は最終モデルとベストモデルの両方が残る。
- `configs/hardcore_next_run.yaml` の次周設定を、vel_coef=1（速度チューニング）から vel_coef=0（`configs/hardcore_finetune.yaml`）に戻した。resume 元の `pf8e9dqb` 自体の完走率がまだ55%であり、速度を追う前に完走率を上げるべき局面と判断したため。
- 提出候補（`pf8e9dqb`）は変更なし。現時点でこれを上回る確認済みモデルはない。

## 8. 追記（2026-07-15）: mild-lion-18 の NaN クラッシュ調査

**きっかけ:** §7 の対応後に回した Hardcore 追加学習の4周目（run `jp5jwddi` / mild-lion-18、`pf8e9dqb` から vel_coef=0 で resume）が crashed になった。

**調査したこと:**

1. **12時間上限ではなかった。** run の実行時間は約4.5時間（16,203秒）、進捗は 3,686,897 step（100万中68.7万）。セッション上限による強制終了なら約12時間で切られるはずで、パターンが違う。
2. **output.log の末尾にトレースバックが残っていた。** `ValueError: Expected parameter scale ... found invalid values: tensor([[nan, ...]])`。直前の学習ログで `train/std = 2.72e+14`（log_std ≈ 33）まで膨らんでおり、gSDE（`use_sde: true`）の探索ノイズパラメータ log_std が発散 → `exp(log_std)` が桁あふれで NaN → 分布の生成で例外、という数値爆発クラッシュだった。SB3 の gSDE では既知の失敗モードで、公式の対策は std 計算を expln 方式（`use_expln=True`）に切り替えること。expln は log_std≤0 の範囲では exp と完全に同一の値を返すため、正常な学習挙動は変わらない。
3. **学習自体はクラッシュまで好調だった。** eval/mean_reward は resume 直後の -54（リプレイバッファが空になるための一時的な落ち込み）から回復し、3.65M step 時点でピーク **243.5** に到達（resume 元 `pf8e9dqb` の終了時 122 を大幅に上回る）。つまり「vel_coef=0 のまま完走率を底上げする」という §7 の方針自体は機能していた。
4. **ピークのモデルは回収できなかった。** §7 で入れた best_model.zip のアップロードは**学習が正常終了したときにしか実行されない**ため、途中クラッシュした今回の run からは model.zip も best_model.zip も回収できず、ピーク 243.5 のモデルは消失した。§7 と同種の資産管理バグが「クラッシュ時」というより悪い形で残っていたことになる。

**対応（src/train.py に3点）:**

- **発散の予防:** モデルの新規作成・resume の直後に gSDE の `use_expln` を一律で有効化（`enable_expln()`）。resume では YAML のハイパラが反映されないため、config ではなくコード側で常時有効にする。
- **墜落の回避:** log_std に NaN/inf を検知したら学習を安全に止めるコールバック（`StopOnNonFiniteCallback`）を追加。万一発散しても run は「正常終了」になり、最終保存・アップロード・動画作成まで走る。
- **資産回収の耐クラッシュ化:** EvalCallback がベストモデルを更新するたびに、その場で W&B へアップロードするコールバック（`UploadBestToWandbCallback`）を追加。以後は run がどの理由で途中終了しても、その時点までのベストは必ず W&B に残る。

**次の一手:** `configs/hardcore_next_run.yaml` は変更なし（`pf8e9dqb` 起点・vel_coef=0）。この対策を main に取り込んだうえで、同じ周を Kaggle でやり直す。提出候補は引き続き `pf8e9dqb`（今回の run で 243.5 が出た事実は、この周のやり直しで上回れる見込みが高いことを示唆している）。

**補足: 暴走の直前に見えていた予兆（次周で観察すべきポイント）**

output.log を遡ると、`std`（log_std を `exp` した値）は学習の大半で 0.018〜0.04 前後に安定していたが、クラッシュ直前のごく短い区間（数千ステップ）で `0.03 → 0.2 → 4 → 125 → 8,000 → 2.7×10^14` と、ほぼ毎ログで2〜3倍に増える指数関数的な暴走に入っていた。

さらにその暴走が始まる約1.5万ステップ前から、`actor_loss` が それまでの +0.3〜+2.7 程度から **-5〜-7 まで一方向に下がり続けていた**一方、`critic_loss`（TDエラー）はむしろ低いまま安定していた。これは純粋なランダムノイズというより、**critic（Q値の推定）が一方向に偏り始めていた可能性**を示す手がかりで、TQC が抑えようとしている過大評価バイアスがこの局面で顕在化しかけていたのかもしれない（未検証の仮説）。

`use_expln` は log_std が発散しても数値として爆発しないよう頭打ちにする対策であり、この「actor_loss が一方向にずれ続ける」という根っこの不安定さ自体は直していない。**次周以降、W&B の `train/actor_loss` が同じように大きくマイナス方向へずれ続ける兆候が出ないか観察してほしい。** 同じパターンが再発するようなら、クラッシュの有無に関わらず方策の質が不安定になりかけているサインとして調べる価値があり、レポート④（学習の取り組み）の考察素材にもなる。
