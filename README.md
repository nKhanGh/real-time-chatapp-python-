# BK Hybrid P2P Chat 💬

A modern hybrid peer-to-peer chat application with centralized authentication and distributed messaging, built with Python and CustomTkinter.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-2.7%20%7C%203.x-blue.svg)

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Architecture](#architecture)
- [HTTP Server (Task 1)](#http-server-task-1)
- [License](#license)

## ✨ Features

### 🔐 Authentication & Security
- User registration and login system
- Session-based authentication with cookies
- Access control for private channels

### 💬 Messaging
- **Public Channels**: Open to all users
- **Private Channels**: Restricted access with member management
- **Direct Messages**: One-on-one private conversations
- **Broadcast**: P2P message delivery to all online users

### 🎨 Modern UI
- Beautiful dark-themed interface with CustomTkinter
- Visual selection indicators (Blue for channels, Green for users)
- Emoji support and quick reactions
- Typing indicators
- Search with highlighting
- Desktop notifications

### 🔄 Real-time Features
- Direct P2P message delivery
- Auto-refresh peer list
- Online status tracking
- Message history synchronization

## 🚀 Quick Start

### Prerequisites

```bash
python --version  # Python 2.7 or 3.x required
```

### Installation

1. **Install dependencies**

```bash
pip install customtkinter plyer
# or for Windows only
pip install customtkinter win10toast
```

2. **Initialize database**

```bash
python db_init.py
```

Expected output:
```
======================================================================
🚀 KHỞI TẠO DATABASE
======================================================================
✓ Tạo bảng 'users'...
  → Đã thêm user 'admin', 'user1', 'user2'.
✓ Tạo bảng 'channels' với access control...
======================================================================
✅ DATABASE ĐÃ SẴN SÀNG TẠI: db/app.db
======================================================================
```

### Running the Application

**Step 1: Start Tracker Server**

```bash
python start_tracker.py
```

**Step 2: Launch Client(s)**

```bash
# Terminal 1 - User 1
python peer_gui.py

# Terminal 2 - User 2
python peer_gui.py

# Terminal 3 - User 3 (optional)
python peer_gui.py
```

## 📖 Usage

### Login

Default accounts:
- **admin** / password
- **user1** / 123
- **user2** / 456

Or click **Register** to create a new account.

### Channel Management

**Join Channel**
- Click channel name in sidebar (e.g., `# general`)
- Start sending messages

**Create New Channel**
1. Click ➕ button next to "CHANNELS"
2. Enter channel name and topic
3. Check "🔒 Private Channel" for access control
4. Add members (for private channels)
5. Click "Create Channel"

**Private Channels**
- 🔒 icon indicates private channels
- Access requires:
  - Being the channel owner, OR
  - Being in the allowed members list
- Owners can manage members via right-click menu

### Broadcasting

1. Select a channel
2. Click 📢 **Broadcast** button (bottom left)
3. Enter your message
4. Click "Broadcast"

Result: Message sent directly to ALL online peers via P2P

```
[15:30] admin (BROADCAST): Team meeting at 3pm!
```

### Direct Messages

1. Click any username in the **ONLINE** section
2. Type and send messages privately
3. Unread count shown in brackets: `[2]`
4. Desktop notification on new DM

### Search Messages

1. Click search bar (top left)
2. Type your query
3. Matching text highlighted in yellow
4. Search count shown in notification

## 🏗️ Architecture

### Hybrid P2P Design
- **Centralized Tracker**: Authentication, history storage, peer discovery
- **P2P Messaging**: Direct peer-to-peer message delivery
- **Protocol**: Custom HTTP-based protocol over TCP
- **Database**: SQLite for persistence

### Database Schema
- `users`: User accounts and authentication
- `peers`: Online peer tracking
- `channels`: Channel metadata and access control
- `channel_members`: Private channel membership
- `messages`: Channel message history
- `direct_messages`: DM history

### Network Ports
- **Tracker**: 8000 (default)
- **Backend**: 9000 (default)
- **Proxy**: 8080 (default)
- **P2P Clients**: 9002+ (auto-assigned)

### Project Structure

```
├── peer_gui.py          # Client GUI application
├── start_tracker.py     # Central server
├── start_backend.py     # HTTP backend server
├── start_proxy.py       # Reverse proxy server
├── db_init.py          # Database initialization
├── daemon/             # Core networking modules
│   ├── weaprous.py     # RESTful routing framework
│   ├── backend.py      # Backend server logic
│   ├── proxy.py        # Proxy implementation
│   ├── request.py      # HTTP request handler
│   ├── response.py     # HTTP response builder
│   └── httpadapter.py  # HTTP adapter
├── db/                 # SQLite database
└── config/             # Configuration files
```

## 🌐 HTTP Server (Task 1)

The project includes a reverse proxy and backend HTTP server.

### Running HTTP Server

```bash
# Terminal 1: Run proxy
python start_proxy.py --server-ip 0.0.0.0 --server-port 8080

# Terminal 2: Run backend
python start_backend.py --server-ip 0.0.0.0 --server-port 9000
```

### Access

```
http://127.0.0.1:8080/
```

### Features
- Reverse proxy with virtual host routing
- Round-robin load balancing
- Session-based authentication
- Static file serving
- Cookie management

## 🔑 Key Concepts

### Broadcast vs Regular Messages
- **Regular Message**: Logged to server + delivered to online peers
- **Broadcast**: Direct P2P to ALL online users, marked with `(BROADCAST)` tag

### Access Control
- **Public Channels**: Anyone can join and send messages
- **Private Channels**: 
  - Owner has full access
  - Members must be explicitly added
  - Non-members see 🔒 and receive "Access Denied"

### Message Synchronization
- Channel history stored on server
- DM history stored on server
- History loaded when opening channel/DM
- Timestamps converted to local timezone

## 🛠️ Technical Stack

- **Language**: Python 2.7/3.x
- **UI Framework**: CustomTkinter
- **Database**: SQLite3
- **Networking**: Python socket (TCP)
- **Notifications**: plyer / win10toast
- **Architecture**: Hybrid P2P

## 📝 License

Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.

Released under the MIT License. This project is part of the CO3093/CO3094 course.

---

**Note**: Desktop notifications require `plyer` (cross-platform) or `win10toast` (Windows). The app works without them but won't show system notifications.

## 🤝 Contributing

This is a course project. Contributions are welcome for educational purposes.

## 📧 Contact

For questions or issues, please contact the course instructor or open an issue in the repository.