"""TQC（sb3-contrib）を CPU で学習・保存するスクリプト（W&B sweep 対応）。

このスクリプトがやること:
  1. YAML 設定ファイル（configs/*.yaml）を読み込む
  2. その設定で BipedalWalker-v3 の学習環境と評価環境を作る
  3. TQC で学習し、途中でベストモデルとチェックポイントを保存する
  4. 最後に最終モデルを命名規則に従って models/ に保存する

実行例:
  # まず配管確認（数千ステップで一周回す）
  python src/train.py --config configs/smoke.yaml

  # 本番の baseline 学習（vel_coef=0 の素の TQC）
  python src/train.py --config configs/classic_baseline.yaml

  # チェックポイントから再開する
  python src/train.py --config configs/classic_baseline.yaml --resume checkpoints/xxx.zip

【どこを編集する？】
  学習の設定（ステップ数・ハイパラ・速度ボーナス等）は YAML 側で変えます
  （共有 configs/ は直接書き換えず、members/<自分の番号>/configs/ にコピーして編集）。
  このスクリプト自体を書き換える必要は普段ありません。TQC のハイパラ
  （tau や gamma など）を新しく試したいときも、YAML に1行足すだけで
  自動的に TQC へ渡ります（下の TQC_PARAM_NAMES を参照）。
"""

import argparse
import inspect
import os

import yaml
import gymnasium as gym
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import (
    CallbackList,
    CheckpointCallback,
    EvalCallback,
)
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.utils import set_random_seed
from sb3_contrib import TQC

from wrappers import SpeedReward


# YAML の項目は次の2種類に自動で振り分けられます。
#
#   1. TQC のハイパラ … TQC のコンストラクタ引数と同じ名前なら、そのまま TQC へ
#      渡されます。名前の一覧は TQC の実物の定義から自動で取るので、新しいハイパラ
#      （tau・gamma・batch_size など）を試したいときは YAML に1行足すだけでOK。
#      このファイルの編集は不要です。
#   2. 学習の制御用キー … total_timesteps や vel_coef など、このスクリプト自身が
#      読む項目。下の CONTROL_KEYS に列挙してあります。
#
# どちらにも当てはまらないキーは打ち間違いの可能性が高いので、実行時に
# [warn] で知らせます（エラーにはせず学習は続けます）。

# TQC へは policy・env などを別途明示的に渡すので、YAML から受け取る対象から外す
_EXPLICITLY_PASSED = {
    "self", "policy", "env", "device", "verbose",
    "seed", "tensorboard_log", "_init_setup_model",
}
TQC_PARAM_NAMES = set(inspect.signature(TQC.__init__).parameters) - _EXPLICITLY_PASSED

# このスクリプト自身が読む「学習の制御用」キー
CONTROL_KEYS = {
    "env_id", "vel_coef", "time_penalty", "seed", "total_timesteps",
    "eval_freq", "n_eval_episodes", "checkpoint_freq",
    "use_wandb", "wandb_project", "wandb_entity",
}


def warn_unknown_keys(config):
    """TQC にも学習制御にも当てはまらないキーを警告する（打ち間違い対策）。

    W&B が内部で足すメタ情報（アンダースコア始まり）は対象外。
    """
    for key in config:
        if key.startswith("_"):
            continue
        if key not in TQC_PARAM_NAMES and key not in CONTROL_KEYS:
            print(
                f"[warn] 設定キー '{key}' は TQC のハイパラにも学習制御用キーにも"
                f"見当たりません。打ち間違いではないですか？（無視して続行します）"
            )


def make_env(env_id, vel_coef, seed, training, time_penalty=0.0):
    """1つの環境を作って返す。

    ラップの順番:
      gym.make → Monitor（必ず）→ （学習用かつ vel_coef>0 or time_penalty>0 のときだけ）SpeedReward

    training の意味:
      True  … 学習用の環境。vel_coef>0 or time_penalty>0 なら SpeedReward を被せる。
      False … 評価用の環境。常に素の環境（SpeedReward を被せない）。
    """
    env = gym.make(env_id)
    env = Monitor(env)  # エピソード報酬・長さを記録する標準ラッパー
    if training and (vel_coef > 0 or time_penalty > 0):
        env = SpeedReward(env, vel_coef=vel_coef, time_penalty=time_penalty)
    env.reset(seed=seed)
    return env


