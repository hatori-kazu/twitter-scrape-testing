import asyncio
import os
import json
from datetime import datetime
import requests
from twscrape import API, gather

# ===== 設定 =====
SALTCORN_URL = "https://sachitwitterlist.saltcorn.com/api/tweets"
SALTCORN_TOKEN = os.environ["SALTCORN_API_TOKEN"]

# 監視対象ユーザーとキーワード
TARGET_USER = "hatori_copy"
TARGET_KEYWORDS = ["aw"]

# 除外キーワード
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


async def fetch_tweets():
    """twscrapeで検索（from: + キーワード）"""
    api = API()

    # Xの高度な検索構文：from:ユーザー名 (キーワード1 OR キーワード2)
    keywords_query = " OR ".join(TARGET_KEYWORDS)
    query = f"from:{TARGET_USER} ({keywords_query}) -filter:replies"

    tweets = await gather(api.search(query, limit=FETCH_LIMIT))
    print(f"Fetched {len(tweets)} tweets from @{TARGET_USER}")
    return tweets


def save_to_saltcorn(tweets):
    """twscrapeのTweetオブジェクトをSaltcornスキーマにマッピング"""
    saved = 0
    for t in tweets:
        text = t.rawContent or ""
        if not should_save(text):
            continue

        payload = {
            "tweet_id": str(t.id),
            "text": text,
            "author_name": t.user.displayname or TARGET_USER,
            "author_handle": t.user.username or TARGET_USER,
            "tweet_url": f"https://x.com/{t.user.username}/status/{t.id}",
            "tweet_created_at": t.date.isoformat() if t.date else None,
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


async def main():
    tweets = await fetch_tweets()
    save_to_saltcorn(tweets)


if __name__ == "__main__":
    asyncio.run(main())
