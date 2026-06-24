"""チーム共通の評価スクリプト。素の環境・deterministicで完走率とゴール到達ステップ数を出す。"""

import argparse
import json
import os
import statistics

import gymnasium as gym
from stable_baselines3.common.monitor import Monitor
from sb3_contrib import TQC


# --- 完走判定のしきい値（根拠はコメント参照）---
# BipedalWalker は転倒（hullが地面に接触 or 画面外）すると報酬 -100 で terminated する。
# したがって「最終ステップの報酬が -90 以下」なら転倒終了とみなせる
# （通常の1ステップ報酬は概ね [-1, +1] 程度で、-90 はほぼ転倒ペナルティ -100 専用の領域）。
FALL_PENALTY_MARGIN = -90.0
# コースを完走（terrainの終端に到達）すると、転倒ペナルティ無しで terminated する。
# 時間切れ（TimeLimit, 1600ステップ）は truncated になり、終端未到達なので完走ではない。
# さらに念のため、累積報酬がこの値以上であることも条件に加える。
# BipedalWalker-v3 は平均報酬300で「解けた」とされ、終端到達エピソードは概ね 250 以上になる。
# 立ち止まりや微小移動で truncated したケースを弾く保険として 200 を採用。
SUCCESS_REWARD_THRESHOLD = 200.0


def is_success(total_reward, last_reward, terminated, truncated):
    """1エピソードが完走（コース終端到達）かどうかを頑健に判定する。

    条件: (1) 転倒で終わっていない（最終ステップ報酬が転倒ペナルティ相当でない）、
    (2) 時間切れ(truncated)ではなく terminated で終わっている、
    (3) 累積報酬が十分高い。
    """
    fell = last_reward <= FALL_PENALTY_MARGIN
    reached_goal = terminated and (not truncated)
    return (not fell) and reached_goal and (total_reward >= SUCCESS_REWARD_THRESHOLD)


def run_episode(model, env):
    """1エピソードを deterministic で回し、(完走か, ステップ数, 累積報酬) を返す。"""
    obs, _ = env.reset()
    total_reward = 0.0
    last_reward = 0.0
    steps = 0
    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)
        total_reward += reward
        last_reward = reward
        steps += 1
    success = is_success(total_reward, last_reward, terminated, truncated)
    return success, steps, total_reward


def evaluate(model, model_path, env_id, seeds, episodes_per_seed):
    """素の環境で seeds × episodes 回し、結果を集計して辞書で返す。"""
    n_total = 0
    n_success = 0
    success_steps = []   # 完走したエピソードのステップ数

    for seed in seeds:
        # 評価は素の環境（SpeedReward なし）。Monitorのみ被せる。
        env = gym.make(env_id)
        env = Monitor(env)
        env.reset(seed=seed)
        for _ in range(episodes_per_seed):
            success, steps, _reward = run_episode(model, env)
            n_total += 1
            if success:
                n_success += 1
                success_steps.append(steps)
        env.close()

    result = {
        "model": os.path.basename(model_path),
        "env_id": env_id,
        "seeds": list(seeds),
        "episodes_per_seed": episodes_per_seed,
        "n_total": n_total,
        "n_success": n_success,
        "completion_rate": n_success / n_total if n_total else 0.0,
        "goal_steps_mean": statistics.mean(success_steps) if success_steps else None,
        "goal_steps_median": statistics.median(success_steps) if success_steps else None,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Evaluate a TQC model on raw BipedalWalker")
    parser.add_argument("model", help="評価するモデルの .zip パス")
    parser.add_argument("--env-id", default="BipedalWalker-v3")
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[0, 1, 2],
        help="評価に使うシード（複数）。",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=10,
        help="各シードあたりのエピソード数。",
    )
    args = parser.parse_args()

    model = TQC.load(args.model, device="cpu")
    result = evaluate(model, args.model, args.env_id, args.seeds, args.episodes)

    # --- 標準出力（簡潔なテキスト）---
    print(f"model            : {result['model']}")
    print(f"seeds            : {result['seeds']}  (episodes/seed={result['episodes_per_seed']})")
    print(f"completion_rate  : {result['completion_rate']:.3f}  ({result['n_success']}/{result['n_total']})")
    if result["goal_steps_mean"] is not None:
        print(f"goal_steps_mean  : {result['goal_steps_mean']:.1f}")
        print(f"goal_steps_median: {result['goal_steps_median']}")
    else:
        print("goal_steps       : 完走エピソードなし")

    # --- JSON 出力 ---
    os.makedirs("results", exist_ok=True)
    out_name = os.path.splitext(os.path.basename(args.model))[0] + ".json"
    out_path = os.path.join("results", out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[saved] {out_path}")


if __name__ == "__main__":
    main()
