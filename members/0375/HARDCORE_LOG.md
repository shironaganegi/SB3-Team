# Hardcore完走率メモ(0375個人)

チームの共有 `docs/BEST_CONFIG.md` / `README.md` / `configs/hardcore_next_run.yaml` は
今後変更せず、単独での反復(resume先・config・結果)はここに記録する。
理由: 共有ファイルを何度も書き換えると他メンバーの並行作業とコンフリクトしやすい
(2026-07-16 の PR #23 で実際にコンフリクトが発生した)。

現時点の提出候補(共有側): `models/final/team25_tqc_sb3_env1_random.zip`
= run `75glj5ue`(light-hill-20)の `best_model.zip`。Hardcore完走 65%(13/20)。

## 2026-07-22: 失敗モード分析(Step 1)

`75glj5ue` の `best_model.zip` を20シード(0..19)で評価し、失敗した7シードの
コース上の位置と直前の地形を特定した。

**手法上の注意:** `src/evaluate.py` の `evaluate()` は `env.reset(seed=seed)` の直後に
`run_episode()` 内でもう一度 `env.reset()`(seedなし)を呼んでいる。gymnasiumの
仕様上、これは「seed値がそのまま作るコース」ではなく「そこからもう1回分進んだ
コース」になる(結果は毎回同じなので65%という数字自体は再現性があるが、
`record_video.py --seed N` で同じNを指定しても採点で使われたのとは別のコースを
録画してしまう)。今回の分析では `evaluate()` と同じ二重resetを再現して、
実際に採点されたコースと同じものを見ている。詳細・対応要否は別途チームに報告予定
(共有の `src/evaluate.py` / `src/record_video.py` に関わる話なので、直すなら
PRが必要。今回のSoftFallPenalty計画とは別件として保留)。

**失敗7シードの内訳:**

| seed | steps | reward | 終了理由 | 直前の地形 |
|---|---|---|---|---|
| 1  | 269  | -40.93 | 転倒 | STUMP通過直後 |
| 4  | 138  | -82.08 | 転倒 | 障害物到達前(草地の起伏のみ) |
| 7  | 718  | 134.00 | 転倒 | PIT通過直後 |
| 10 | 2000 | 123.57 | **時間切れ(転倒せず)** | PIT付近で停滞 |
| 17 | 563  | 96.16  | 転倒 | PIT通過直後 |
| 18 | 357  | -22.70 | 転倒 | STUMP通過直後 |
| 19 | 252  | -43.52 | 転倒 | STUMP付近 |

**集計:** PIT関連 3件(うち1件は転倒ですらなく2000stepの時間切れ) / STUMP関連 3件 /
障害物と無関係な初期不安定 1件。STAIRS単独が直接原因の失敗は今回の7件には無かった。

**所感:** seed 10 の「転倒せず2000stepそのまま時間切れ」は、PITの手前で
方策が動けなくなっている(=挑戦して転ぶより、その場に留まる方をQ値上選んでいる)
ことを強く示唆する。これは検索で確認した「転倒ペナルティ-100が大きすぎて
探索に対して臆病になる」という仮説([ugurcanozalp/td3-sac-bipedal-walker-hardcore-v3](https://github.com/ugurcanozalp/td3-sac-bipedal-walker-hardcore-v3)、
[Nikolaj Goodgerのreward shaping実験](https://medium.com/@ngoodger_7766/proximal-policy-optimisation-in-pytorch-with-recurrent-models-edefb8a72180))
と整合する具体例。

**次:** `src/wrappers.py` に `SoftFallPenalty`(転倒ペナルティ-100→-10)を追加し、
`members/0375/configs/hardcore_softfall.yaml` で `75glj5ue` から追加学習する。

## 2026-07-22: SoftFallPenalty実装・実行準備(Step 2-3)

`SoftFallPenalty` は共有の `src/wrappers.py` / `src/train.py`(`CONTROL_KEYS` に
`fall_penalty` 追加)に実装し、PR [#24](https://github.com/shironaganegi/SB3-Team/pull/24)
でmainにマージ済み。`make_env` 単体テストとsmoke学習で、(a) `fall_penalty=-10`
指定時に転倒時報酬が-10になること、(b) 未指定時は従来と完全に同一の挙動である
こと、を確認済み。

`members/0375/configs/hardcore_softfall.yaml` を作成(`fall_penalty: -10`・
`total_timesteps: 800000`・`n_eval_episodes: 15`)。short smokeでも正常動作を確認済み。

**Kaggle実行手順:** `notebooks/kaggle_hardcore_finetune.ipynb` のセル4で以下を上書き
(共有の `configs/hardcore_next_run.yaml` は変更しない):
```python
RESUME_RUN_PATH = "sai3desuyo-/bipedal-timetrial/75glj5ue"
CONFIG_PATH = "members/0375/configs/hardcore_softfall.yaml"
```
Save & Run All。実測8〜10時間の見込み(total_timesteps=80万)。

**終了後にやること:** best_model.zip をW&Bから回収し、20シード(必要なら+10シード)で
採点再現。現候補(`75glj5ue`、Hardcore 65%)を上回ったら、この表に追記し、
`models/final/team25_tqc_sb3_env1_random.zip` の差し替えと `resume_run_path` の
更新(このconfig内のコメント、または新しいconfigファイル)を行う。

## 2026-07-23: 意図せず素の設定のまま追加学習(fall_penalty未適用)

Kaggleノートのセル4で `NameError: name 'resume_run_path' is not defined` が発生した際、
修正前に一度 `RESUME_RUN_PATH` / `CONFIG_PATH` を空のまま(＝共有の
`configs/hardcore_next_run.yaml` の既定値にフォールバック)実行してしまい、
`hardcore_softfall.yaml`(fall_penalty=-10)ではなく共有既定の
`configs/hardcore_finetune.yaml`(fall_penalty無し・total_timesteps=1,000,000)で
run `0fcv7lmb`(gallant-tree-22)が完走した。`75glj5ue` から+100万step
(300万→400万step相当、W&B上のnum_timesteps基準)。

20シード評価: **完走率65%(13/20)**、goal_steps_mean 973.9、reward_mean 208.1。
`75glj5ue` と完走率は同値で、fall_penaltyを変えない限りプラトーが動かないことの
傍証になった。

到達step数は`75glj5ue`より多い分だけ有利なので、この`0fcv7lmb`を次のresume元に
更新した(`members/0375/configs/hardcore_softfall.yaml` 参照)。次周こそ
`fall_penalty=-10`を実際に適用して回す。

**Kaggle実行手順(更新):**
```python
RESUME_RUN_PATH = "sai3desuyo-/bipedal-timetrial/0fcv7lmb"
CONFIG_PATH = "members/0375/configs/hardcore_softfall.yaml"
```
このノートのセル4は、`defaults = yaml.safe_load(...)` の直後に
`resume_run_path = RESUME_RUN_PATH or defaults["resume_run_path"]` と
`config_path = CONFIG_PATH or defaults["config_path"]` の2行が必須
(この2行を上の代入行と間違えて消してしまったのが今回のNameErrorの原因)。
セルを上書きする前に、この2行が残っているか必ず確認すること。
