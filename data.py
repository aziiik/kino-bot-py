# ══════════════════════════════════════════════
#  data.py — Barcha ma'lumotlar xotirada saqlanadi
#  ⚠️  Bot to'xtasa ma'lumotlar o'chadi (faqat test uchun)
# ══════════════════════════════════════════════

# Foydalanuvchilar: { "user_id": {"username": "..."} }
users: dict = {}

# Kinolar: { "kod": {"file_id": "...", "title": "...", "desc": "..."} }
# Misol:
# movies = {
#     "001": {"file_id": "BQACAgI...", "title": "Inception", "desc": ""},
# }
movies: dict = {}

# Admin ID lari (int)
admins: list = []

# Support ID lari (int)
supports: list = []

# Majburiy obuna kanallari: ["@kanal1", "@kanal2"]
channels: list = []
