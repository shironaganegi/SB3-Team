# speed_wrapper.py
import gymnasium as gym
import numpy as np

class SpeedRewardWrapper(gym.RewardWrapper):
    def __init__(self, env, speed_bonus_weight=2.0):
        super().__init__(env)
        self.speed_bonus_weight = speed_bonus_weight
        self.previous_x = None

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        # BipedalWalkerの観測空間(obs)の仕様上、直接のx座標は取れないため
        # ハル（胴体）のLIDAR情報などから前進を評価するか、
        # あるいは環境内部の変数にアクセスします。
        # 今回は最もシンプルに「観測値の2番目（hull_linear_velocity_x）」をボーナスにします。
        return obs, info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        
        # BipedalWalkerのobs[2]は、胴体の水平方向の速度(hull_linear_velocity_x)です。
        # これがプラス（前に進んでいる）なら、速度に比例してボーナスを与えます。
        forward_velocity = obs[2]
        
        # 速度が一定以上（例: 0.1以上）の場合にボーナスを加算
        if forward_velocity > 0.1:
            speed_bonus = forward_velocity * self.speed_bonus_weight
            reward += speed_bonus
            
        return obs, reward, terminated, truncated, info

# RL Zooから呼び出せるように、環境を登録するための関数
def make_speed_env(env_id="BipedalWalkerHardcore-v3", **kwargs):
    env = gym.make(env_id, **kwargs)
    env = SpeedRewardWrapper(env)
    return env