import os
import time
from datetime import datetime
import requests

# ===== 設定 =====
BRIGHTDATA_TOKEN = os.environ["BRIGHTDATA_API_TOKEN"]
SALTCORN_URL = "https://sachitwitterlist.saltcorn.com/api/tweets"
SALTCORN_TOKEN = os.environ["SALTCORN_API_TOKEN"]

# 監視対象ユーザー（@なし）
TARGET_USER = "hatori_copy"
TARGET_PROFILE_URL = f"https://x.com/{TARGET_USER}"

# キーワードフィルタ（いずれかを含むツイートのみ保存）
TARGET_KEYWORDS = ["aw"]

# 除外キーワード
EXCLUDE_KEYWORDS = []

# 取得件数（毎時6件）
MAX_ITEMS = 6

# Bright Data設定
DATASET_ID = "gd_lwxkxvnf1cynvib9co"


def fetch_tweets():
    """Bright Data APIでプロフィールの最新投稿を取得"""
    url = "https://api.brightdata.com/datasets/v3/scrape"
    params = {
        "dataset_id": DATASET_ID,
        "type": "discover_new",
        "discover_by": "profile_url",
        "format": "json",
        "limit_per_input": MAX_ITEMS,
    }
    headers = {
        "Authorization": f"Bearer {BRIGHTDATA_TOKEN}",
        "Content-Type": "application/json",
    }
    # ★ 修正点：配列を直接送信する
    payload = [{"url": TARGET_PROFILE_URL}]

    res = requests.post(
        url, params=params, headers=headers, json=payload, timeout=70
    )

    # 202 = 同期タイムアウト → 非同期で結果を取得
    if res.status_code == 202:
        snapshot_id = res.json()["snapshot_id"]
        return poll_snapshot(snapshot_id)

    res.raise_for_status()
    return res.json()


def poll_snapshot(snapshot_id):
    """非同期ジョブの結果をポーリングで取得"""
    url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
    headers = {"Authorization": f"Bearer {BRIGHTDATA_TOKEN}"}
    for _ in range(12):
        time.sleep(5)
        res = requests.get(url, headers=headers, params={"format": "json"})
        if res.status_code == 200:
            return res.json()
    raise TimeoutError("Snapshot polling timed out")


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
    """Bright Dataの出力をSaltcornスキーマにマッピングして保存"""
    saved = 0
    for t in tweets[:MAX_ITEMS]:
        text = t.get("description") or ""
        if not should_save(text):
            continue

        payload = {
            "tweet_id": str(t.get("id")),
            "text": text,
            "author_name": t.get("user_posted") or TARGET_USER,
            "author_handle": t.get("user_posted") or TARGET_USER,
            "tweet_url": t.get("url"),
            "tweet_created_at": t.get("date_posted"),
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
    print(f"Fetched {len(tweets)} tweets from @{TARGET_USER}")
    save_to_saltcorn(tweets)


if __name__ == "__main__":
    main()
