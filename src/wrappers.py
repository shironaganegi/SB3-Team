"""前進速度ボーナスを報酬に加えるだけの gymnasium ラッパー（学習時のみ使用）。"""

import gymnasium as gym


class SpeedReward(gym.Wrapper):
    """BipedalWalker の前進速度に応じた報酬ボーナスを足すラッパー。

    観測ベクトル obs[2] は正規化された前進（hull）速度。
    reward += vel_coef * obs[2] を足すだけで、転倒ペナルティ（報酬 -100）には
    一切手を触れない。vel_coef=0 のときは何も足さず、素の環境と同じ挙動になる。

    注意: あくまで「学習を速い歩容に誘導する」ための報酬整形であり、
    最終的な評価（完走率・ゴール到達ステップ数）は素の環境で行う。
    evaluate.py 側ではこのラッパーを被せないこと。
    """

    def __init__(self, env: gym.Env, vel_coef: float = 0.0):
        super().__init__(env)
        self.vel_coef = float(vel_coef)

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        # vel_coef=0 のときは加算をスキップ（baseline と完全に同一の挙動）
        if self.vel_coef != 0.0:
            # obs[2] = 正規化された前進速度。前進していれば正、後退で負。
            reward = reward + self.vel_coef * obs[2]
        return obs, reward, terminated, truncated, info
