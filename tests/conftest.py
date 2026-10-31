import os

# bot.py reads this key at import time. A fake value lets the tests run
# on any machine (a fresh clone, CI) without a real key or a .env file.
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")