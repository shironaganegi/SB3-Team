"""モデルの走りを動画（mp4）にするスクリプト。評価と同じ素の環境で1エピソード再生する。

このスクリプトがやること:
  保存済みの TQC モデル(.zip)を読み込み、素の環境（SpeedReward なし）で
  deterministic=True の1エピソードを再生しながら全フレームを録画し、
  mp4 として保存します。完走判定は evaluate.py と同じロジックです。

実行例:
  python src/record_video.py models/best_model.zip
  python src/record_video.py models/best_model.zip --env-id BipedalWalkerHardcore-v3 --seed 0
  python src/record_video.py models/best_model.zip --wandb   # W&B にもアップロード

【なぜ動画を撮るのか】
  完走率やステップ数の数字だけでは「どんな歩き方をしているか」
  「どこで転ぶ・詰まるか」が分かりません。動画はレポートの説明にも、
  次に何を改善すべきかの観察にも使えます。

【動画の時間換算】
  BipedalWalker の物理は 50 FPS（README §8）なので、fps=50 で書き出すと
  動画の再生時間 = ゲーム内時間になります（例: 577ステップ ≒ 11.5秒）。

【W&B にアップロードするとき（--wandb）】
  wandb login 済みの環境（Kaggle なら Secrets 経由でログインするセル3の後）で
  実行してください。project は学習と同じ bipedal-timetrial に、
  job_type="video" の小さな run として記録されます。
"""

import argparse
import os

import gymnasium as gym
import imageio
from sb3_contrib import TQC

# 完走判定は evaluate.py（チーム共通評価）と同じものを使う。
# src/ ディレクトリ内で実行される前提（python src/record_video.py ...）。
from evaluate import is_success


def record_episode(model, env_id, seed, out_path):
    """素の環境で1エピソード再生して mp4 に保存する。

    train.py からも呼ばれる共通関数（学習終了時の自動動画アップロード用）。
    戻り値: (success, steps, total_reward)
    """
    env = gym.make(env_id, render_mode="rgb_array")
    obs, _ = env.reset(seed=seed)
    frames = [env.render()]
    total_reward = 0.0
    last_reward = 0.0
    steps = 0
    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)
        frames.append(env.render())
        total_reward += float(reward)
        last_reward = float(reward)
        steps += 1
    env.close()

    success = is_success(total_reward, last_reward, terminated, truncated)

    # 物理 50 FPS に合わせて書き出す（再生時間 = ゲーム内時間）
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    imageio.mimwrite(out_path, frames, fps=50)
    return success, steps, total_reward


def main():
    parser = argparse.ArgumentParser(description="Record a TQC model episode as mp4")
    parser.add_argument("model", help="動画にするモデルの .zip パス")
    parser.add_argument("--env-id", default="BipedalWalker-v3")
    parser.add_argument("--seed", type=int, default=0, help="コースを決める乱数シード")
    parser.add_argument(
        "--out",
        default=None,
        help="出力先 mp4 パス。省略時は results/videos/<モデル名>_<env>_seed<seed>.mp4",
    )
    parser.add_argument(
        "--wandb",
        action="store_true",
        help="mp4 を W&B にもアップロードする（wandb login 済みであること）",
    )
    args = parser.parse_args()

    if args.out is None:
        stem = os.path.splitext(os.path.basename(args.model))[0]
        env_tag = "hardcore" if "Hardcore" in args.env_id else "basic"
        args.out = f"results/videos/{stem}_{env_tag}_seed{args.seed}.mp4"

    # 素の環境（SpeedReward を被せない）で1エピソード再生して録画
    model = TQC.load(args.model, device="cpu")
    success, steps, total_reward = record_episode(model, args.env_id, args.seed, args.out)

    print(f"model        : {os.path.basename(args.model)}")
    print(f"env / seed   : {args.env_id} / {args.seed}")
    print(f"result       : {'完走' if success else '未完走'}  steps={steps}  reward={total_reward:.1f}")
    print(f"[saved] {args.out}")

    if args.wandb:
        import wandb

        run = wandb.init(
            project="bipedal-timetrial",
            name=f"video_{os.path.splitext(os.path.basename(args.out))[0]}",
            job_type="video",
            config={
                "model": os.path.basename(args.model),
                "env_id": args.env_id,
                "seed": args.seed,
                "success": success,
                "steps": steps,
                "reward": round(total_reward, 1),
            },
        )
        wandb.log({"demo": wandb.Video(args.out, format="mp4")})
        run.finish()
        print("[uploaded] W&B に動画をアップロードしました")


if __name__ == "__main__":
    main()
