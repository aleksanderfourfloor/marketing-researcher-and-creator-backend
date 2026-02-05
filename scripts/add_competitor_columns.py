"""One-off: add twitter_url, instagram_url, facebook_url, reddit_url, discord_url to competitors. Run with: python scripts/add_competitor_columns.py"""
import sqlite3
import os

# Same path as default in config (relative to project root)
db_path = os.path.join(os.path.dirname(__file__), "..", "competitor_analysis.db")
if not os.path.isfile(db_path):
    print(f"DB not found at {db_path}; nothing to do.")
    exit(0)

conn = sqlite3.connect(db_path)
cols = ["twitter_url", "instagram_url", "facebook_url", "reddit_url", "discord_url"]
for col in cols:
    try:
        conn.execute(f"ALTER TABLE competitors ADD COLUMN {col} VARCHAR(512)")
        print(f"Added column: {col}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"Column {col} already exists, skipping")
        else:
            raise
conn.commit()
conn.close()
print("Done.")
