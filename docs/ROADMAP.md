# 提出までの5ステップ（ロードマップ）

このページは「全体の進め方」「次に何をやるのか」に答える1枚です。**チームの現在地は [README](../README.md) の「📍 いまのフェーズ」表を見てください**。ほかの困りごとの入口も README のドキュメント地図にあります。

最終課題の採点ルール（[EVALUATION.md §1](EVALUATION.md#1-最終課題の採点ルール要点)）が確定したので、提出までの道のりを5段階に分けます。各段階は前の段階の結果を土台にします。

## Step 1: Basic のベースラインを作る

`configs/classic_baseline.yaml` で、複数人がそれぞれ別の `seed`（0〜4）を担当して回します。乱数の当たり外れが大きいため、複数シードで回すこと自体が探索になります（レポートの根拠にも使えます）。完了の目安は `evaluate.py` で完走が出始めること。BipedalWalker-v3 は TQC なら 100万ステップ前後で「解けた」（平均報酬300）に届くのが相場です。

## Step 2: ハイパラ探索（Step 1 と並行）

`sweeps/baseline_sweep.yaml` の sweep に Kaggle から全員で参加します（[EXPERIMENTS.md §3](EXPERIMENTS.md#3-kaggleコミットでの-sweep-の回し方)）。当たり値が見つかったら classic_baseline に反映して Step 1 を上回るのが目標です。公式 sweep の結果とベスト設定の選定理由は [BEST_CONFIG.md](BEST_CONFIG.md) にまとめてあります（レポートに転記できる形式）。

## Step 3: タイム短縮

`configs/classic_speed.yaml`（`vel_coef=2`）や `classic_fast.yaml` で報酬整形を乗せます。`vel_coef` を上げるほど平均ステップ数は減る方向に行きますが、上げすぎると転倒が増えて完走率が落ちるトレードオフがあります。baseline との比較は、そのままレポートの「結果」の章のグラフになります。

## Step 4: Hardcore への追加学習（カリキュラム学習）

採点は Basic / Hardcore の両モードで行われ、**Hardcore も完走できれば「平均ステップ数」（=速さ）で採点される**ため、Hardcore は完走して終わりではありません。2段階で進めます。

**(4a) まず完走させる。** Step 1〜3 のベストモデルのチェックポイントから Hardcore で追加学習します:

```bash
python src/train.py --config configs/hardcore_finetune.yaml --resume checkpoints/<ベストのzip>
```

Hardcore をゼロから学習するのは CPU の予算ではほぼ無理ですが、観測・行動の次元は Basic と同一なので、「歩ける」モデルに障害物対応だけ追加学習させるのが定石です。最初の目安は、Hardcore の評価で `reward_mean` が「その場で転ぶ」水準（約 -100）を明確に上回ること。その先の目標は完走が出ることです。

**(4b) 完走が出たら、Hardcore でもタイム短縮。** やり方は Step 3 と同じ発想です。共有 config `configs/hardcore_finetune_velcoef.yaml`（`vel_coef=1`。まだ完走率が低いうちはいきなり大きくせず、崩れなければ次の周で上げる）を使うか、より大きく振りたい場合は `members/<自分の番号>/configs/` にコピーして値を調整し、完走率が落ちていないかを [EVALUATION.md §2](EVALUATION.md#2-共通評価プロトコル) の採点再現コマンド（Hardcore側）で確認しながら詰めます。Basic と同様、速さを欲張って完走率を落とすと本番で「平均Reward採点」側に落ちて大損するので、**完走率優先**は変わりません。

## Step 5: 提出モデルの選抜

候補モデルを [EVALUATION.md §2](EVALUATION.md#2-共通評価プロトコル) の「採点再現コマンド」で両モード測定し、課題の採点式（完走なら平均ステップ最小、非完走なら平均Reward最大）で1つ選び、班で1つの zip として Classroom フォームへ提出します。
