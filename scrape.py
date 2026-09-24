import os
import time
from datetime import datetime
import requests

# ===== 設定 =====
BRIGHTDATA_TOKEN = os.environ["BRIGHTDATA_API_TOKEN"]
SALTCORN_URL = "https://sachitwitterlist.saltcorn.com/api/tweets"
SALTCORN_TOKEN = os.environ["SALTCORN_API_TOKEN"]

TARGET_PROFILE = "https://x.com/hatori_copy"   # 監視したいユーザーのプロフィールURL
DATASET_ID = "gd_lwxkxvnf1cynvib9co"        # Posts (Discover by Profile URL)
MAX_ITEMS = 6

def fetch_tweets():
    """Bright Data X Scraper APIでプロフィールの最新投稿を取得"""
    url = "https://api.brightdata.com/datasets/v3/scrape"
    params = {"dataset_id": DATASET_ID, "format": "json"}
    headers = {
        "Authorization": f"Bearer {BRIGHTDATA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = [{"url": TARGET_PROFILE, "limit": MAX_ITEMS}]

    res = requests.post(url, params=params, headers=headers, json=payload, timeout=70)

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
    for _ in range(10):          # 最大10回（約50秒）
        time.sleep(5)
        res = requests.get(url, headers=headers, params={"format": "json"})
        if res.status_code == 200:
            return res.json()
    raise TimeoutError("Snapshot polling timed out")

def save_to_saltcorn(tweets):
    """Bright Dataの出力をSaltcornスキーマにマッピングして保存"""
    for t in tweets[:MAX_ITEMS]:
        payload = {
            "tweet_id": t.get("id"),
            "text": t.get("description") or t.get("text"),
            "author_name": t.get("user_posted") or t.get("user_name"),
            "author_handle": t.get("user_posted"),
            "tweet_url": t.get("url"),
            "tweet_created_at": t.get("date_posted"),
            "collected_at": datetime.now().isoformat(),
        }
        res = requests.post(
            SALTCORN_URL,
            json=payload,
            headers={"Authorization": f"Bearer {SALTCORN_TOKEN}"},
        )
        if res.status_code not in (200, 201, 409):
            print(f"ERROR {res.status_code}: {res.text}")

def main():
    tweets = fetch_tweets()
    print(f"Fetched {len(tweets)} tweets")
    save_to_saltcorn(tweets)

if __name__ == "__main__":
    main()
