# start_tracker.py - ENHANCED VERSION WITH ACCESS CONTROL
import json
import argparse
import sqlite3
from datetime import datetime, timezone
from daemon.weaprous import WeApRous
from daemon.response import Response

PORT = 8000 
DB_PATH = 'db/app.db'
app = WeApRous()

def get_db_conn():
    """Hàm tiện ích kết nối DB"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_from_req(req):
    """Lấy thông tin user (id, username) từ cookie trong request"""
    username = req.cookies.get('session')
    if not username:
        return None, None
    
    conn = get_db_conn()
    user = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user:
        return user['id'], user['username']
    return None, None

def build_json_response(req, data_dict, status_code=200, set_cookie=None):
    """Tự động build một response với body là JSON"""
    resp = Response(req)
    resp.status_code = status_code
    resp._content = json.dumps(data_dict).encode('utf-8')
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    
    if set_cookie:
        resp.headers['Set-Cookie'] = set_cookie
    
    return resp.build_response_header(req) + resp._content

def parse_json_body(req):
    """Helper function to parse JSON from request body"""
    try:
        if not req.body:
            return None, "Empty request body"
        
        body_str = req.body
        if isinstance(body_str, bytes):
            body_str = body_str.decode('utf-8')
        
        data = json.loads(body_str)
        return data, None
    except json.JSONDecodeError as e:
        print(f"[JSON] Decode error: {e}")
        return None, f"Invalid JSON: {str(e)}"
    except Exception as e:
        print(f"[JSON] Parse error: {e}")
        return None, f"Parse error: {str(e)}"


# ============ AUTHENTICATION APIs ============

@app.route('/register', methods=['POST'])
def register_user(req):
    print("[Tracker] Register request received")
    
    data, error = parse_json_body(req)
    if error:
        print(f"[Tracker] Parse error: {error}")
        return build_json_response(req, {"status": "error", "message": error}, 400)
    
    try:
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"[Tracker] Registering user: {username}")
        
        if not username or not password:
            print(f"[Tracker] ❌ Empty username or password")
            return build_json_response(req, {"status": "error", "message": "Username and password required"}, 400)
        
        conn = get_db_conn()
        existing = conn.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            print(f"[Tracker] ❌ Username '{username}' already exists")
            return build_json_response(req, {"status": "error", "message": "Username already exists"}, 401)
        
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
            conn.commit()
            print(f"[Tracker] ✅ User '{username}' registered successfully")
            conn.close()
            return build_json_response(req, {"status": "success", "message": "Registration successful"}, 200)
        except sqlite3.IntegrityError:
            conn.close()
            print(f"[Tracker] ❌ Username '{username}' already exists (race condition)")
            return build_json_response(req, {"status": "error", "message": "Username already exists"}, 401)
            
    except Exception as e:
        print(f"[Tracker] ❌ Register error: {e}")
        import traceback
        traceback.print_exc()
        return build_json_response(req, {"status": "error", "message": f"Server error: {str(e)}"}, 500)


@app.route('/login', methods=['POST'])
def login(req):
    print("[Tracker] Login request received")
    
    data, error = parse_json_body(req)
    if error:
        print(f"[Tracker] Parse error: {error}")
        return build_json_response(req, {"status": "error", "message": error}, 400)
    
    try:
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"[Tracker] Login attempt for user: {username}")
        
        if not username or not password:
            return build_json_response(req, {"status": "error", "message": "Username and password required"}, 400)
        
        conn = get_db_conn()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        conn.close()

        if user:
            print(f"[Tracker] ✅ User '{username}' logged in successfully")
            cookie_str = f"session={username}; Path=/; HttpOnly; SameSite=Lax"
            return build_json_response(
                req, 
                {"status": "success", "message": "Login successful", "user_id": user['id'], "body": {"username": username}}, 
                200,
                set_cookie=cookie_str
            )
        else:
            print(f"[Tracker] ❌ Invalid credentials for username: '{username}'")
            return build_json_response(req, {"status": "error", "message": "Invalid username or password"}, 401)
    except Exception as e:
        print(f"[Tracker] ❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        return build_json_response(req, {"status": "error", "message": f"Server error: {str(e)}"}, 500)


# ============ PEER MANAGEMENT APIs ============

@app.route('/submit-info/', methods=['POST'])
def submit_info(req):
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        print("[Tracker] Unauthorized submit-info request")
        return resp.build_unauthorized()

    data, error = parse_json_body(req)
    if error:
        return build_json_response(req, {"status": "error", "message": error}, 400)

    try:
        ip, port = data.get('ip'), data.get('port')
        if not ip or not port:
            return build_json_response(req, {"status": "error", "message": "Invalid peer info"}, 400)

        conn = get_db_conn()
        conn.execute("DELETE FROM peers WHERE username = ? AND ip = ? AND port = ?", 
                     (username, ip, port))
        conn.execute("INSERT INTO peers (ip, port, username) VALUES (?, ?, ?)", 
                     (ip, port, username))
        conn.commit()
        conn.close()
        
        print(f"[Tracker] ✅ '{username}' registered at {ip}:{port}")
        return build_json_response(req, {"status": "success", "message": "Peer registered"})
    except Exception as e:
        print(f"[Tracker] ❌ Error in submit_info: {e}")
        return resp.build_server_error()

@app.route('/get-list/', methods=['GET'])
def get_list(req):
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id: 
        print("[Tracker] Unauthorized get-list request")
        return resp.build_unauthorized()
    
    conn = get_db_conn()
    peers = conn.execute("SELECT ip, port, username FROM peers").fetchall()
    conn.close()
    
    peer_list = [dict(peer) for peer in peers] 
    print(f"[Tracker] Returned {len(peer_list)} peers to '{username}'")
    return build_json_response(req, peer_list)

@app.route('/logout/', methods=['POST'])
def logout(req):
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not username:
        return resp.build_unauthorized()

    try:
        data = json.loads(req.body) if req.body else {}
        ip = data.get('ip')
        port = data.get('port')
        
        conn = get_db_conn()
        
        if ip and port:
            conn.execute("DELETE FROM peers WHERE username = ? AND ip = ? AND port = ?", 
                        (username, ip, port))
            print(f"[Tracker] '{username}' unregistered from {ip}:{port}")
        else:
            conn.execute("DELETE FROM peers WHERE username = ?", (username,))
            print(f"[Tracker] All sessions for '{username}' unregistered")
        
        conn.commit()
        conn.close()
        return build_json_response(req, {"status": "success", "message": "Logged out"})
    except Exception as e:
        print(f"[Tracker] Logout error: {e}")
        return resp.build_server_error()


# ============ CHANNEL MANAGEMENT APIs WITH ACCESS CONTROL ============

@app.route('/create-channel/', methods=['POST'])
def create_channel(req):
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
    
    try:
        data = json.loads(req.body)
        name = data.get('name', '').strip()
        topic = data.get('topic', '').strip()
        is_private = data.get('is_private', False)
        allowed_users = data.get('allowed_users', [])
        
        if not name:
            return build_json_response(req, {"status": "error", "message": "Channel name required"}, 400)

        conn = get_db_conn()
        
        # Insert channel with access control
        conn.execute(
            "INSERT INTO channels (name, topic, owner_id, is_private) VALUES (?, ?, ?, ?)",
            (name, topic, user_id, 1 if is_private else 0)
        )
        
        # Add allowed users if private
        if is_private and allowed_users:
            channel_id = conn.execute("SELECT id FROM channels WHERE name = ?", (name,)).fetchone()['id']
            for allowed_user in allowed_users:
                user_row = conn.execute("SELECT id FROM users WHERE username = ?", (allowed_user,)).fetchone()
                if user_row:
                    conn.execute(
                        "INSERT INTO channel_members (channel_id, user_id) VALUES (?, ?)",
                        (channel_id, user_row['id'])
                    )
        
        conn.commit()
        conn.close()
        print(f"[Tracker] '{username}' created channel '{name}' (private: {is_private})")
        return build_json_response(req, {"status": "success", "message": f"Channel '{name}' created"})
    except sqlite3.IntegrityError:
        return build_json_response(req, {"status": "error", "message": "Channel already exists"}, 401)
    except Exception as e:
        print(f"[Tracker] Create error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()

@app.route('/list-channels/', methods=['GET'])
def list_channels(req):
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
    
    conn = get_db_conn()
    channels = conn.execute('''
        SELECT c.id, c.name, c.topic, u.username as owner, c.is_private
        FROM channels c JOIN users u ON c.owner_id = u.id
        ORDER BY c.created_at DESC
    ''').fetchall()
    
    result = []
    for ch in channels:
        channel_dict = dict(ch)
        
        # Get allowed users for private channels
        if ch['is_private']:
            members = conn.execute('''
                SELECT u.username 
                FROM channel_members cm 
                JOIN users u ON cm.user_id = u.id
                WHERE cm.channel_id = ?
            ''', (ch['id'],)).fetchall()
            channel_dict['allowed_users'] = [m['username'] for m in members]
        else:
            channel_dict['allowed_users'] = []
        
        result.append(channel_dict)
    
    conn.close()
    
    print(f"[Tracker] Returned {len(result)} channels to '{username}'")
    return build_json_response(req, result)


@app.route('/add-channel-member/', methods=['POST'])
def add_channel_member(req):
    """Thêm thành viên vào private channel"""
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
    
    try:
        data = json.loads(req.body)
        channel_name = data.get('channel_name', '').strip()
        new_member_username = data.get('username', '').strip()
        
        if not channel_name or not new_member_username:
            return build_json_response(req, {"status": "error", "message": "Missing fields"}, 400)
        
        conn = get_db_conn()
        
        # Kiểm tra channel có tồn tại và có phải private không
        channel = conn.execute(
            "SELECT id, owner_id, is_private FROM channels WHERE name = ?", 
            (channel_name,)
        ).fetchone()
        
        if not channel:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Channel not found"}, 404)
        
        # Chỉ owner mới có thể thêm thành viên
        if channel['owner_id'] != user_id:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Only owner can add members"}, 403)
        
        if not channel['is_private']:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Cannot add members to public channel"}, 400)
        
        # Lấy user_id của member mới
        new_user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (new_member_username,)
        ).fetchone()
        
        if not new_user:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "User not found"}, 404)
        
        # Kiểm tra xem user đã là member chưa
        existing = conn.execute(
            "SELECT 1 FROM channel_members WHERE channel_id = ? AND user_id = ?",
            (channel['id'], new_user['id'])
        ).fetchone()
        
        if existing:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "User already a member"}, 400)
        
        # Thêm member
        conn.execute(
            "INSERT INTO channel_members (channel_id, user_id) VALUES (?, ?)",
            (channel['id'], new_user['id'])
        )
        conn.commit()
        conn.close()
        
        print(f"[Tracker] '{username}' added '{new_member_username}' to #{channel_name}")
        return build_json_response(req, {"status": "success", "message": f"Added {new_member_username} to channel"})
        
    except Exception as e:
        print(f"[Tracker] Add member error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()


@app.route('/remove-channel-member/', methods=['POST'])
def remove_channel_member(req):
    """Xóa thành viên khỏi private channel"""
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
    
    try:
        data = json.loads(req.body)
        channel_name = data.get('channel_name', '').strip()
        remove_username = data.get('username', '').strip()
        
        if not channel_name or not remove_username:
            return build_json_response(req, {"status": "error", "message": "Missing fields"}, 400)
        
        conn = get_db_conn()
        
        channel = conn.execute(
            "SELECT id, owner_id, is_private FROM channels WHERE name = ?", 
            (channel_name,)
        ).fetchone()
        
        if not channel:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Channel not found"}, 404)
        
        if channel['owner_id'] != user_id:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Only owner can remove members"}, 403)
        
        remove_user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (remove_username,)
        ).fetchone()
        
        if not remove_user:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "User not found"}, 404)
        
        conn.execute(
            "DELETE FROM channel_members WHERE channel_id = ? AND user_id = ?",
            (channel['id'], remove_user['id'])
        )
        conn.commit()
        conn.close()
        
        print(f"[Tracker] '{username}' removed '{remove_username}' from #{channel_name}")
        return build_json_response(req, {"status": "success", "message": f"Removed {remove_username} from channel"})
        
    except Exception as e:
        print(f"[Tracker] Remove member error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()


@app.route('/get-channel-members/', methods=['POST'])
def get_channel_members(req):
    """Lấy danh sách thành viên của channel"""
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
    
    try:
        data = json.loads(req.body)
        channel_name = data.get('channel_name', '').strip()
        
        if not channel_name:
            return build_json_response(req, {"status": "error", "message": "Channel name required"}, 400)
        
        conn = get_db_conn()
        
        channel = conn.execute(
            "SELECT id, owner_id, is_private FROM channels WHERE name = ?", 
            (channel_name,)
        ).fetchone()
        
        if not channel:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Channel not found"}, 404)
        
        # Kiểm tra quyền truy cập
        if channel['is_private']:
            if channel['owner_id'] != user_id:
                is_member = conn.execute(
                    "SELECT 1 FROM channel_members WHERE channel_id = ? AND user_id = ?",
                    (channel['id'], user_id)
                ).fetchone()
                
                if not is_member:
                    conn.close()
                    return build_json_response(req, {"status": "error", "message": "Access denied"}, 403)
        
        # Lấy danh sách members
        members = conn.execute('''
            SELECT u.username 
            FROM channel_members cm 
            JOIN users u ON cm.user_id = u.id
            WHERE cm.channel_id = ?
        ''', (channel['id'],)).fetchall()
        
        # Lấy owner
        owner = conn.execute(
            "SELECT username FROM users WHERE id = ?", 
            (channel['owner_id'],)
        ).fetchone()
        
        conn.close()
        
        result = {
            "owner": owner['username'] if owner else None,
            "members": [m['username'] for m in members]
        }
        
        return build_json_response(req, result)
        
    except Exception as e:
        print(f"[Tracker] Get members error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()

# ============ MESSAGE MANAGEMENT APIs (CHANNEL) WITH ACCESS CONTROL ============

@app.route('/log-message/', methods=['POST'])
def log_message(req):
    """Lưu tin nhắn channel vào database"""
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        print("[Tracker] ❌ Unauthorized log-message")
        return resp.build_unauthorized()
    
    try:
        data = json.loads(req.body)
        channel_name = data.get('channel_name', '').strip()
        content = data.get('content', '').strip()
        
        print(f"[Tracker] 📝 Log message request: user='{username}', channel='{channel_name}'")
        
        if not channel_name or not content:
            print(f"[Tracker] ❌ Missing fields")
            return build_json_response(req, {"status": "error", "message": "Missing fields"}, 400)

        conn = get_db_conn()
        channel = conn.execute("SELECT id, owner_id, is_private FROM channels WHERE name = ?", (channel_name,)).fetchone()
        
        if not channel:
            print(f"[Tracker] ❌ Channel '{channel_name}' not found")
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Channel not found"}, 404)
        
        print(f"[Tracker] 📋 Channel info: id={channel['id']}, owner_id={channel['owner_id']}, is_private={channel['is_private']}, current_user_id={user_id}")
        
        # Check access control
        if channel['is_private']:
            print(f"[Tracker] 🔒 Private channel - checking access...")
            
            # Owner always has access
            if channel['owner_id'] == user_id:
                print(f"[Tracker] ✅ User is OWNER - access granted")
            else:
                print(f"[Tracker] 🔍 User is not owner, checking membership...")
                # Check if user is in allowed list
                member = conn.execute(
                    "SELECT 1 FROM channel_members WHERE channel_id = ? AND user_id = ?",
                    (channel['id'], user_id)
                ).fetchone()
                
                if not member:
                    print(f"[Tracker] ❌ ACCESS DENIED - user '{username}' (id={user_id}) not in channel_members")
                    conn.close()
                    return build_json_response(req, {"status": "error", "message": "Access denied"}, 403)
                else:
                    print(f"[Tracker] ✅ User is MEMBER - access granted")
        else:
            print(f"[Tracker] 🌐 Public channel - access granted")
        
        utc_now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            "INSERT INTO messages (content, user_id, channel_id, timestamp) VALUES (?, ?, ?, ?)",
            (content, user_id, channel['id'], utc_now)
        )
        conn.commit()
        conn.close()
        
        print(f"[Tracker] ✅ Message saved: '{username}' -> #{channel_name}: {content[:50]}...")
        return build_json_response(req, {"status": "success", "message": "Message sent"})
    except Exception as e:
        print(f"[Tracker] ❌ Log error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()

@app.route('/get-history/', methods=['POST'])
def get_history(req):
    """Lấy lịch sử tin nhắn channel với access control"""
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
        
    try:
        data = json.loads(req.body)
        channel_name = data.get('channel_name', '').strip()
        
        if not channel_name:
            return build_json_response(req, {"status": "error", "message": "Channel name required"}, 400)
        
        conn = get_db_conn()
        channel = conn.execute("SELECT id, owner_id, is_private FROM channels WHERE name = ?", (channel_name,)).fetchone()
        
        if not channel:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Channel not found"}, 404)
        
        # Check access control
        if channel['is_private']:
            if channel['owner_id'] != user_id:
                member = conn.execute(
                    "SELECT 1 FROM channel_members WHERE channel_id = ? AND user_id = ?",
                    (channel['id'], user_id)
                ).fetchone()
                
                if not member:
                    conn.close()
                    return build_json_response(req, {"status": "error", "message": "Access denied"}, 403)
        
        messages = conn.execute('''
            SELECT m.content, u.username, m.timestamp
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.channel_id = ?
            ORDER BY m.timestamp DESC
            LIMIT 100
        ''', (channel['id'],)).fetchall()
        conn.close()
        
        result = []
        for m in reversed(messages):
            msg_dict = dict(m)
            result.append(msg_dict)
        
        print(f"[Tracker] Returned {len(result)} messages from #{channel_name} to '{username}'")
        return build_json_response(req, result)
    except Exception as e:
        print(f"[Tracker] Get history error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()


# ============ DIRECT MESSAGE APIs ============

@app.route('/log-dm/', methods=['POST'])
def log_dm(req):
    """Lưu Direct Message vào database"""
    resp = Response(req)
    sender_id, sender_username = get_user_from_req(req)
    if not sender_id:
        return resp.build_unauthorized()
    
    try:
        data = json.loads(req.body)
        receiver_username = data.get('receiver', '').strip()
        content = data.get('content', '').strip()
        
        if not receiver_username or not content:
            return build_json_response(req, {"status": "error", "message": "Missing fields"}, 400)

        conn = get_db_conn()
        
        receiver = conn.execute("SELECT id FROM users WHERE username = ?", (receiver_username,)).fetchone()
        if not receiver:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "Receiver not found"}, 404)
        
        receiver_id = receiver['id']
        utc_now = datetime.now(timezone.utc).isoformat()
        
        conn.execute("INSERT INTO direct_messages (content, sender_id, receiver_id, timestamp) VALUES (?, ?, ?, ?)",
                     (content, sender_id, receiver_id, utc_now))
        conn.commit()
        conn.close()
        
        print(f"[Tracker] DM: '{sender_username}' -> '{receiver_username}': {content[:50]}...")
        return build_json_response(req, {"status": "success", "message": "DM sent"})
    except Exception as e:
        print(f"[Tracker] Log DM error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()


@app.route('/get-dm-history/', methods=['POST'])
def get_dm_history(req):
    """Lấy lịch sử DM giữa 2 users"""
    resp = Response(req)
    user_id, username = get_user_from_req(req)
    if not user_id:
        return resp.build_unauthorized()
        
    try:
        data = json.loads(req.body)
        other_username = data.get('other_user', '').strip()
        
        if not other_username:
            return build_json_response(req, {"status": "error", "message": "Other user required"}, 400)
        
        conn = get_db_conn()
        
        other_user = conn.execute("SELECT id FROM users WHERE username = ?", (other_username,)).fetchone()
        if not other_user:
            conn.close()
            return build_json_response(req, {"status": "error", "message": "User not found"}, 404)
        
        other_user_id = other_user['id']
        
        messages = conn.execute('''
            SELECT dm.content, 
                   sender.username as sender, 
                   receiver.username as receiver,
                   dm.timestamp
            FROM direct_messages dm
            JOIN users sender ON dm.sender_id = sender.id
            JOIN users receiver ON dm.receiver_id = receiver.id
            WHERE (dm.sender_id = ? AND dm.receiver_id = ?)
               OR (dm.sender_id = ? AND dm.receiver_id = ?)
            ORDER BY dm.timestamp DESC
            LIMIT 100
        ''', (user_id, other_user_id, other_user_id, user_id)).fetchall()
        conn.close()
        
        result = []
        for m in reversed(messages):
            msg_dict = dict(m)
            result.append(msg_dict)
        
        print(f"[Tracker] Returned {len(result)} DMs between '{username}' and '{other_username}'")
        return build_json_response(req, result)
    except Exception as e:
        print(f"[Tracker] Get DM history error: {e}")
        import traceback
        traceback.print_exc()
        return resp.build_server_error()


# ============ HEALTH CHECK ============

@app.route('/health', methods=['GET'])
def health_check(req):
    """Health check endpoint"""
    conn = get_db_conn()
    peer_count = conn.execute("SELECT COUNT(*) as count FROM peers").fetchone()['count']
    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    channel_count = conn.execute("SELECT COUNT(*) as count FROM channels").fetchone()['count']
    dm_count = conn.execute("SELECT COUNT(*) as count FROM direct_messages").fetchone()['count']
    conn.close()
    
    return build_json_response(req, {
        "status": "healthy",
        "peers_online": peer_count,
        "total_users": user_count,
        "total_channels": channel_count,
        "total_dms": dm_count,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='HybridChatServer', description='Hybrid P2P Chat Server')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    print("=" * 70)
    print(f"🚀 HYBRID P2P CHAT SERVER - ENHANCED WITH ACCESS CONTROL")
    print("=" * 70)
    print(f"📍 Address: {ip}:{port}")
    print(f"💾 Database: {DB_PATH}")
    print(f"⏰ Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ Features:")
    print(f"   • DM History Storage")
    print(f"   • Channel History")
    print(f"   • Access Control (Private/Public Channels)")
    print(f"   • Synchronized Timestamp")
    print(f"   • Auto Local Timezone Support")
    print("=" * 70)
    
    app.prepare_address(ip, port)
    app.run()