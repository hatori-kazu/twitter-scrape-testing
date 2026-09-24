import os
from datetime import datetime
import requests
from Scweet import Scweet

# ===== 設定 =====
SALTCORN_URL = "https://sachitwitterlist.saltcorn.com/api/tweets"
SALTCORN_TOKEN = os.environ["SALTCORN_API_TOKEN"]

# X認証情報（両方必要）
X_AUTH_TOKEN = os.environ["X_AUTH_TOKEN"]
X_CT0 = os.environ["X_CT0"]

# 監視対象ユーザーとキーワード
TARGET_USER = "hatori_copy"
TARGET_KEYWORDS = ["aw"]
EXCLUDE_KEYWORDS = [""]

# 取得件数
FETCH_LIMIT = 20


def should_save(text):
    """キーワードフィルタ"""
    if not text:
        return False
    lower = text.lower()
    if any(ng.lower() in lower for ng in EXCLUDE_KEYWORDS):
        return False
    if not any(kw.lower() in lower for kw in TARGET_KEYWORDS):
        return False
    return True


def fetch_tweets():
    """Scweetで特定ユーザーのキーワード付きツイートを取得"""
    # auth_token と ct0 を cookies として明示的に渡す
    s = Scweet(cookies={
        "auth_token": X_AUTH_TOKEN,
        "ct0": X_CT0,
    })

    # X の高度な検索構文：from:ユーザー名 (キーワード1 OR キーワード2)
    keywords_query = " OR ".join(TARGET_KEYWORDS)
    query = f"from:{TARGET_USER} ({keywords_query}) -filter:replies"

    tweets = s.search(
        query,
        limit=FETCH_LIMIT,
        save=False,
    )
    print(f"Fetched {len(tweets)} tweets from @{TARGET_USER}")
    return tweets


def save_to_saltcorn(tweets):
    """Scweetの出力をSaltcornスキーマにマッピングして保存"""
    saved = 0
    for t in tweets:
        text = getattr(t, "text", "") or ""
        if not should_save(text):
            continue

        user = getattr(t, "user", None)
        payload = {
            "tweet_id": str(getattr(t, "id", "")),
            "text": text,
            "author_name": getattr(user, "name", TARGET_USER) if user else TARGET_USER,
            "author_handle": getattr(user, "screen_name", TARGET_USER) if user else TARGET_USER,
            "tweet_url": f"https://x.com/{TARGET_USER}/status/{getattr(t, 'id', '')}",
            "tweet_created_at": (
                t.date.isoformat() if getattr(t, "date", None) else None
            ),
            "collected_at": datetime.now().isoformat(),
        }
        res = requests.post(
            SALTCORN_URL,
            json=payload,
            headers={"Authorization": f"Bearer {SALTCORN_TOKEN}"},
        )
        if res.status_code in (200, 201):
            saved += 1
        elif res.status_code != 409:
            print(f"ERROR {res.status_code}: {res.text}")
    print(f"Saved {saved}/{len(tweets)} tweets after filtering")


def main():
    tweets = fetch_tweets()
    save_to_saltcorn(tweets)


if __name__ == "__main__":
    main()
