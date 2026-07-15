# members/ — メンバー個人の実験フォルダ

ここは**各メンバーが自由にコミットしてよい個人領域**です。フォルダ名は自分のブランチ番号と対応しています（`member/0375` ブランチの人 → `members/0375/`）。

## なぜこのフォルダがあるのか

全員が共有の `configs/classic_baseline.yaml` や `sweeps/*.yaml` を直接書き換えると、main にマージするたびに同じ行の変更同士がぶつかってコンフリクトになります。そこで役割を分けます。

- **共有の `configs/`・`sweeps/`（リポジトリ直下）** … チーム公式のベースライン。**変更したいときは PR を出してチームで合意**してから反映する。
- **`members/<自分の番号>/`（ここ）** … 自分専用の実験場。**他人のフォルダは触らない**というルールさえ守れば、パラメータをいくら変えてコミットしてもコンフリクトは起きない。

## 使い方

1. 共有の config をベースに自分用のコピーを作る。

   ```bash
   cp configs/classic_baseline.yaml members/<自分の番号>/configs/my_lr_test.yaml
   ```

2. コピーしたファイルのパラメータ（`learning_rate` や `seed` など）を自由に書き換える。
3. 自分の config を指定して学習を回す。

   ```bash
   python src/train.py --config members/<自分の番号>/configs/my_lr_test.yaml
   ```

4. sweep 定義も同様に `members/<自分の番号>/sweeps/` にコピーして編集する。
5. 良い結果が出て「チームのベースラインにすべき」と思ったら、共有の `configs/` への反映を PR で提案する。

## 注意

- 学習の成果物（`models/`・`checkpoints/`・`results/` の zip など）はここには置きません。Git 管理外で、結果の共有は W&B のダッシュボードで行います。最終提出候補のモデルだけ、例外的に `models/final/` へコミットできます。
- config のファイル名は後で見返して分かるように（例: `lr7e4_seed3.yaml`）。
