"""YAMLで設定したTQC（sb3-contrib）をCPUで学習・保存するスクリプト（W&B sweep対応）。"""

import argparse
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


# YAMLからTQCコンストラクタへ渡すハイパラのキー一覧（これ以外は学習制御用）
TQC_HYPERPARAM_KEYS = [
    "learning_starts",
    "batch_size",
    "buffer_size",
    "learning_rate",
    "use_sde",
    "train_freq",
    "gradient_steps",
    "gamma",
    "tau",
]


def make_env(env_id, vel_coef, seed, training):
    """環境を生成する。

    Monitorで必ずラップし、training=True かつ vel_coef>0 のときだけ
    SpeedReward を被せる。評価用（training=False）は常に素の環境。
    """
    env = gym.make(env_id)
    env = Monitor(env)
    if training and vel_coef > 0:
        env = SpeedReward(env, vel_coef=vel_coef)
    env.reset(seed=seed)
    return env


def load_config(path):
    """YAML設定を辞書として読み込む。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Train TQC on BipedalWalker (CPU)")
    parser.add_argument(
        "--config",
        default="configs/classic_baseline.yaml",
        help="YAML設定ファイル。sweepでは既定値の土台として使う。",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="チェックポイント(.zip)から学習を再開する場合のパス。",
    )
    # sweep agentが付ける --vel_coef=... 等の未知引数は無視し、wandb.config から取り込む
    args, _unknown = parser.parse_known_args()

    config = load_config(args.config)

    # --- W&B を使うか判定（configのフラグ、またはsweep起動時のenv varで有効化）---
    is_sweep = os.environ.get("WANDB_SWEEP_ID") is not None
    use_wandb = bool(config.get("use_wandb", False)) or is_sweep

    run = None
    if use_wandb:
        import wandb

        run = wandb.init(
            project=config.get("wandb_project", "bipedal-timetrial"),
            entity=config.get("wandb_entity") or None,
            config=config,            # YAML既定値を土台として渡す
            sync_tensorboard=True,
            save_code=True,
        )
        # sweep agent経由ならwandb.configにvel_coef/seed/learning_rate等の上書きが入る。
        # それをYAML既定値の上にマージする（sweepの値が優先）。
        for key in dict(wandb.config).keys():
            config[key] = wandb.config[key]

    # --- 設定値の取り出し ---
    env_id = config.get("env_id", "BipedalWalker-v3")
    vel_coef = float(config.get("vel_coef", 0))
    seed = int(config.get("seed", 0))
    total_timesteps = int(config.get("total_timesteps", 4000))

    set_random_seed(seed)

    # --- 環境（学習用はvel_coef>0でSpeedReward、評価用は素の環境）---
    train_env = make_env(env_id, vel_coef, seed, training=True)
    eval_env = make_env(env_id, 0.0, seed + 10000, training=False)

    # --- 出力ディレクトリ ---
    os.makedirs("models", exist_ok=True)
    os.makedirs("checkpoints", exist_ok=True)
    tensorboard_log = f"runs/{run.id}" if run is not None else None

    # --- TQCハイパラをconfigから組み立て ---
    tqc_kwargs = {k: config[k] for k in TQC_HYPERPARAM_KEYS if k in config}

    # --- モデル生成 or 再開 ---
    if args.resume:
        print(f"[resume] {args.resume} から再開します")
        model = TQC.load(
            args.resume,
            env=train_env,
            device="cpu",
            tensorboard_log=tensorboard_log,
        )
        reset_num_timesteps = False
    else:
        model = TQC(
            "MlpPolicy",
            train_env,
            device="cpu",
            seed=seed,
            verbose=1,
            tensorboard_log=tensorboard_log,
            **tqc_kwargs,
        )
        reset_num_timesteps = True

    # --- コールバック ---
    callbacks = []
    # 評価は素の環境・deterministic=Trueで行い、best modelを保存する
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

    # 再開用チェックポイント
    checkpoint_callback = CheckpointCallback(
        save_freq=int(config.get("checkpoint_freq", 50000)),
        save_path="checkpoints",
        name_prefix=f"tqc_velcoef{int(vel_coef)}_seed{seed}",
    )
    callbacks.append(checkpoint_callback)

    if run is not None:
        from wandb.integration.sb3 import WandbCallback

        callbacks.append(
            WandbCallback(
                gradient_save_freq=0,
                model_save_path=f"runs/{run.id}/model",
                verbose=2,
            )
        )

    # --- 学習 ---
    model.learn(
        total_timesteps=total_timesteps,
        callback=CallbackList(callbacks),
        reset_num_timesteps=reset_num_timesteps,
        progress_bar=False,
    )

    # --- 最終モデルを命名規則で保存 ---
    # ファイル名用の評価報酬: EvalCallbackのbest、無ければ最後に素の環境で短評価する
    eval_reward = eval_callback.best_mean_reward
    if eval_reward == -float("inf"):
        eval_reward, _ = evaluate_policy(
            model, eval_env, n_eval_episodes=5, deterministic=True
        )

    steps = model.num_timesteps
    name = (
        f"bipedalwalker_tqc_velcoef{int(vel_coef)}_seed{seed}"
        f"_{steps}_{int(round(eval_reward))}"
    )
    save_path = os.path.join("models", name)
    model.save(save_path)
    print(f"[saved] {save_path}.zip  (eval_reward={eval_reward:.1f})")

    train_env.close()
    eval_env.close()
    if run is not None:
        run.finish()


if __name__ == "__main__":
    main()
