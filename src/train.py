"""TQC（sb3-contrib）を CPU で学習・保存するスクリプト（W&B sweep 対応）。

このスクリプトがやること:
  1. YAML 設定ファイル（configs/*.yaml）を読み込む
  2. その設定で BipedalWalker-v3 の学習環境と評価環境を作る
  3. TQC で学習し、途中でベストモデルとチェックポイントを保存する
  4. 最後に最終モデルを命名規則に従って models/ に保存する

実行例:
  # まず配管確認（数千ステップで一周回す）
  python src/train.py --config configs/smoke.yaml

  # 本番の baseline 学習（vel_coef=0 の素の TQC）
  python src/train.py --config configs/classic_baseline.yaml

  # チェックポイントから再開する
  python src/train.py --config configs/classic_baseline.yaml --resume checkpoints/xxx.zip

【どこを編集する？】
  学習の設定（ステップ数・ハイパラ・速度ボーナス等）は YAML 側で変えます
  （共有 configs/ は直接書き換えず、members/<自分の番号>/configs/ にコピーして編集）。
  このスクリプト自体を書き換える必要は普段ありません。TQC のハイパラ
  （tau や gamma など）を新しく試したいときも、YAML に1行足すだけで
  自動的に TQC へ渡ります（下の TQC_PARAM_NAMES を参照）。
"""

import argparse
import inspect
import os

import yaml
import torch as th
import gymnasium as gym
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CallbackList,
    CheckpointCallback,
    EvalCallback,
)
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.utils import set_random_seed
from sb3_contrib import TQC

from wrappers import SpeedReward, SoftFallPenalty


# YAML の項目は次の2種類に自動で振り分けられます。
#
#   1. TQC のハイパラ … TQC のコンストラクタ引数と同じ名前なら、そのまま TQC へ
#      渡されます。名前の一覧は TQC の実物の定義から自動で取るので、新しいハイパラ
#      （tau・gamma・batch_size など）を試したいときは YAML に1行足すだけでOK。
#      このファイルの編集は不要です。
#   2. 学習の制御用キー … total_timesteps や vel_coef など、このスクリプト自身が
#      読む項目。下の CONTROL_KEYS に列挙してあります。
#
# どちらにも当てはまらないキーは打ち間違いの可能性が高いので、実行時に
# [warn] で知らせます（エラーにはせず学習は続けます）。

# TQC へは policy・env などを別途明示的に渡すので、YAML から受け取る対象から外す
_EXPLICITLY_PASSED = {
    "self", "policy", "env", "device", "verbose",
    "seed", "tensorboard_log", "_init_setup_model",
}
TQC_PARAM_NAMES = set(inspect.signature(TQC.__init__).parameters) - _EXPLICITLY_PASSED

# このスクリプト自身が読む「学習の制御用」キー
CONTROL_KEYS = {
    "env_id", "vel_coef", "time_penalty", "fall_penalty", "seed", "total_timesteps",
    "eval_freq", "n_eval_episodes", "checkpoint_freq",
    "use_wandb", "wandb_project", "wandb_entity",
}

# fall_penalty の既定値（素の環境と同じ -100 = SoftFallPenalty を被せない）。
# wrappers.SoftFallPenalty の既定値（-10）とは意図的に別の定数。ここが「無効」を
# 意味する基準値で、SoftFallPenalty 側は「有効にしたときの推奨値」を持つ。
FALL_PENALTY_DISABLED = -100.0


def warn_unknown_keys(config):
    """TQC にも学習制御にも当てはまらないキーを警告する（打ち間違い対策）。

    W&B が内部で足すメタ情報（アンダースコア始まり）は対象外。
    """
    for key in config:
        if key.startswith("_"):
            continue
        if key not in TQC_PARAM_NAMES and key not in CONTROL_KEYS:
            print(
                f"[warn] 設定キー '{key}' は TQC のハイパラにも学習制御用キーにも"
                f"見当たりません。打ち間違いではないですか？（無視して続行します）"
            )


