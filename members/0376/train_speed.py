# train_speed.py
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from speed_wrapper import make_speed_env
from sb3_contrib import RecurrentPPO
import torch

if __name__ == "__main__":
    print(f"CUDA使用可能: {torch.cuda.is_available()}")

    # 9800X3Dを活かすために、環境を16個並列で起動！
    n_envs = 16
    
    # カスタムラッパーを適用した環境を並列化して作成
    env = make_vec_env(make_speed_env, n_envs=n_envs)

    # Hugging Faceで使われていた、LSTM(記憶)付きのPPOモデルの初期設定
    # ※まずは動作確認のため、短いステップ数で回せる設定にしています
    model = RecurrentPPO(
        "MlpLstmPolicy",
        env,
        learning_rate=3e-4,
        n_steps=256,
        batch_size=256,
        n_epochs=10,
        gamma=0.999,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.001,
        policy_kwargs=dict(
            ortho_init=False,
            lstm_hidden_size=64,
            net_arch=dict(pi=[64], vf=[64])
        ),
        verbose=1,
        device="cpu" # RTX 5070 Tiを明示的に指定
    )

    print("🚀 学習スタート！ (中断する場合は Ctrl+C を押してください)")
    
    # まずは動作テストとして、10万ステップ回してみます（本番は数千万〜1億ステップです）
    model.learn(total_timesteps=5000000)

    # 学習したモデルを保存
    model.save("speed_bipedal_5M")
    print("✅ テスト学習完了。モデルを保存しました！")