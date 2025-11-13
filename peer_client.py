# peer_client.py
import socket
import threading
import json
import http.client as httplib
import sys
from daemon.weaprous import WeApRous
import urllib.parse
import time # Thêm time
from daemon.response import Response

# --- Cấu hình ---
TRACKER_HOST = '127.0.0.1'
TRACKER_PORT = 8000
MY_HOST = '0.0.0.0'
MY_PORT = 9002  # Nhớ thay đổi cổng này cho mỗi client (9002, 9003...)
BACKEND_HOST = '127.0.0.1'
BACKEND_PORT = 9000 

# --- Biến toàn cục ---
current_channel = "general" # Kênh mặc định
auth_cookie = None # Sẽ lưu cookie (ví dụ: 'session=admin')
my_real_ip = "127.0.0.1" # Sẽ được cập nhật
peer_list = {} # THAY ĐỔI: Dùng dictionary để map username -> (ip, port)
lock = threading.Lock()
app = WeApRous()

# --- 1. P2P API Endpoint (Server của Peer) ---

@app.route('/send-peer', methods=['POST'])
def receive_message(req): 
    """Đây là API P2P mà các peer khác sẽ gọi."""
    
    # --- THAY ĐỔI: Tuân thủ hợp đồng 'chuẩn' ---
    resp = Response(req) # Tạo response object
    
    try:
        data = json.loads(req.body) 
        sender = data.get('sender_username', 'Anonymous')
        channel = data.get('channel', 'general')
        message = data.get('message', '')
        
        if channel == current_channel:
            print(f"\n[{channel}] {sender}: {message}")
            sys.stdout.write(f"[{current_channel}]: ") 
            sys.stdout.flush()
        
        # Trả về 200 OK (với body JSON)
        resp._content = b'{"status": "received"}'
        resp.headers['Content-Type'] = 'application/json'
        return resp.build_response_header(req) + resp._content

    except json.JSONDecodeError:
        # Trả về 400 Bad Request
        resp.status_code = 400
        resp._content = b'{"status": "error", "message": "Invalid JSON"}'
        resp.headers['Content-Type'] = 'application/json'
        return resp.build_response_header(req) + resp._content

# --- 2. Các hàm Client (Gọi Tracker và các Peer khác) ---

def get_my_ip():
    # ... (Hàm này giữ nguyên) ...
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(('10.255.255.255', 1)); IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return IP

def http_request(method, host, port, path, body_bytes=None, headers=None, cookie_str=None):
    # ... (Hàm này giữ nguyên, nó đã hỗ trợ cookie) ...
    try:
        conn = httplib.HTTPConnection(host, port, timeout=5)
        if headers is None: headers = {}
        if cookie_str: headers['Cookie'] = cookie_str
        if body_bytes: headers['Content-Length'] = len(body_bytes)
        
        conn.request(method, path, body_bytes, headers)
        response = conn.getresponse()
        data = response.read()
        set_cookie_header = response.getheader('Set-Cookie')
        conn.close()
        
        print(f"[HTTP Client] {method} {host}:{port}{path} - Status: {response.status}")
        return data, response.status, set_cookie_header
    except Exception as e:
        print(f"[HTTP Client] Lỗi khi kết nối {host}:{port}. Lỗi: {e}")
        return None, 500, None

# ... (các import và cấu hình giữ nguyên) ...

# ... (API /send-peer/ và các hàm http_request, get_my_ip giữ nguyên) ...

def perform_login():
    """(Task 1) HỎI user và thực hiện login để lấy cookie"""
    
    # --- THAY ĐỔI: Dùng input() thay vì hardcode ---
    print("--- Đăng nhập ---")
    username = input("Username: ")
    password = input("Password: ")
    # Gợi ý: ('admin', 'password') hoặc ('user1', '123')
    
    print(f"[Login] Đang đăng nhập với user '{username}'...")
    login_data = {'username': username, 'password': password}
    # --- HẾT THAY ĐỔI ---

    body_bytes = urllib.parse.urlencode(login_data).encode('utf-8')
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    
    data, status, set_cookie_header = http_request("POST", BACKEND_HOST, BACKEND_PORT, "/login", body_bytes=body_bytes, headers=headers)
    
    if status == 200 and set_cookie_header:
        cookie = set_cookie_header.split(';')[0] 
        print(f"[Login] Đăng nhập thành công. Đã nhận cookie: {cookie}")
        return cookie
    else:
        print(f"[Login] Đăng nhập thất bại! (Kiểm tra username/password)")
        return None
    
