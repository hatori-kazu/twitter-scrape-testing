import os
import json
import subprocess
from datetime import datetime
import requests

# ===== 設定 =====
SALTCORN_URL = "https://sachitwitterlist.saltcorn.com/api/tweets"
SALTCORN_TOKEN = os.environ["SALTCORN_API_TOKEN"]

# 監視対象ユーザー（@なし）
TARGET_USER = "hatori_copy"

# 取得件数（深めに取得してフィルタで絞る）
FETCH_LIMIT = 100

# フィルタするキーワード（いずれかを含むツイートのみ保存）
TARGET_KEYWORDS = ["galaxy"]

# 除外キーワード
EXCLUDE_KEYWORDS = [""]


def fetch_tweets():
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}/data:/data",
            "ghcr.io/tamnd/x:latest",
            "timeline", TARGET_USER,
            "--guest",
            "-n", str(FETCH_LIMIT),
            "-o", "jsonl",
        ],
        capture_output=True, text=True, timeout=120,
    )
    print("=== STDOUT ===")
    print(result.stdout[:500])
    print("=== STDERR ===")
    print(result.stderr[:1000])
    print(f"=== returncode: {result.returncode} ===")
    
    if result.returncode != 0:
        print(f"x-cli ERROR: {result.stderr}")
        return []

    tweets = []
    for line in result.stdout.strip().splitlines():
        if line.strip():
            tweets.append(json.loads(line))
    print(f"Fetched {len(tweets)} tweets from @{TARGET_USER}")
    return tweets


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


def save_to_saltcorn(tweets):
    """x-cliのJSONL出力をSaltcornスキーマにマッピングして保存"""
    saved = 0
    for t in tweets:
        text = t.get("text") or ""
        if not should_save(text):
            continue

        author = t.get("author") or {}
        payload = {
            "tweet_id": str(t.get("id")),                    # 文字列で保持（snowflake精度）
            "text": text,
            "author_name": author.get("name") or TARGET_USER,
            "author_handle": author.get("username") or TARGET_USER,
            "tweet_url": t.get("url") or f"https://x.com/{TARGET_USER}/status/{t.get('id')}",
            "tweet_created_at": t.get("created_at"),
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