def load_config(path):
    """YAML 設定ファイルを辞書として読み込む。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    # ----------------------------------------------------------------------
    # 1. コマンドライン引数
    # ----------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Train TQC on BipedalWalker (CPU)")
    parser.add_argument(
        "--config",
        default="configs/classic_baseline.yaml",
        help="使う YAML 設定ファイル。sweep ではこれを既定値の土台にする。",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="チェックポイント(.zip)から学習を再開したい場合のパス。",
    )
    # W&B sweep の agent は --vel_coef=... のような引数を勝手に付けてきます。
    # それらは argparse で受けず（parse_known_args で無視し）、後で wandb.config から
    # 取り込みます。なので未知の引数が来てもエラーにしません。
    args, _unknown = parser.parse_known_args()

    config = load_config(args.config)

    # ----------------------------------------------------------------------
    # 2. W&B を使うか判定
    # ----------------------------------------------------------------------
    # 次のどちらかなら W&B を有効化する:
    #   - config に use_wandb: true がある
    #   - sweep の agent から起動された（環境変数 WANDB_SWEEP_ID が立っている）
    is_sweep = os.environ.get("WANDB_SWEEP_ID") is not None
    use_wandb = bool(config.get("use_wandb", False)) or is_sweep

    run = None
    if use_wandb:
        import wandb

        run = wandb.init(
            project=config.get("wandb_project", "bipedal-timetrial"),
            entity=config.get("wandb_entity") or None,
            config=config,            # YAML の既定値をまず土台として渡す
            sync_tensorboard=True,
            save_code=True,
        )
        # sweep 経由なら wandb.config に vel_coef / seed / learning_rate などの
        # 「今回試す値」が入ってきます。それを YAML 既定値の上に上書きします
        # （= sweep が指定した値を優先）。
        for key in dict(wandb.config).keys():
            config[key] = wandb.config[key]

    # ----------------------------------------------------------------------
    # 3. 設定値の取り出し
    # ----------------------------------------------------------------------
    warn_unknown_keys(config)  # 打ち間違いキーがあればここで知らせる

    env_id = config.get("env_id", "BipedalWalker-v3")
    vel_coef = float(config.get("vel_coef", 0))
    time_penalty = float(config.get("time_penalty", 0))
    seed = int(config.get("seed", 0))
    total_timesteps = int(config.get("total_timesteps", 4000))

    # time_penalty を使った学習は、成果物のファイル名でも区別できるようにする
    # （README §9 の命名規則。0 のときは従来どおりタグなし）
    tp_tag = f"_timepen{time_penalty:g}" if time_penalty > 0 else ""

    set_random_seed(seed)  # 再現性のため乱数シードを固定

    # ----------------------------------------------------------------------
    # 4. 環境を用意
    # ----------------------------------------------------------------------
    # 学習用: vel_coef>0 or time_penalty>0 なら SpeedReward あり。
    # 評価用: 常に素の環境。学習用とシードをずらして（+10000）汎化を見る。
    train_env = make_env(env_id, vel_coef, seed, training=True, time_penalty=time_penalty)
    eval_env = make_env(env_id, 0.0, seed + 10000, training=False)

    # ----------------------------------------------------------------------
    # 5. 出力先ディレクトリ（.gitignore 済み。GitHub には上がらない）
    # ----------------------------------------------------------------------
    os.makedirs("models", exist_ok=True)        # ベストモデル・最終モデル
    os.makedirs("checkpoints", exist_ok=True)   # 再開用チェックポイント
    tensorboard_log = f"runs/{run.id}" if run is not None else None

    # ----------------------------------------------------------------------
    # 6. モデルを作る or 再開する
    # ----------------------------------------------------------------------
    # YAML から TQC へ渡すハイパラだけを抜き出す（名前が一致するものは全部渡る）
    tqc_kwargs = {k: config[k] for k in config if k in TQC_PARAM_NAMES}

    if args.resume:
        print(f"[resume] {args.resume} から学習を再開します")
        model = TQC.load(
            args.resume,
            env=train_env,
            device="cpu",
            tensorboard_log=tensorboard_log,
        )
        reset_num_timesteps = False  # ステップ数を引き継ぐ
    else:
        model = TQC(
            "MlpPolicy",
            train_env,
            device="cpu",            # GPU は使わない。全員 CPU で回す方針。
            seed=seed,
            verbose=1,
            tensorboard_log=tensorboard_log,
            **tqc_kwargs,
        )
        reset_num_timesteps = True

    # ----------------------------------------------------------------------
    # 7. コールバック（学習中に定期的に走る処理）
    # ----------------------------------------------------------------------
    callbacks = []

    # (a) 評価コールバック: 一定ステップごとに素の環境で deterministic 評価し、
    #     成績が良ければ models/best_model.zip を更新する。
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="models",
        log_path="results",
        eval_freq=int(config.get("eval_freq", 10000)),
        n_eval_episodes=int(config.get("n_eval_episodes", 10)),
        deterministic=True,
        render=False,
    )
    callbacks.append(eval_callback)

    # (b) チェックポイント: 一定ステップごとに checkpoints/ へ保存（再開用）。
    checkpoint_callback = CheckpointCallback(
        save_freq=int(config.get("checkpoint_freq", 50000)),
        save_path="checkpoints",
        name_prefix=f"tqc_velcoef{int(vel_coef)}{tp_tag}_seed{seed}",
    )
    callbacks.append(checkpoint_callback)

    # (c) W&B を使うときだけ、学習ログを W&B に送るコールバックを足す。
    if run is not None:
        from wandb.integration.sb3 import WandbCallback

        callbacks.append(
            WandbCallback(
                gradient_save_freq=0,
                model_save_path=f"runs/{run.id}/model",
                verbose=2,
            )
        )

    # ----------------------------------------------------------------------
    # 8. 学習本体
    # ----------------------------------------------------------------------
    model.learn(
        total_timesteps=total_timesteps,
        callback=CallbackList(callbacks),
        reset_num_timesteps=reset_num_timesteps,
        progress_bar=False,
    )

    # ----------------------------------------------------------------------
    # 9. 最終モデルを命名規則で保存
    # ----------------------------------------------------------------------
    # ファイル名に入れる評価報酬:
    #   基本は EvalCallback が見つけたベスト平均報酬を使う。
    #   一度も評価が走らなかった（= -inf のまま）場合だけ、最後に短く評価する。
    eval_reward = eval_callback.best_mean_reward
    if eval_reward == -float("inf"):
        eval_reward, _ = evaluate_policy(
            model, eval_env, n_eval_episodes=5, deterministic=True
        )

    steps = model.num_timesteps
    # 例: bipedalwalker_tqc_velcoef0_seed0_1000000_312.zip
    #     velcoef=速度ボーナス係数 / (timepen=時間ペナルティ、使ったときだけ) /
    #     seed=シード / steps=総ステップ / 末尾=評価報酬
    name = (
        f"bipedalwalker_tqc_velcoef{int(vel_coef)}{tp_tag}_seed{seed}"
        f"_{steps}_{int(round(eval_reward))}"
    )
    save_path = os.path.join("models", name)
    model.save(save_path)
    print(f"[saved] {save_path}.zip  (eval_reward={eval_reward:.1f})")

    # ----------------------------------------------------------------------
    # 10. 後片付け
    # ----------------------------------------------------------------------
    train_env.close()
    eval_env.close()
    if run is not None:
        run.finish()


if __name__ == "__main__":
    main()