def perform_logout():
    """(Task 2) Gọi POST /logout/ để xóa peer khỏi Tracker DB."""
    print(f"[Tracker] Đang hủy đăng ký (logout)...")
    
    # --- THAY ĐỔI: Gửi kèm ip/port trong body ---
    payload = {"ip": my_real_ip, "port": MY_PORT}
    body_bytes = json.dumps(payload).encode('utf-8')
    headers = {"Content-type": "application/json"}
    
    data, status, _ = http_request(
        "POST", 
        TRACKER_HOST, 
        TRACKER_PORT, 
        "/logout/", 
        body_bytes=body_bytes,  # <-- Gửi body
        headers=headers,        # <-- Gửi header
        cookie_str=auth_cookie
    )
    # --- HẾT THAY ĐỔI ---

    if status == 200: 
        print("[Tracker] Hủy đăng ký thành công.")
    else: 
        print(f"[Tracker] Hủy đăng ký thất bại.")

def register_with_tracker():
    """(Client-Server) Gọi POST /submit-info/ để đăng ký."""
    print(f"[Tracker] Đang đăng ký với IP {my_real_ip} và cổng {MY_PORT}")
    payload = {"ip": my_real_ip, "port": MY_PORT}
    body_bytes = json.dumps(payload).encode('utf-8')
    headers = {"Content-type": "application/json"}
    
    data, status, _ = http_request("POST", TRACKER_HOST, TRACKER_PORT, "/submit-info/", body_bytes=body_bytes, headers=headers, cookie_str=auth_cookie)
    if status == 200: print("[Tracker] Đăng ký thành công.")
    else: print(f"[Tracker] Đăng ký thất bại. (Status: {status})")

# (trong peer_client.py)
from collections import defaultdict # <-- Thêm import này ở đầu file

def update_peer_list():
    """(Client-Server) Gọi GET /get-list/ và cập nhật dictionary peer."""
    global peer_list
    print("[Tracker] Đang lấy danh sách peer...")
    data, status, _ = http_request("GET", TRACKER_HOST, TRACKER_PORT, "/get-list/", cookie_str=auth_cookie)
    if status != 200: return
        
    try:
        all_peers_list = json.loads(data.decode('utf-8'))
        my_username = auth_cookie.split('=')[1]
        
        with lock:
            # --- THAY ĐỔI: Dùng defaultdict(list) ---
            # peer_list giờ sẽ là: {'admin': [('1.1.1.1', 9001), ('1.1.1.1', 9002)]}
            peer_list = defaultdict(list)
            
            for peer in all_peers_list:
                if peer['username'] != my_username:
                    peer_list[peer['username']].append( (peer['ip'], peer['port']) )

        print(f"[P2P Client] Cập nhật danh sách: có {len(peer_list)} user khác đang online.")
        
    except json.JSONDecodeError:
        print("[Tracker] Lỗi: Tracker trả về JSON không hợp lệ.")

# (trong peer_client.py)

def broadcast_message(message, channel="general"):
    """(P2P) Gửi tin nhắn đến TẤT CẢ các session của TẤT CẢ các peer."""
    
    my_username = auth_cookie.split('=')[1]
    
    # 1. Gửi P2P
    payload = {
        "sender_username": my_username,
        "channel": channel,
        "message": message
    }
    body_bytes = json.dumps(payload).encode('utf-8')
    headers = {"Content-type": "application/json"}
    
    current_peers_dict = {}
    with lock:
        current_peers_dict = dict(peer_list)
    
    print(f"[Broadcast] Đang gửi P2P...")
    
    # --- THAY ĐỔI: Thêm vòng lặp bên trong ---
    total_sessions = 0
    for username, ip_port_list in current_peers_dict.items():
        # ip_port_list là một list, ví dụ: [('1.1.1.1', 9001), ('1.1.1.1', 9002)]
        print(f" -> Gửi cho '{username}' (có {len(ip_port_list)} session)")
        for (peer_ip, peer_port) in ip_port_list:
            http_request("POST", peer_ip, peer_port, "/send-peer", body_bytes=body_bytes, headers=headers)
            total_sessions += 1
    # --- HẾT THAY ĐỔI ---

    print(f"[Broadcast] Đã gửi P2P tới {len(current_peers_dict)} user / {total_sessions} session.")
    
    # 2. Gửi cho Server để LƯU LỊCH SỬ (Giữ nguyên)
    log_payload = {"channel_name": channel, "content": message}
    log_body_bytes = json.dumps(log_payload).encode('utf-8')
    http_request("POST", TRACKER_HOST, TRACKER_PORT, "/log-message/", body_bytes=log_body_bytes, headers=headers, cookie_str=auth_cookie)
