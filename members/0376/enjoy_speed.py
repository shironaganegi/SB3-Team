# enjoy_speed.py
import gymnasium as gym
from sb3_contrib import RecurrentPPO
from speed_wrapper import make_speed_env
import numpy as np

# 画面表示(human)ありでカスタム環境を起動
env = make_speed_env(render_mode="human")

# 先ほど保存した学習済みモデルを読み込む（CPUで動かすように指定）
model = RecurrentPPO.load("speed_bipedal_15M", env=env, device="cpu")

obs, info = env.reset()

# LSTM（記憶）の初期化
lstm_states = None
# エピソードの開始フラグ（最初はTrue）
episode_starts = np.ones((1,), dtype=bool)

print("📺 学習したモデルの動きを再生します！")

# 1000コマ分（約30秒）動かしてみる
for i in range(1000):
    # モデル(脳みそ)にセンサー情報を渡し、行動を決定させる
    action, lstm_states = model.predict(
        obs,
        state=lstm_states,
        episode_start=episode_starts,
        deterministic=True  # 確率的なブレをなくし、実力通りの動きをさせる
    )
    
    # 行動を実行
    obs, reward, terminated, truncated, info = env.step(action)
    
    # 転倒したりゴールしたかの判定
    episode_starts = np.array([terminated or truncated], dtype=bool)
    
    if terminated or truncated:
        print("🔄 エピソード終了。リセットします。")
        obs, info = env.reset()
        lstm_states = None  # 転んだら記憶もリセットする

env.close()