"""チーム共通の評価スクリプト。素の環境で完走率とゴール到達ステップ数を測る。

このスクリプトがやること:
  保存済みの TQC モデル(.zip)を読み込み、素の BipedalWalker-v3 で
  複数シード × 複数エピソード回して、次の3つを出します。
    1. 完走率（completion_rate）… 何割のエピソードでコースを完走できたか
    2. ゴール到達ステップ数（goal_steps）… 完走したときの平均・中央値ステップ
    3. 平均報酬（reward_mean）… 全エピソードの累積報酬の平均

実行例:
  python src/evaluate.py models/bipedalwalker_tqc_velcoef0_seed0_1000000_312.zip
  python src/evaluate.py models/best_model.zip --seeds 0 1 2 3 4 --episodes 20

【最終課題の採点を手元で再現する】
  採点は Basic / Hardcore 両モードで「ランダムコース5回の平均」。
  ゴールできれば平均ステップ数（→ goal_steps_mean）、できなければ
  平均Reward（→ reward_mean）で順位づけされます（README §2.5）。
  シードを5つ変えれば「コースが毎回ランダム」を再現できます:
    python src/evaluate.py models/<候補>.zip --seeds 0 1 2 3 4 --episodes 1
    python src/evaluate.py models/<候補>.zip --env-id BipedalWalkerHardcore-v3 --seeds 0 1 2 3 4 --episodes 1

【最終選抜はこのスクリプトだけで行います】
  学習時の SpeedReward は絶対に被せません（素の環境で測る）。
  W&B の eval/mean_reward はあくまで探索用の代理指標で、勝敗には使いません。
  1本の好成績で判断せず、必ず複数シードで安定して出ることを確認してください。

【どこを編集する？】
  完走の判定基準を変えたいときは、下の2つのしきい値と is_success() を読みます。
  普段の評価では --seeds と --episodes をコマンドラインで変えるだけで十分です。
"""

import argparse
import json
import os
import statistics

import gymnasium as gym
from stable_baselines3.common.monitor import Monitor
from sb3_contrib import TQC


# ======================================================================
# 完走判定のしきい値（根拠は各コメント参照）
# ======================================================================
# BipedalWalker は転倒（hull が地面に接触 or 画面外）すると報酬 -100 で終了します。
# 通常の1ステップ報酬は概ね [-1, +1] 程度なので、「最終ステップの報酬が -90 以下」
# なら、それは転倒ペナルティ -100 によるものだと判断できます。
FALL_PENALTY_MARGIN = -90.0

# コースを完走（地形の終端に到達）すると、転倒ペナルティなしで terminated します。
# 一方、時間切れ（TimeLimit, 1600ステップ）は truncated で、終端未到達なので完走ではない。
# さらに保険として、累積報酬がこの値以上であることも条件に加えます。
# BipedalWalker-v3 は平均報酬300で「解けた」とされ、完走エピソードは概ね 250 以上。
# その場で立ち止まって truncated したケースを弾くため、しきい値を 200 に設定。
SUCCESS_REWARD_THRESHOLD = 200.0


def is_success(total_reward, last_reward, terminated, truncated):
    """1エピソードが「完走（コース終端に到達）」かどうかを頑健に判定する。

    完走とみなす条件（3つすべてを満たす）:
      (1) 転倒で終わっていない … 最終ステップの報酬が転倒ペナルティ相当でない
      (2) 時間切れではなく terminated で終わっている … truncated でない
      (3) 累積報酬が十分高い … 立ち止まり等の偽の終了を弾く保険
    """
    fell = last_reward <= FALL_PENALTY_MARGIN
    reached_goal = terminated and (not truncated)
    return (not fell) and reached_goal and (total_reward >= SUCCESS_REWARD_THRESHOLD)


def run_episode(model, env):
    """1エピソードを deterministic で最後まで回す。

    返り値: (完走したか[bool], かかったステップ数[int], 累積報酬[float])
    """
    obs, _ = env.reset()
    total_reward = 0.0
    last_reward = 0.0
    steps = 0
    terminated = truncated = False

    # terminated（成功 or 転倒）か truncated（時間切れ）になるまで動かす
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = env.step(action)
        total_reward += reward
        last_reward = reward   # 最後のステップ報酬を覚えておく（転倒判定に使う）
        steps += 1

    success = is_success(total_reward, last_reward, terminated, truncated)
    return success, steps, total_reward


def evaluate(model, model_path, env_id, seeds, episodes_per_seed):
    """素の環境で seeds × episodes 回し、結果を集計して辞書で返す。"""
    n_total = 0
    n_success = 0
    success_steps = []   # 完走したエピソードのステップ数だけを溜める
    all_rewards = []     # 全エピソードの累積報酬（完走できないモデルの比較用）

    for seed in seeds:
        # 評価は必ず素の環境（SpeedReward なし）。Monitor だけ被せる。
        env = gym.make(env_id)
        env = Monitor(env)
        env.reset(seed=seed)

        for _ in range(episodes_per_seed):
            success, steps, reward = run_episode(model, env)
            n_total += 1
            all_rewards.append(reward)
            if success:
                n_success += 1
                success_steps.append(steps)

        env.close()

    # 集計結果をまとめる（このまま JSON にも書き出す）
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
        # 課題の第2指標: ゴールできないモデルは「平均Reward」で順位づけされる。
        # 完走ゼロのモデル同士でも、この値で改善しているかを比較できる。
        # 環境が返す報酬は numpy の float32 なので、JSON に書けるよう float に直す。
        "reward_mean": float(statistics.mean(all_rewards)) if all_rewards else None,
    }
    return result


def main():
    # --- コマンドライン引数 ---
    parser = argparse.ArgumentParser(description="Evaluate a TQC model on raw BipedalWalker")
    parser.add_argument("model", help="評価するモデルの .zip パス")
    parser.add_argument("--env-id", default="BipedalWalker-v3")
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[0, 1, 2],
        help="評価に使うシード（複数指定可）。例: --seeds 0 1 2 3 4",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=10,
        help="各シードあたりのエピソード数。",
    )
    args = parser.parse_args()

    # モデルを CPU で読み込んで評価
    model = TQC.load(args.model, device="cpu")
    result = evaluate(model, args.model, args.env_id, args.seeds, args.episodes)

    # --- 標準出力（ターミナルに簡潔に表示）---
    print(f"model            : {result['model']}")
    print(f"seeds            : {result['seeds']}  (episodes/seed={result['episodes_per_seed']})")
    print(f"completion_rate  : {result['completion_rate']:.3f}  ({result['n_success']}/{result['n_total']})")
    if result["goal_steps_mean"] is not None:
        print(f"goal_steps_mean  : {result['goal_steps_mean']:.1f}")
        print(f"goal_steps_median: {result['goal_steps_median']}")
    else:
        print("goal_steps       : 完走エピソードなし")
    if result["reward_mean"] is not None:
        print(f"reward_mean      : {result['reward_mean']:.1f}")

    # --- JSON 出力（results/<モデル名>.json に保存。後で比較しやすいように）---
    os.makedirs("results", exist_ok=True)
    out_name = os.path.splitext(os.path.basename(args.model))[0] + ".json"
    out_path = os.path.join("results", out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[saved] {out_path}")


if __name__ == "__main__":
    main()