# --- Các hàm xử lý lệnh mới ---

def handle_create_channel(command):
    try:
        parts = command.split(' ', 2)
        name = parts[1]
        topic = parts[2] if len(parts) > 2 else ""
        
        payload = {"name": name, "topic": topic}
        body_bytes = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = http_request("POST", TRACKER_HOST, TRACKER_PORT, "/create-channel/", body_bytes=body_bytes, headers=headers, cookie_str=auth_cookie)
        response_data = json.loads(data.decode('utf-8'))
        print(f"[Server] {response_data.get('message')}")
        
    except IndexError:
        print("[Lỗi] Cú pháp: !create <tên_kênh> [chủ đề]")
    except Exception as e:
        print(f"[Lỗi] {e}")

def handle_list_channels():
    print("[Server] Đang lấy danh sách kênh...")
    data, status, _ = http_request("GET", TRACKER_HOST, TRACKER_PORT, "/list-channels/", cookie_str=auth_cookie)
    if status != 200: return

    try:
        channels = json.loads(data.decode('utf-8'))
        print("--- Danh sách kênh ---")
        for c in channels:
            print(f"- #{c['name']} (Chủ đề: {c.get('topic', 'N/A')}, Tạo bởi: {c['owner']})")
        print("----------------------")
    except Exception as e:
        print(f"[Lỗi] {e}")

def handle_join_channel(command):
    global current_channel
    try:
        new_channel = command.split(' ', 1)[1].strip()
        if not new_channel:
            print("[Lỗi] Tên kênh không được rỗng.")
            return

        # 1. Lấy lịch sử
        print(f"[Server] Đang lấy lịch sử kênh #{new_channel}...")
        payload = {"channel_name": new_channel}
        body_bytes = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = http_request("POST", TRACKER_HOST, TRACKER_PORT, "/get-history/", body_bytes=body_bytes, headers=headers, cookie_str=auth_cookie)
        
        # 2. Xóa màn hình (giả lập) và in lịch sử
        print("\n" * 50) # Xóa màn hình
        print(f"--- Chào mừng đến với kênh #{new_channel} ---")
        
        if status == 200:
            history = json.loads(data.decode('utf-8'))
            for msg in history:
                print(f"[{msg['timestamp']}] {msg['username']}: {msg['content']}")
        else:
            response_data = json.loads(data.decode('utf-8'))
            print(f"[Lỗi] Không thể lấy lịch sử: {response_data.get('message')}")

        print(f"----------------------------------------")
        current_channel = new_channel # Chuyển kênh
        
    except IndexError:
        print("[Lỗi] Cú pháp: !join <tên_kênh>")
    except Exception as e:
        print(f"[Lỗi] {e}")


# --- 3. Main ---

if __name__ == "__main__":
    
    # 0. Đăng nhập để lấy Cookie (Task 1)
    auth_cookie = perform_login()
    if not auth_cookie:
        print("Đăng nhập thất bại. Thoát chương trình.")
        sys.exit(1)
    
    my_real_ip = get_my_ip()
    print(f"IP của bạn là: {my_real_ip}")
    print(f"Chạy P2P Server trên cổng: {MY_PORT}")
    
    # 1. Chuẩn bị P2P Server
    app.prepare_address(MY_HOST, MY_PORT)
    server_thread = threading.Thread(target=app.run)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(0.5) # Chờ server P2P khởi động
    
    # 2. Đăng ký với Tracker
    register_with_tracker()
    
    # 3. Lấy danh sách peer lần đầu
    update_peer_list()

    # 4. Tự động tham gia kênh 'general' (và lấy lịch sử)
    handle_join_channel("!join general")
    
    print(f"--- Gõ '!create <kênh>', '!list', '!join <kênh>', 'refresh', 'quit' ---")
    
    # 5. Luồng chính chờ nhập tin nhắn
    try:
        while True:
            message = input(f"[{current_channel}]: ") 
            
            if message.lower() == 'quit':
                perform_logout()
                break
            elif message.lower() == 'refresh':
                update_peer_list()
            elif message.lower().startswith('!create '):
                handle_create_channel(message)
            elif message.lower() == '!list':
                handle_list_channels()
            elif message.lower().startswith('!join '):
                handle_join_channel(message)
            elif message:
                broadcast_message(message, channel=current_channel)
                
    except (EOFError, KeyboardInterrupt):
        print("\nĐang thoát và hủy đăng ký...")
        perform_logout()
    finally:
        print("Đã thoát.")