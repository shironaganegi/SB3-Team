"""学習時だけ報酬を整形するための gymnasium ラッパー集。

このファイルには「報酬の形を変えるラッパー」を置きます。今は前進速度ボーナスを
足す SpeedReward だけですが、別の報酬整形を試したくなったら、ここに新しい
gym.Wrapper のクラスを追加し、train.py の make_env() から呼び出す形にします。

【重要】ラッパーは「学習を望ましい歩き方へ誘導する」ための道具です。
最終的な成績（完走率・ゴール到達ステップ数）は必ず素の環境で測るので、
evaluate.py 側ではこのラッパーを絶対に被せないでください。
"""

import gymnasium as gym


class SpeedReward(gym.Wrapper):
    """前進速度ボーナスと時間ペナルティで「速い歩容」へ学習を誘導するラッパー（学習時のみ使用）。

    仕組み:
      毎ステップの報酬に次の2項を足します。

        reward += vel_coef * obs[2]      # 前進が速いほど加点（後退は減点）
        reward -= time_penalty           # 1ステップ経過ごとの一定減点

      obs[2] は BipedalWalker の観測ベクトルの3番目の要素で、
      「正規化された前進（hull）速度」です。前進していれば正、後退で負。
      time_penalty はゴール到達を急がせる（＝ステップ数を縮める）効果があります。

    触らない部分:
      転倒ペナルティ（報酬 -100 で終了）には一切手を加えません。
      vel_coef=0 かつ time_penalty=0 のときは加算をまるごとスキップするので、
      素の環境（baseline）と完全に同じ挙動になります。

    パラメータ:
      vel_coef: 速度ボーナスの強さ。configs の `vel_coef` で指定します。
                0 = ボーナスなし。大きいほど「とにかく速く」に寄ります。
      time_penalty: 1ステップごとの減点の強さ。configs の `time_penalty` で指定します。
                大きすぎると「早めに転んで損切りした方が得」という報酬ハックを
                招くため小さく設定します。

    注意: あくまで学習誘導用の報酬整形であり、最終的な評価（完走率・ゴール到達
    ステップ数）は素の環境で行う。evaluate.py 側ではこのラッパーを被せないこと。
    """

    def __init__(self, env: gym.Env, vel_coef: float = 0.0, time_penalty: float = 0.0):
        super().__init__(env)
        self.vel_coef = float(vel_coef)
        self.time_penalty = float(time_penalty)

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)

        # vel_coef=0 のときは何も足さない（baseline と完全に同一の挙動にするため）。
        if self.vel_coef != 0.0:
            # obs[2] = 正規化された前進速度（前進で正・後退で負）。
            forward_velocity = obs[2]
            reward = reward + self.vel_coef * forward_velocity
        if self.time_penalty != 0.0:
            # 1ステップごとの一定減点。早くゴールするほど累積ペナルティが小さい。
            reward = reward - self.time_penalty

        return obs, reward, terminated, truncated, info
