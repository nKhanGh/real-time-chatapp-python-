import sqlite3
import os

DB_PATH = 'db/app.db'
if os.path.exists(DB_PATH):
    print(f"Đang xóa database cũ: {DB_PATH}")
    os.remove(DB_PATH)

os.makedirs('db', exist_ok=True)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 70)
print("🚀 KHỞI TẠO DATABASE")
print("=" * 70)

# Bảng 1: Users
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
''')
print("✓ Tạo bảng 'users'...")
try:
    cursor.executemany("INSERT INTO users (username, password) VALUES (?, ?)", [
        ('admin', 'password'),
        ('user1', '123'),
        ('user2', '456')
    ])
    print("  → Đã thêm user 'admin', 'user1', 'user2'.")
except sqlite3.IntegrityError:
    print("  → Users đã tồn tại.")

# Bảng 2: Peers
cursor.execute('''
CREATE TABLE IF NOT EXISTS peers (
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT NOT NULL, 
    PRIMARY KEY (ip, port) 
)
''')
print("✓ Tạo bảng 'peers'...")

# Bảng 3: Channels WITH ACCESS CONTROL
cursor.execute('''
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    owner_id INTEGER NOT NULL,
    is_private INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
)
''')
print("✓ Tạo bảng 'channels' với access control...")

# Bảng mới: Channel Members (for private channels)
cursor.execute('''
CREATE TABLE IF NOT EXISTS channel_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(channel_id, user_id)
)
''')
print("✓ Tạo bảng 'channel_members' (access control)...")

try:
    cursor.execute("INSERT INTO channels (name, topic, owner_id, is_private) VALUES (?, ?, ?, ?)", 
                   ('general', 'Kênh chat chung', 1, 0))
    print("  → Đã tạo kênh '#general' mặc định (public).")

    
    # Add user2 to private channel
    cursor.execute("INSERT INTO channel_members (channel_id, user_id) VALUES (?, ?)", 
                   (2, 3))  # channel_id=2 (private-admin), user_id=3 (user2)
    print("  → Đã thêm 'user2' vào kênh '#private-admin'.")
except sqlite3.IntegrityError:
    print("  → Channels đã tồn tại.")

# Bảng 4: Messages (channel messages)
cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
)
''')
print("✓ Tạo bảng 'messages'...")

# Bảng 5: Direct Messages
cursor.execute('''
CREATE TABLE IF NOT EXISTS direct_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
)
''')
print("✓ Tạo bảng 'direct_messages'...")

# Index để tìm kiếm DM nhanh hơn
cursor.execute('''
CREATE INDEX IF NOT EXISTS idx_dm_users 
ON direct_messages(sender_id, receiver_id)
''')
print("✓ Tạo index cho direct_messages...")

# Index cho channel members
cursor.execute('''
CREATE INDEX IF NOT EXISTS idx_channel_members 
ON channel_members(channel_id, user_id)
''')
print("✓ Tạo index cho channel_members...")

conn.commit()
conn.close()

print("=" * 70)
print(f"✅ DATABASE ĐÃ SẴN SÀNG TẠI: {DB_PATH}")
print("=" * 70)
print("📊 SCHEMA SUMMARY:")
print("  • users: User authentication")
print("  • peers: Online peer tracking")
print("  • channels: Chat channels (public/private)")
print("  • channel_members: Access control for private channels")
print("  • messages: Channel message history")
print("  • direct_messages: DM history")
print("=" * 70)
print("🔒 ACCESS CONTROL:")
print("  • Public channels: Everyone can join")
print("  • Private channels: Only owner + allowed members")
print("  • Owner always has full access")
print("=" * 70)
print("📝 DEFAULT DATA:")
print("  • Users: admin, user1, user2")
print("  • Channels: #general (public), #private-admin (private)")
print("  • Permissions: user2 can access #private-admin")
print("=" * 70)