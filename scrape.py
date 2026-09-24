import os
from datetime import datetime
import requests
from Scweet import Scweet

# ===== 設定 =====
KEYWORD = "au"
SALTCORN_URL = "https://sachitwitterlist.saltcorn.com/api/tweets"
SALTCORN_TOKEN = os.environ["SALTCORN_API_TOKEN"]
X_AUTH_TOKEN = os.environ["X_AUTH_TOKEN"]
TARGET_USERS = ["hatori_copy"]

def main():
    # ① Scweetの初期化（auth_tokenを渡す）
    s = Scweet(auth_token=X_AUTH_TOKEN)

    # ② キーワード検索（最新20件を取得）
    tweets = s.search(
    KEYWORD,
    from_users=TARGET_USERS,
    limit=20,
    save=False,
)

    # ③ 各ツイートをSaltcornへPOST
    for t in tweets:
        payload = {
            "tweet_id": t.id,
            "text": t.text,
            "author_name": t.user.name,
            "author_handle": t.user.screen_name,
            "tweet_url": f"https://x.com/{t.user.screen_name}/status/{t.id}",
            "tweet_created_at": t.date.isoformat(),
            "collected_at": datetime.now().isoformat(),
        }
        res = requests.post(
            SALTCORN_URL,
            json=payload,
            headers={"Authorization": f"Bearer {SALTCORN_TOKEN}"},
        )
        # 重複（409）は無視、それ以外のエラーはログ出力
        if res.status_code not in (200, 201, 409):
            print(f"ERROR {res.status_code}: {res.text}")

if __name__ == "__main__":
    main()