def make_env(env_id, vel_coef, seed, training, time_penalty=0.0, fall_penalty=FALL_PENALTY_DISABLED):
    """1つの環境を作って返す。

    ラップの順番:
      gym.make → Monitor（必ず）
        → （学習用かつ vel_coef>0 or time_penalty>0 のときだけ）SpeedReward
        → （学習用かつ fall_penalty が既定値 -100 以外のときだけ）SoftFallPenalty

    training の意味:
      True  … 学習用の環境。上記の条件を満たすラッパーを被せる。
      False … 評価用の環境。常に素の環境（どちらのラッパーも被せない）。
    """
    env = gym.make(env_id)
    env = Monitor(env)  # エピソード報酬・長さを記録する標準ラッパー
    if training and (vel_coef > 0 or time_penalty > 0):
        env = SpeedReward(env, vel_coef=vel_coef, time_penalty=time_penalty)
    if training and fall_penalty != FALL_PENALTY_DISABLED:
        env = SoftFallPenalty(env, fall_penalty=fall_penalty)
    env.reset(seed=seed)
    return env


def load_config(path):
    """YAML 設定ファイルを辞書として読み込む。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def enable_expln(model):
    """gSDE の std 計算を expln 方式に切り替えて、NaN クラッシュを防ぐ。

    【なぜ】gSDE（use_sde: true）は探索ノイズの大きさを log_std という学習パラメータで
    持ち、標準では std = exp(log_std) で計算する。長い学習で log_std が正の方向に
    育ちすぎると exp が桁あふれして NaN になり、学習が墜落する（2026-07-15 の
    Hardcore run mild-lion-18 が 3.69M step でこれで落ちた。docs/BEST_CONFIG.md §8）。
    expln 方式は log_std<=0 では exp と完全に同じ値を返し、log_std>0 の領域だけ
    対数的にしか増えないため、正常な学習の挙動を一切変えずに発散だけを防げる。

    【なぜロード後にフラグを立てるだけでよいか】SB3 の
    StateDependentNoiseDistribution.get_std() は呼び出しのたびに self.use_expln を
    参照するので、モデル作成/ロード後にこの属性を True にすれば以降の計算に効く。
    --resume ではチェックポイント保存時のハイパラが復元される（YAML は効かない）ため、
    ここで一律に有効化する。
    """
    dist = getattr(getattr(model.policy, "actor", None), "action_dist", None)
    if dist is not None and hasattr(dist, "use_expln") and not dist.use_expln:
        dist.use_expln = True
        print("[nan-guard] gSDE の use_expln を有効化しました（std の発散による NaN を防ぐため）")


class StopOnNonFiniteCallback(BaseCallback):
    """学習パラメータに NaN/inf を検知したら、墜落する前に学習を「正常終了」させる。

    【なぜ】NaN で例外が出てプロセスごと死ぬと、学習後の処理（最終モデルの保存・
    best_model.zip の W&B アップロード・動画作成）が一切走らず、その run の成果が
    まるごと回収不能になる（mild-lion-18 で実際に起きた）。ここで先に検知して
    学習ループを止めれば、model.learn() が普通に戻ってきて後続の保存処理が全部走る。

    【何を見るか】発散の起点になった gSDE の log_std を番兵として監視する。
    注意: use_sde でないモデルでは log_std 属性はテンソルではなく nn.Linear 層
    なので、テンソルのときだけ検査する（それ以外は何もしない）。
    """

    def __init__(self, check_freq=1000):
        super().__init__()
        self.check_freq = check_freq

    def _on_step(self):
        if self.n_calls % self.check_freq != 0:
            return True
        log_std = getattr(getattr(self.model.policy, "actor", None), "log_std", None)
        if isinstance(log_std, th.Tensor) and not th.isfinite(log_std).all():
            print(
                f"[nan-guard] log_std に NaN/inf を検知したため、学習を安全に停止します"
                f"（step={self.model.num_timesteps:,}）。ここまでのベストモデルは保存されています。"
            )
            return False
        return True


class UploadBestToWandbCallback(BaseCallback):
    """EvalCallback がベストモデルを更新するたびに、その場で W&B へアップロードする。

    【なぜ】学習終了時のアップロード（main() 9.3節）だけだと、クラッシュ・NaN・
    Kaggle セッション上限のどれかで途中終了した run からは何も回収できない
    （mild-lion-18 では eval 報酬ピーク 243.5 のモデルを失った）。ベスト更新の
    たびに上げておけば、run がどう死んでも「その時点のベスト」は必ず W&B に残る。

    【使い方】EvalCallback の callback_on_new_best に渡す（ベストモデルの保存が
    済んだ直後に呼ばれる）。W&B を使う run でだけ生成すること。
    """

    def _on_step(self):
        import wandb

        best_path = os.path.join("models", "best_model.zip")
        if os.path.exists(best_path):
            # policy="live" は「ファイルが更新されるたびに同期し続ける」指定
            wandb.save(best_path, base_path="models", policy="live")
        return True


def main():
    # ----------------------------------------------------------------------
    # 1. コマンドライン引数
    # ----------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Train TQC on BipedalWalker (CPU)")
    parser.add_argument(
        "--config",
        default="configs/classic_baseline.yaml",
        help="使う YAML 設定ファイル。sweep ではこれを既定値の土台にする。",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="チェックポイント(.zip)から学習を再開したい場合のパス。",
    )
    # W&B sweep の agent は --vel_coef=... のような引数を勝手に付けてきます。
    # それらは argparse で受けず（parse_known_args で無視し）、後で wandb.config から
    # 取り込みます。なので未知の引数が来てもエラーにしません。
    args, _unknown = parser.parse_known_args()

    config = load_config(args.config)

    # ----------------------------------------------------------------------
    # 2. W&B を使うか判定
    # ----------------------------------------------------------------------
    # 次のどちらかなら W&B を有効化する:
    #   - config に use_wandb: true がある
    #   - sweep の agent から起動された（環境変数 WANDB_SWEEP_ID が立っている）
    is_sweep = os.environ.get("WANDB_SWEEP_ID") is not None
    use_wandb = bool(config.get("use_wandb", False)) or is_sweep

    run = None
    if use_wandb:
        import wandb

        run = wandb.init(
            project=config.get("wandb_project", "bipedal-timetrial"),
            entity=config.get("wandb_entity") or None,
            config=config,            # YAML の既定値をまず土台として渡す
            sync_tensorboard=True,
            save_code=True,
        )
        # sweep 経由なら wandb.config に vel_coef / seed / learning_rate などの
        # 「今回試す値」が入ってきます。それを YAML 既定値の上に上書きします
        # （= sweep が指定した値を優先）。
        for key in dict(wandb.config).keys():
            config[key] = wandb.config[key]

    # ----------------------------------------------------------------------
    # 3. 設定値の取り出し
    # ----------------------------------------------------------------------
    warn_unknown_keys(config)  # 打ち間違いキーがあればここで知らせる

    env_id = config.get("env_id", "BipedalWalker-v3")
    vel_coef = float(config.get("vel_coef", 0))
    time_penalty = float(config.get("time_penalty", 0))
    fall_penalty = float(config.get("fall_penalty", FALL_PENALTY_DISABLED))
    seed = int(config.get("seed", 0))
    total_timesteps = int(config.get("total_timesteps", 4000))

    # time_penalty を使った学習は、成果物のファイル名でも区別できるようにする
    # （README §9 の命名規則。0 のときは従来どおりタグなし）
    tp_tag = f"_timepen{time_penalty:g}" if time_penalty > 0 else ""

    # Hardcore で学習したモデルは、ファイル名だけで Basic と区別できるようにする
    # （README §9。Basic のときはタグなしで従来名と完全一致）
    env_tag = "hardcore_" if "Hardcore" in env_id else ""

    set_random_seed(seed)  # 再現性のため乱数シードを固定

    # ----------------------------------------------------------------------
    # 4. 環境を用意
    # ----------------------------------------------------------------------
    # 学習用: vel_coef>0 or time_penalty>0 なら SpeedReward、fall_penalty が
    #         既定値(-100)以外なら SoftFallPenalty も追加で被さる。
    # 評価用: 常に素の環境。学習用とシードをずらして（+10000）汎化を見る。
    train_env = make_env(
        env_id, vel_coef, seed, training=True,
        time_penalty=time_penalty, fall_penalty=fall_penalty,
    )
    eval_env = make_env(env_id, 0.0, seed + 10000, training=False)

    # ----------------------------------------------------------------------
    # 5. 出力先ディレクトリ（.gitignore 済み。GitHub には上がらない）
    # ----------------------------------------------------------------------
    os.makedirs("models", exist_ok=True)        # ベストモデル・最終モデル
    os.makedirs("checkpoints", exist_ok=True)   # 再開用チェックポイント
    tensorboard_log = f"runs/{run.id}" if run is not None else None

    # ----------------------------------------------------------------------
    # 6. モデルを作る or 再開する
    # ----------------------------------------------------------------------
    # YAML から TQC へ渡すハイパラだけを抜き出す（名前が一致するものは全部渡る）
    tqc_kwargs = {k: config[k] for k in config if k in TQC_PARAM_NAMES}

    if args.resume:
        print(f"[resume] {args.resume} から学習を再開します")
        # 再開時のハイパラはチェックポイント保存時点の値が使われる。
        # YAML でハイパラを変えても反映されない（変えたいときは新規学習で）。
        if tqc_kwargs:
            print(
                f"[resume] 注意: YAML のハイパラ {sorted(tqc_kwargs)} は再開時には"
                f"反映されません（チェックポイント保存時の値をそのまま使います）"
            )
        model = TQC.load(
            args.resume,
            env=train_env,
            device="cpu",
            tensorboard_log=tensorboard_log,
        )
        reset_num_timesteps = False  # ステップ数を引き継ぐ
    else:
        model = TQC(
            "MlpPolicy",
            train_env,
            device="cpu",            # GPU は使わない。全員 CPU で回す方針。
            seed=seed,
            verbose=1,
            tensorboard_log=tensorboard_log,
            **tqc_kwargs,
        )
        reset_num_timesteps = True

    # 新規・再開のどちらでも、gSDE の std 発散による NaN クラッシュを防ぐ
    # （関数の docstring 参照。use_sde でないモデルには何もしない）
    enable_expln(model)

    # ----------------------------------------------------------------------
    # 7. コールバック（学習中に定期的に走る処理）
    # ----------------------------------------------------------------------
    callbacks = []

    # (a) 評価コールバック: 一定ステップごとに素の環境で deterministic 評価し、
    #     成績が良ければ models/best_model.zip を更新する。
    #     W&B を使うときは、ベスト更新のたびにその場で W&B へも上げる
    #     （run が途中で死んでもベストだけは回収できるように）。
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="models",
        log_path="results",
        eval_freq=int(config.get("eval_freq", 10000)),
        n_eval_episodes=int(config.get("n_eval_episodes", 10)),
        deterministic=True,
        render=False,
        callback_on_new_best=UploadBestToWandbCallback() if run is not None else None,
    )
    callbacks.append(eval_callback)

    # (a') NaN の見張り: log_std が壊れたら墜落する前に学習を正常終了させる
    callbacks.append(StopOnNonFiniteCallback())

    # (b) チェックポイント: 一定ステップごとに checkpoints/ へ保存（再開用）。
    checkpoint_callback = CheckpointCallback(
        save_freq=int(config.get("checkpoint_freq", 50000)),
        save_path="checkpoints",
        name_prefix=f"tqc_{env_tag}velcoef{int(vel_coef)}{tp_tag}_seed{seed}",
    )
    callbacks.append(checkpoint_callback)

    # (c) W&B を使うときだけ、学習ログを W&B に送るコールバックを足す。
    if run is not None:
        from wandb.integration.sb3 import WandbCallback

        callbacks.append(
            WandbCallback(
                gradient_save_freq=0,
                model_save_path=f"runs/{run.id}/model",
                verbose=2,
            )
        )

    # ----------------------------------------------------------------------
    # 8. 学習本体
    # ----------------------------------------------------------------------
    model.learn(
        total_timesteps=total_timesteps,
        callback=CallbackList(callbacks),
        reset_num_timesteps=reset_num_timesteps,
        progress_bar=False,
    )

    # ----------------------------------------------------------------------
    # 9. 最終モデルを命名規則で保存
    # ----------------------------------------------------------------------
    # ファイル名に入れる評価報酬:
    #   基本は EvalCallback が見つけたベスト平均報酬を使う。
    #   一度も評価が走らなかった（= -inf のまま）場合だけ、最後に短く評価する。
    eval_reward = eval_callback.best_mean_reward
    if eval_reward == -float("inf"):
        eval_reward, _ = evaluate_policy(
            model, eval_env, n_eval_episodes=5, deterministic=True
        )

    steps = model.num_timesteps
    # 例: bipedalwalker_tqc_velcoef0_seed0_1000000_312.zip
    #     bipedalwalker_hardcore_tqc_velcoef0_seed0_1000000_120.zip
    #     (hardcore=Hardcore環境で学習したときだけ) / velcoef=速度ボーナス係数 /
    #     (timepen=時間ペナルティ、使ったときだけ) / seed=シード /
    #     steps=総ステップ / 末尾=評価報酬
    name = (
        f"bipedalwalker_{env_tag}tqc_velcoef{int(vel_coef)}{tp_tag}_seed{seed}"
        f"_{steps}_{int(round(eval_reward))}"
    )
    save_path = os.path.join("models", name)
    model.save(save_path)
    print(f"[saved] {save_path}.zip  (eval_reward={eval_reward:.1f})")

    # ----------------------------------------------------------------------
    # 9.3 EvalCallback のベストモデルを W&B へアップロード
    # ----------------------------------------------------------------------
    # 【なぜ】WandbCallback（8節）は学習終了時点の最終モデルしかアップロードしない
    #         （model_save_freq を指定していないため）。一方 Hardcore の評価報酬は
    #         run の途中で大きく上下することがあり、最終モデルがそのrunのベストとは
    #         限らない。resume の起点や最終提出の選抜がこの run のベスト到達点を
    #         使えるよう、models/best_model.zip も明示的に上げておく。
    if run is not None:
        best_model_path = os.path.join("models", "best_model.zip")
        if os.path.exists(best_model_path):
            wandb.save(best_model_path, base_path="models")
            print(f"[wandb] best_model.zip をアップロードしました（eval_reward={eval_reward:.1f}）")

    # ----------------------------------------------------------------------
    # 9.5 ベストモデルの走りを動画にして W&B へ自動アップロード
    # ----------------------------------------------------------------------
    # 【なぜ】完走率やステップ数の数字だけでは「どんな歩き方か」「どこで転ぶか」
    #         が分からない。全員の学習 run に動画が自動で付けば、W&B の
    #         ダッシュボードを見るだけで互いの方策の質を比較できる。
    # 【何を撮る】評価ベストの models/best_model.zip（無ければ最終モデル）を、
    #             学習と同じ env_id の素の環境で1エピソード。
    # 【失敗しても】モデルは保存済みなので、動画の失敗は警告だけ出して無視する。
    if run is not None:
        try:
            from record_video import record_episode

            best_path = os.path.join("models", "best_model.zip")
            film_path = best_path if os.path.exists(best_path) else save_path + ".zip"
            video_path = os.path.join("results", "videos", f"{name}.mp4")
            film_model = TQC.load(film_path, device="cpu")
            success, v_steps, v_reward = record_episode(film_model, env_id, seed, video_path)
            wandb.log({"demo": wandb.Video(video_path, format="mp4")})
            print(
                f"[video] {'完走' if success else '未完走'} steps={v_steps} "
                f"reward={v_reward:.1f} → W&B の run に動画をアップロードしました"
            )
        except Exception as e:  # 動画は学習の成否と無関係なので、ここでは落とさない
            print(f"[video] 動画の作成/アップロードに失敗しました（学習結果には影響なし）: {e}")

    # ----------------------------------------------------------------------
    # 10. 後片付け
    # ----------------------------------------------------------------------
    train_env.close()
    eval_env.close()
    if run is not None:
        run.finish()


if __name__ == "__main__":
    main()
