# train_continue.py
from stable_baselines3.common.env_util import make_vec_env
from sb3_contrib import RecurrentPPO
from speed_wrapper import make_speed_env

if __name__ == "__main__":
    # 9800X3Dを活かすために16並列で環境を作成
    n_envs = 16
    env = make_vec_env(make_speed_env, n_envs=n_envs)

    print("🧠 前回の500万ステップ学習済みモデルを読み込みます...")
    
    # ここが最大のポイント！
    # 前回保存した「speed_bipedal_5M」を読み込み、新しい環境(env)に接続します
    # ※GPUエラーを避けるため、引き続き device="cpu" を指定します
    model = RecurrentPPO.load("speed_bipedal_5M", env=env, device="cpu")

    print("🚀 追加学習（1000万ステップ）をスタートします！")
    
    # reset_num_timesteps=False にすることで、内部のステップカウンターを
    # 0に戻さず、500万の続きからカウントするようにします
    model.learn(total_timesteps=10000000, reset_num_timesteps=False)

    # 学習が終わったら新しい名前で保存
    model.save("speed_bipedal_15M")
    print("✅ 追加学習完了！ 合計1500万ステップのモデルを保存しました！")