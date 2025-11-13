# Task 1: HTTP server

```bash
# Terminal 1: run proxy
python start_proxy.py --server-ip 0.0.0.0 --server-port 8080
# Terminal 2: run backend
python start_backend.py --server-ip 0.0.0.0 --server-port 9000
# Access:
http://127.0.0.1:8080/
```


# Task 2: 🚀 BK Hybrid P2P Chat 

📦 Installation
1. Prerequisites
```bash
# Python 2.7 or Python 3.x
python --version
```
2. Install Desktop Notifications (Optional but Recommended)
```bash
# Library for UI:
pip install customtkinter
#or
python -m pip install customtkinter

# For cross-platform support
pip install plyer
# or
python -m pip install --upgrade pip
python -m pip install plyer

# OR for Windows only
pip install win10toast
#or
python -m pip install win10toast
```

3. Initialize Database
```bash
# Run this FIRST before starting tracker
python db_init.py
Expected output:
======================================================================
🚀 KHỞI TẠO DATABASE ENHANCED - WITH ACCESS CONTROL
======================================================================
✓ Tạo bảng 'users'...
  → Đã thêm user 'admin', 'user1', 'user2'.
✓ Tạo bảng 'peers'...
✓ Tạo bảng 'channels' với access control...
✓ Tạo bảng 'channel_members' (access control)...
  → Đã tạo kênh '#general' mặc định (public).
  → Đã tạo kênh '#private-admin' (private).
  → Đã thêm 'user2' vào kênh '#private-admin'.
======================================================================
✅ DATABASE ĐÃ SẴN SÀNG TẠI: db/app.db
======================================================================
```
🚀 Running the Application

Step 1: Start Tracker Server
```bash
python start_tracker.py
Expected output:
======================================================================
🚀 HYBRID P2P CHAT SERVER - ENHANCED WITH ACCESS CONTROL
======================================================================
📍 Address: 0.0.0.0:8000
💾 Database: db/app.db
⏰ Server Time: 2025-01-10 15:30:00
✅ Features:
   • DM History Storage
   • Channel History
   • Access Control (Private/Public Channels)
   • Synchronized Timestamp
   • Auto Local Timezone Support
======================================================================
```
Step 2: Start Client(s)
```bash
# Terminal 1 - User 1
python peer_gui.py

# Terminal 2 - User 2
python peer_gui.py

# Terminal 3 - User 3 (optional)
python peer_gui.py
```
📖 Usage Guide
1. Login

Default users (from db_init.py):

Username: admin / Password: password
Username: user1 / Password: 123
Username: user2 / Password: 456


Or click Register to create new account

2. Channel Features
Join Public Channel

Click on channel name in left sidebar (e.g., # general)
Start sending messages

Join Private Channel

Private channels show 🔒 icon
Only accessible if:

You are the owner
OR you are in the allowed members list

If no access, you'll see: "🔒 Access denied: Private channel"

Create New Channel

Click ➕ button next to "CHANNELS"
Enter channel name and topic
Check "🔒 Private Channel" for access control
Click "Create Channel"

3. Broadcast Feature
How to Broadcast

Make sure you're in a channel (e.g., #general)
Click 📢 Broadcast button (bottom left)
Enter your message
Click "Broadcast"

What Happens

Message is sent directly to ALL online peers via P2P
ALL peers receive it in the SAME CHANNEL you're in
Message is marked with (BROADCAST) tag
Everyone sees it in their current channel view
Desktop notification sent: "📢 Broadcast Sent"

Example:
[15:30] admin (BROADCAST): Team meeting at 3pm!
4. Direct Messages (DM)

Click on username in ONLINE section
Type message and press Enter
Unread count shows in square brackets: [2]
Desktop notification when new DM arrives

5. Desktop Notifications
You'll receive desktop notifications for:

👋 User joined/left
💬 New DM received
📢 Broadcast messages
🔍 Search results

Note: Install plyer or win10toast for desktop notifications.
6. Search Messages

Click search bar (top left)
Type your query
Matching text in message content will be highlighted in yellow
Search count shown in notification

7. Access Control Examples
Scenario 1: Public Channel
User: admin
Action: Join #general
Result: ✓ Success (everyone can join)
Scenario 2: Private Channel (Owner)
User: admin
Channel: #private-admin (owner: admin)
Action: Join #private-admin
Result: ✓ Success (owner always has access)
Scenario 3: Private Channel (Allowed Member)
User: user2
Channel: #private-admin (owner: admin, members: [user2])
Action: Join #private-admin
Result: ✓ Success (user2 is in allowed list)
Scenario 4: Private Channel (Denied)
User: user1
Channel: #private-admin (owner: admin, members: [user2])
Action: Try to join #private-admin
Result: ❌ "Access denied: Private channel"