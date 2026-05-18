"""Data health check — validates that collectors are working correctly."""
from datetime import datetime, timezone
 
from gw2trading.db.database import get_connection
from gw2trading.collectors.tracked_items import TOP_200_ITEM_IDS

def main() -> None:
    print("=== GW2 Data Health Check ===\n")


    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items")
    items_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM price_snapshots")
    prices_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM patch_notes")
    patch_notes_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reddit_posts")
    reddit_posts_count = cursor.fetchone()[0]

    print(f"Items: {items_count}")
    print(f"Price snapshots: {prices_count}")
    print(f"Patch notes: {patch_notes_count}")
    print(f"Reddit posts: {reddit_posts_count}")

    cursor.execute("SELECT MAX(timestamp) FROM price_snapshots")
    latest_price = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(date) FROM patch_notes")
    latest_patch = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(fetched_at) FROM reddit_posts")
    latest_reddit = cursor.fetchone()[0]
    print(f"Latest price snapshot: {latest_price or 'No data yet'}")
    print(f"Latest patch note: {latest_patch or 'No data yet'}")
    print(f"Latest reddit post: {latest_reddit or 'No data yet'}")

    # Freshness checks
    print()
    if latest_price:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(latest_price)
        if age.total_seconds() > 1800:
            print(f"(!!!!!) Price data is stale ({int(age.total_seconds() // 60)} min old)")
        else:
            print("(✓✓✓) Price data is fresh (< 30 min old)")
    else:
        print("(!!!!!) No price data collected yet")

    if latest_reddit:
        reddit_dt = datetime.fromisoformat(latest_reddit).replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - reddit_dt
        if age.total_seconds() > 7200:
            print(f"(!!!!!) Reddit data is stale ({int(age.total_seconds() // 60)} min old)")
        else:
            print("(✓✓✓) Reddit data is fresh (< 2 hours old)")
    else:
        print("(!!!!!) No Reddit data collected yet")

    cursor.execute("""
        SELECT COUNT(DISTINCT item_id) FROM price_snapshots
        WHERE item_id IN ({})
    """.format(','.join(str(id) for id in TOP_200_ITEM_IDS)))
    covered_items = cursor.fetchone()[0]
    print(f"Tracked items with price data: {covered_items}/{len(TOP_200_ITEM_IDS)}")

    conn.close()




if __name__ == "__main__":
    main()

