#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
peer_gui.py - ENHANCED BEAUTIFUL UI WITH CUSTOMTKINTER
Modern, polished interface with visual feedback and smooth interactions
"""

import sys
if sys.version_info[0] == 3:
    import tkinter as tk
    from tkinter import scrolledtext, messagebox, filedialog, simpledialog
    import http.client as httplib
else:
    import Tkinter as tk
    import ScrolledText as scrolledtext
    import tkMessageBox as messagebox
    import httplib

# CustomTkinter import
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("[Warning] CustomTkinter not available. Install with: pip install customtkinter")
    sys.exit(1)

import socket
import threading
import json
import time
from datetime import datetime
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from daemon.weaprous import WeApRous
from daemon.response import Response
from collections import defaultdict
import hashlib

# Desktop notification support
try:
    from plyer import notification as desktop_notify
    DESKTOP_NOTIFY_AVAILABLE = True
except ImportError:
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        DESKTOP_NOTIFY_AVAILABLE = True
    except ImportError:
        DESKTOP_NOTIFY_AVAILABLE = False

TRACKER_HOST = '127.0.0.1'
TRACKER_PORT = 8000
MY_HOST = '0.0.0.0'
AUTO_REFRESH_INTERVAL = 3000

# Set theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 🎨 ENHANCED COLOR PALETTE
class ColorTheme:
    # Main colors
    PRIMARY = "#6366f1"  # Indigo
    PRIMARY_HOVER = "#4f46e5"
    SECONDARY = "#8b5cf6"  # Purple
    SECONDARY_HOVER = "#7c3aed"
    
    # Channel/User selection colors
    CHANNEL_SELECT = "#3b82f6"  # Blue
    CHANNEL_SELECT_HOVER = "#2563eb"
    USER_SELECT = "#10b981"  # Emerald
    USER_SELECT_HOVER = "#059669"
    
    # Status colors
    SUCCESS = "#10b981"
    SUCCESS_HOVER = "#059669"
    WARNING = "#f59e0b"
    WARNING_HOVER = "#d97706"
    ERROR = "#ef4444"
    ERROR_HOVER = "#dc2626"
    
    # UI elements
    BACKGROUND = "#1e1e2e"
    SURFACE = "#2a2a3e"
    SURFACE_SUB = "#181829"
    SURFACE_HOVER = "#363650"
    BORDER = "#3a3a50"
    
    # Text colors
    TEXT_PRIMARY = "#e5e7eb"
    TEXT_SECONDARY = "#9ca3af"
    TEXT_DISABLED = "#6b7280"
    
    # Indicator
    INDICATOR_WIDTH = 4
    INDICATOR_RADIUS = 2

THEME = ColorTheme()


def get_current_time():
    return datetime.now().strftime("%H:%M")


def parse_timestamp(ts_str):
    if not ts_str:
        return get_current_time()
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        return local_dt.strftime("%H:%M")
    except:
        return get_current_time()


def show_desktop_notification(title, message):
    """Show desktop notification"""
    if not DESKTOP_NOTIFY_AVAILABLE:
        return
    
    try:
        desktop_notify.notify(
            title=title,
            message=message,
            app_name='BK Chat',
            timeout=5
        )
    except:
        try:
            toaster.show_toast(title, message, duration=5, threaded=True)
        except:
            pass


class P2PServer:
    def __init__(self, port, message_callback):
        self.port = port
        self.message_callback = message_callback
        self.app = None
        self.is_running = False
        self.server_thread = None
        
    def setup_routes(self):
        self.app = WeApRous()
        app = self.app
        callback = self.message_callback
        
        @app.route('/send-peer', methods=['POST'])
        def receive_message(req):
            resp = Response(req)
            try:
                data = json.loads(req.body)
                sender = data.get('sender_username', 'Anonymous')
                channel = data.get('channel', 'general')
                message = data.get('message', '')
                msg_type = data.get('type', 'channel')
                msg_id = data.get('msg_id', '')
                reaction = data.get('reaction', '')
                typing = data.get('typing', False)
                broadcast = data.get('broadcast', False)
                
                if typing:
                    callback(channel, sender, '', 'typing')
                elif reaction:
                    callback(channel, sender, reaction, 'reaction', msg_id=msg_id)
                elif broadcast:
                    callback(channel, sender, message, 'broadcast', msg_id=msg_id, broadcast=True)
                else:
                    callback(channel, sender, message, msg_type, msg_id=msg_id)
                
                resp._content = b'{"status": "received"}'
                resp.headers['Content-Type'] = 'application/json'
                return resp.build_response_header(req) + resp._content
            except Exception as e:
                print("[P2P] Error: {}".format(e))
                resp.status_code = 400
                resp._content = b'{"status": "error"}'
                resp.headers['Content-Type'] = 'application/json'
                return resp.build_response_header(req) + resp._content
    
    def check_port_available(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except socket.error:
            sock.close()
            return False
    
    def start(self):
        if self.is_running:
            return True
        
        if not self.check_port_available(self.port):
            print("[P2P] Port {} already in use!".format(self.port))
            return False
        
        try:
            self.setup_routes()
            self.is_running = True
            self.app.prepare_address(MY_HOST, self.port)
            
            def run_server():
                try:
                    print("[P2P] Server starting on port {}...".format(self.port))
                    self.app.run()
                except Exception as e:
                    print("[P2P] Error: {}".format(e))
                finally:
                    print("[P2P] Server stopped")
            
            self.server_thread = threading.Thread(target=run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            time.sleep(0.5)
            print("[P2P] Server started successfully!")
            return True
                
        except Exception as e:
            print("[P2P] Failed to start: {}".format(e))
            self.is_running = False
            return False
    
    def stop(self):
        self.is_running = False
        print("[P2P] Server stopped")


class HTTPClient:
    @staticmethod
    def request(method, host, port, path, body_bytes=None, headers=None, cookie_str=None):
        try:
            conn = httplib.HTTPConnection(host, port, timeout=10)
            if headers is None:
                headers = {}
            if cookie_str:
                headers['Cookie'] = cookie_str
            if body_bytes:
                headers['Content-Length'] = str(len(body_bytes))
            
            conn.request(method, path, body_bytes, headers)
            response = conn.getresponse()
            data = response.read()
            set_cookie = response.getheader('Set-Cookie')
            status = response.status
            conn.close()
            
            return data, status, set_cookie
        except Exception as e:
            print("[HTTP] Error: {}".format(e))
            return None, 500, None


class ChatClient:
    def __init__(self, my_port, on_message_received):
        self.my_port = my_port
        self.my_ip = self.get_local_ip()
        self.auth_cookie = None
        self.username = None
        self.user_id = None
        self.current_channel = "general"
        self.current_dm_user = None
        self.peer_list = defaultdict(list)
        self.lock = threading.Lock()
        self.on_message_received = on_message_received
        self.p2p_server = None
        self.user_status = "online"
        self.typing_users = set()
        self.message_cache = {}
        self.unread_messages = defaultdict(int)
        self.unread_messages_channel = defaultdict(int)
        self.channel_permissions = {}
    
    def start_p2p_server(self):
        if self.p2p_server is None:
            self.p2p_server = P2PServer(self.my_port, self._handle_p2p_message)
        
        if not self.p2p_server.start():
            return False
        
        time.sleep(0.5)
        return True
    
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    
    def _handle_p2p_message(self, channel, sender, message, msg_type='channel', **kwargs):
        broadcast = kwargs.get('broadcast', False)
        
        if msg_type == 'typing':
            self.on_message_received('typing', sender, '', 'typing')
        elif msg_type == 'reaction':
            msg_id = kwargs.get('msg_id', '')
            self.on_message_received('reaction', sender, message, 'reaction', msg_id=msg_id)
        elif broadcast:
            msg_id = kwargs.get('msg_id', '')
            self.on_message_received(channel, sender, message, 'broadcast', msg_id=msg_id, broadcast=True)
        elif msg_type == 'dm':
            self.unread_messages[sender] += 1
            self.on_message_received('dm', sender, message, msg_type)
        elif (msg_type == 'channel' and self.current_channel != channel) or self.current_channel == None:
            self.unread_messages_channel[channel] += 1
            print("unread channel:", channel, self.unread_messages_channel[channel])
            msg_id = kwargs.get('msg_id', '')
            self.on_message_received('channel', sender, message, msg_type, msg_id=msg_id)
        elif channel == self.current_channel:
            msg_id = kwargs.get('msg_id', '')
            self.on_message_received(channel, sender, message, msg_type, msg_id=msg_id)
    
    def login(self, username, password):
        payload = {'username': username, 'password': password}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, cookie = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/login",
            body_bytes=body, headers=headers
        )
        
        if status == 200 and cookie:
            self.auth_cookie = cookie.split(';')[0]
            self.username = username
            try:
                response_data = json.loads(data.decode('utf-8'))
                self.user_id = response_data.get('user_id')
            except:
                pass
            return True, "Login successful"
        else:
            try:
                error_msg = json.loads(data.decode('utf-8')).get('message', 'Unknown error')
            except:
                error_msg = "Invalid credentials"
            return False, error_msg
    
    def register_peer(self):
        payload = {"ip": self.my_ip, "port": self.my_port, "status": self.user_status}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/submit-info/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        return status == 200
    
    def update_peer_list(self):
        data, status, _ = HTTPClient.request(
            "GET", TRACKER_HOST, TRACKER_PORT, "/get-list/",
            cookie_str=self.auth_cookie
        )

        if status == 200:
            try:
                peers = json.loads(data.decode('utf-8'))
                with self.lock:
                    old_users = set(self.peer_list.keys())
                    self.peer_list = defaultdict(list)
                    for peer in peers:
                        if peer['username'] != self.username:
                            self.peer_list[peer['username']].append(
                                (peer['ip'], peer['port'])
                            )
                    new_users = set(self.peer_list.keys())
                joined = new_users - old_users
                left = old_users - new_users
                return joined, left
            except:
                return set(), set()
        return set(), set()
    
    def send_broadcast(self, message, channel=None):
        if channel is None:
            channel = self.current_channel
        
        has_access, error_msg = self.check_channel_access(channel, force_refresh=True)
        if not has_access:
            return 0, 0, [], None
        
        with self.lock:
            peers = dict(self.peer_list)
        
        sent_count = 0
        failed_users = []
        
        msg_id = hashlib.md5("{}{}{}".format(
            self.username, message, time.time()
        ).encode()).hexdigest()[:8]
        
        for target_username, sessions in peers.items():
            payload = {
                "sender_username": self.username,
                "channel": channel,
                "message": message,
                "type": "channel",
                "msg_id": msg_id,
                "broadcast": True
            }
            body = json.dumps(payload).encode('utf-8')
            headers = {"Content-type": "application/json"}
            
            user_sent = False
            for ip, port in sessions:
                try:
                    data, status, _ = HTTPClient.request(
                        "POST", ip, port, "/send-peer",
                        body_bytes=body, headers=headers
                    )
                    if status == 200:
                        user_sent = True
                        break
                except:
                    pass
            
            if user_sent:
                sent_count += 1
            else:
                failed_users.append(target_username)
        
        try:
            log_payload = {"channel_name": channel, "content": message}
            log_body = json.dumps(log_payload).encode('utf-8')
            HTTPClient.request(
                "POST", TRACKER_HOST, TRACKER_PORT, "/log-message/",
                body_bytes=log_body, headers=headers, cookie_str=self.auth_cookie
            )
        except:
            pass
        
        return sent_count, len(peers), failed_users, msg_id
    
    def send_message(self, message, channel=None):
        if channel is None:
            channel = self.current_channel
        
        has_access, error_msg = self.check_channel_access(channel, force_refresh=True)
        if not has_access:
            return -1, None
        
        msg_id = hashlib.md5("{}{}{}".format(
            self.username, message, time.time()
        ).encode()).hexdigest()[:8]
        
        payload = {
            "sender_username": self.username,
            "channel": channel,
            "message": message,
            "type": "channel",
            "msg_id": msg_id
        }
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        with self.lock:
            peers = dict(self.peer_list)
        
        sent_count = 0
        for username, sessions in peers.items():
            for ip, port in sessions:
                try:
                    data, status, _ = HTTPClient.request(
                        "POST", ip, port, "/send-peer",
                        body_bytes=body, headers=headers
                    )
                    if status == 200:
                        sent_count += 1
                except:
                    pass
        
        try:
            log_payload = {"channel_name": channel, "content": message}
            log_body = json.dumps(log_payload).encode('utf-8')
            HTTPClient.request(
                "POST", TRACKER_HOST, TRACKER_PORT, "/log-message/",
                body_bytes=log_body, headers=headers, cookie_str=self.auth_cookie
            )
        except:
            pass
        
        return sent_count, msg_id
    
    def send_typing_indicator(self, target_user=None):
        payload = {
            "sender_username": self.username,
            "channel": self.current_channel if not target_user else target_user,
            "type": "channel" if not target_user else "dm",
            "typing": True
        }
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        with self.lock:
            peers = dict(self.peer_list)
        
        if target_user:
            if target_user in peers:
                for ip, port in peers[target_user]:
                    try:
                        HTTPClient.request(
                            "POST", ip, port, "/send-peer",
                            body_bytes=body, headers=headers
                        )
                    except:
                        pass
        else:
            for username, sessions in peers.items():
                for ip, port in sessions:
                    try:
                        HTTPClient.request(
                            "POST", ip, port, "/send-peer",
                            body_bytes=body, headers=headers
                        )
                    except:
                        pass
    
    # khoong dungf
    def send_reaction(self, msg_id, emoji, channel=None):
        if channel is None:
            channel = self.current_channel
        
        payload = {
            "sender_username": self.username,
            "channel": channel,
            "reaction": emoji,
            "msg_id": msg_id,
            "type": "channel"
        }
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        with self.lock:
            peers = dict(self.peer_list)
        
        for username, sessions in peers.items():
            for ip, port in sessions:
                try:
                    HTTPClient.request(
                        "POST", ip, port, "/send-peer",
                        body_bytes=body, headers=headers
                    )
                except:
                    pass
    
    def send_dm(self, target_username, message):
        with self.lock:
            peers = dict(self.peer_list)
        
        if target_username not in peers:
            return False, "User not online"
        
        msg_id = hashlib.md5("{}{}{}".format(
            self.username, message, time.time()
        ).encode()).hexdigest()[:8]
        
        payload = {
            "sender_username": self.username,
            "channel": target_username,
            "message": message,
            "type": "dm",
            "msg_id": msg_id
        }
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        sent_count = 0
        sessions = peers[target_username]
        
        for ip, port in sessions:
            try:
                data, status, _ = HTTPClient.request(
                    "POST", ip, port, "/send-peer",
                    body_bytes=body, headers=headers
                )
                if status == 200:
                    sent_count += 1
            except:
                pass
        
        try:
            log_payload = {
                "receiver": target_username,
                "content": message
            }
            log_body = json.dumps(log_payload).encode('utf-8')
            HTTPClient.request(
                "POST", TRACKER_HOST, TRACKER_PORT, "/log-dm/",
                body_bytes=log_body, headers=headers, cookie_str=self.auth_cookie
            )
        except Exception as e:
            print("[Client] Failed to log DM: {}".format(e))
        
        return (True, "Sent", msg_id) if sent_count > 0 else (False, "Failed", None)
    
    def get_dm_history(self, other_username):
        payload = {"other_user": other_username}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/get-dm-history/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        
        if status == 200:
            try:
                return json.loads(data.decode('utf-8'))
            except:
                return []
        return []
    
    def get_channel_list(self):
        data, status, _ = HTTPClient.request(
            "GET", TRACKER_HOST, TRACKER_PORT, "/list-channels/",
            cookie_str=self.auth_cookie
        )
        
        if status == 200:
            try:
                channels = json.loads(data.decode('utf-8'))
                for ch in channels:
                    self.channel_permissions[ch['name']] = {
                        'owner': ch.get('owner'),
                        'is_private': ch.get('is_private', False),
                        'allowed_users': ch.get('allowed_users', [])
                    }
                return channels
            except:
                return []
        return []
    
    def create_channel(self, name, topic="", is_private=False, allowed_users=None):
        payload = {
            "name": name, 
            "topic": topic,
            "is_private": is_private,
            "allowed_users": allowed_users or [self.username]
        }
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/create-channel/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        
        return status == 200
    
    def check_channel_access(self, channel_name, force_refresh=False):
        if force_refresh or channel_name not in self.channel_permissions:
            self.get_channel_list()
        
        perms = self.channel_permissions.get(channel_name, {})
        
        if not perms.get('is_private', False):
            return True, None
        
        if perms.get('owner') == self.username:
            return True, None
        
        allowed = perms.get('allowed_users', [])
        if self.username in allowed:
            return True, None
        
        return False, "Access denied: You are not a member of this private channel"
    
    def get_channel_history(self, channel):
        has_access, error_msg = self.check_channel_access(channel, force_refresh=True)
        if not has_access:
            return []
        
        payload = {"channel_name": channel}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/get-history/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        
        if status == 200:
            try:
                return json.loads(data.decode('utf-8'))
            except:
                return []
        return []
    
    def add_channel_member(self, channel_name, username):
        payload = {"channel_name": channel_name, "username": username}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/add-channel-member/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        
        if status == 200:
            return True, "Member added successfully"
        else:
            try:
                error_data = json.loads(data.decode('utf-8'))
                return False, error_data.get('message', 'Failed to add member')
            except:
                return False, "Failed to add member"
    
    def remove_channel_member(self, channel_name, username):
        payload = {"channel_name": channel_name, "username": username}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/remove-channel-member/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        
        if status == 200:
            return True, "Member removed successfully"
        else:
            try:
                error_data = json.loads(data.decode('utf-8'))
                return False, error_data.get('message', 'Failed to remove member')
            except:
                return False, "Failed to remove member"
    
    def get_channel_members(self, channel_name):
        payload = {"channel_name": channel_name}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/get-channel-members/",
            body_bytes=body, headers=headers, cookie_str=self.auth_cookie
        )
        
        if status == 200:
            try:
                return json.loads(data.decode('utf-8'))
            except:
                return {"owner": None, "members": []}
        return {"owner": None, "members": []}
    
    def logout(self):
        print("[Client] Logging out...")
        
        payload = {"ip": self.my_ip, "port": self.my_port}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        try:
            HTTPClient.request(
                "POST", TRACKER_HOST, TRACKER_PORT, "/logout/",
                body_bytes=body, headers=headers, cookie_str=self.auth_cookie
            )
        except:
            pass
        
        if self.p2p_server:
            self.p2p_server.stop()


class ChatGUI:
    """🎨 Enhanced Beautiful GUI with CustomTkinter"""
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 BK Chat")
        self.root.geometry("1400x850")
        
        self.client = None
        self.current_channel = "general"
        self.current_view = "channel"
        self.dm_conversations = {}
        
        self.auto_refresh_job = None
        self.typing_job = None
        self.typing_users_display = {}
        
        self.message_reactions = defaultdict(lambda: defaultdict(list))
        self.all_messages = []
        
        # Selection tracking
        self.selected_channel_btn = None
        self.selected_user_btn = None
        
        self.show_login_screen()
    
    def find_available_port(self, start_port=9002, max_attempts=100):
        for port in range(start_port, start_port + max_attempts):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('0.0.0.0', port))
                sock.close()
                return port
            except socket.error:
                sock.close()
                continue
        return start_port
    
    def show_login_screen(self):
        self.clear_window()
        
        # Main container with gradient effect
        main_frame = ctk.CTkFrame(self.root, fg_color=THEME.BACKGROUND)
        main_frame.pack(expand=True, fill="both")
        
        # Login card with shadow effect
        login_card = ctk.CTkFrame(
            main_frame, 
            width=520, 
            height=720, 
            corner_radius=20,
            fg_color=THEME.SURFACE,
            border_width=1,
            border_color=THEME.BORDER
        )
        login_card.place(relx=0.5, rely=0.5, anchor="center")
        
        # Header with icon
        header_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        header_frame.pack(pady=(40, 20))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🚀 BK CHAT",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=THEME.PRIMARY
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Modern Hybrid P2P Communication",
            font=ctk.CTkFont(size=14),
            text_color=THEME.TEXT_SECONDARY
        )
        subtitle_label.pack(pady=8)
        
        # Features grid
        features_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        features_frame.pack(pady=15)
        
        features = [
            "✨ Real-time messaging",
            "🎭 Emoji reactions",
            "⌨️ Typing indicators",
            "📢 Channel broadcast",
            "🔔 Desktop notifications",
            "🔒 Access control"
        ]
        
        for i, feature in enumerate(features):
            row = i // 2
            col = i % 2
            feature_label = ctk.CTkLabel(
                features_frame,
                text=feature,
                font=ctk.CTkFont(size=11),
                text_color=THEME.TEXT_SECONDARY
            )
            feature_label.grid(row=row, column=col, padx=20, pady=3, sticky="w")
        
        # Server status
        self.check_tracker_status(login_card)
        
        # Input fields with enhanced styling
        input_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        input_frame.pack(pady=20, padx=40, fill="x")
        
        ctk.CTkLabel(
            input_frame,
            text="Username",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(10, 5))
        
        self.username_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Enter your username",
            height=40,
            font=ctk.CTkFont(size=13),
            border_width=2,
            corner_radius=10
        )
        self.username_entry.pack(fill="x")
        
        ctk.CTkLabel(
            input_frame,
            text="Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(15, 5))
        
        self.password_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Enter your password",
            show="●",
            height=40,
            font=ctk.CTkFont(size=13),
            border_width=2,
            corner_radius=10
        )
        self.password_entry.pack(fill="x")
        
        ctk.CTkLabel(
            input_frame,
            text="P2P Port",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(15, 5))
        
        port_container = ctk.CTkFrame(input_frame, fg_color="transparent")
        port_container.pack(fill="x")
        
        self.port_entry = ctk.CTkEntry(
            port_container,
            placeholder_text="Port number",
            height=40,
            font=ctk.CTkFont(size=13),
            width=260,
            border_width=2,
            corner_radius=10
        )
        self.port_entry.insert(0, str(self.find_available_port()))
        self.port_entry.pack(side="left")
        
        find_port_btn = ctk.CTkButton(
            port_container,
            text="🔍 Find",
            width=80,
            height=40,
            command=self.auto_find_port,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME.SECONDARY,
            hover_color=THEME.SECONDARY_HOVER,
            corner_radius=10
        )
        find_port_btn.pack(side="left", padx=(10, 0))
        
        # Buttons with enhanced styling
        btn_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        login_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Login",
            width=160,
            height=45,
            command=self.do_login,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME.SUCCESS,
            hover_color=THEME.SUCCESS_HOVER,
            corner_radius=12
        )
        login_btn.pack(side="left", padx=5)
        
        register_btn = ctk.CTkButton(
            btn_frame,
            text="📝 Register",
            width=160,
            height=45,
            command=self.do_register,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME.PRIMARY,
            hover_color=THEME.PRIMARY_HOVER,
            corner_radius=12
        )
        register_btn.pack(side="left", padx=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            login_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=THEME.ERROR
        )
        self.status_label.pack(pady=10)
    
    def check_tracker_status(self, parent):
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(pady=15)
        
        ctk.CTkLabel(
            status_frame,
            text="Tracker Server:",
            font=ctk.CTkFont(size=11),
            text_color=THEME.TEXT_SECONDARY
        ).pack(side="left", padx=5)
        
        try:
            data, status, _ = HTTPClient.request(
                "GET", TRACKER_HOST, TRACKER_PORT, "/health"
            )
            
            if status == 200:
                status_indicator = ctk.CTkLabel(
                    status_frame,
                    text="●",
                    font=ctk.CTkFont(size=16),
                    text_color=THEME.SUCCESS
                )
                status_indicator.pack(side="left")
                
                ctk.CTkLabel(
                    status_frame,
                    text="Online",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=THEME.SUCCESS
                ).pack(side="left", padx=5)
                
                try:
                    health = json.loads(data.decode('utf-8'))
                    info_text = "({} users, {} peers)".format(
                        health.get('total_users', 0),
                        health.get('peers_online', 0)
                    )
                    ctk.CTkLabel(
                        status_frame,
                        text=info_text,
                        font=ctk.CTkFont(size=10),
                        text_color=THEME.TEXT_SECONDARY
                    ).pack(side="left")
                except:
                    pass
            else:
                status_indicator = ctk.CTkLabel(
                    status_frame,
                    text="●",
                    font=ctk.CTkFont(size=16),
                    text_color=THEME.ERROR
                )
                status_indicator.pack(side="left")
                
                ctk.CTkLabel(
                    status_frame,
                    text="Offline",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=THEME.ERROR
                ).pack(side="left", padx=5)
        except:
            status_indicator = ctk.CTkLabel(
                status_frame,
                text="●",
                font=ctk.CTkFont(size=16),
                text_color=THEME.ERROR
            )
            status_indicator.pack(side="left")
            
            ctk.CTkLabel(
                status_frame,
                text="Offline",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=THEME.ERROR
            ).pack(side="left", padx=5)
    
    def auto_find_port(self):
        port = self.find_available_port()
        self.port_entry.delete(0, "end")
        self.port_entry.insert(0, str(port))
        self.status_label.configure(
            text="✓ Found port: {}".format(port),
            text_color=THEME.SUCCESS
        )
    
    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not username or not password or not port:
            self.status_label.configure(
                text="⚠ All fields required",
                text_color=THEME.WARNING
            )
            return
        
        try:
            port = int(port)
        except:
            self.status_label.configure(
                text="⚠ Invalid port number",
                text_color=THEME.WARNING
            )
            return
        
        self.client = ChatClient(port, self.on_message_received)
        
        self.status_label.configure(
            text="🔄 Starting P2P server...",
            text_color=THEME.PRIMARY
        )
        self.root.update()
        
        self.status_label.configure(
            text="🔄 Logging in...",
            text_color=THEME.PRIMARY
        )
        self.root.update()
        
        success, msg = self.client.login(username, password)
        
        if success:
            if not self.client.start_p2p_server():
                self.status_label.configure(
                    text="✗ Port {} in use! Try another".format(port),
                    text_color=THEME.ERROR
                )
                self.client = None
                return
            
            self.status_label.configure(
                text="🔄 Registering peer...",
                text_color=THEME.PRIMARY
            )
            self.root.update()
            
            if not self.client.register_peer():
                self.status_label.configure(
                    text="✗ Failed to register",
                    text_color=THEME.ERROR
                )
                if self.client.p2p_server:
                    self.client.p2p_server.stop()
                self.client = None
                return
            
            self.client.update_peer_list()
            self.show_chat_screen()
        else:
            self.status_label.configure(text="✗ " + msg, text_color=THEME.ERROR)
            if self.client and self.client.p2p_server:
                self.client.p2p_server.stop()
            self.client = None
    
    def do_register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.status_label.configure(
                text="⚠ Username and password required",
                text_color=THEME.WARNING
            )
            return
        
        self.status_label.configure(
            text="🔄 Registering...",
            text_color=THEME.PRIMARY
        )
        self.root.update()
        
        payload = {'username': username, 'password': password}
        body = json.dumps(payload).encode('utf-8')
        headers = {"Content-type": "application/json"}
        
        data, status, _ = HTTPClient.request(
            "POST", TRACKER_HOST, TRACKER_PORT, "/register",
            body_bytes=body, headers=headers
        )
        
        if status == 200:
            self.status_label.configure(
                text="✓ Registration successful! Please login.",
                text_color=THEME.SUCCESS
            )
        elif status == 401:
            self.status_label.configure(
                text="✗ Username already exists!",
                text_color=THEME.ERROR
            )
        else:
            try:
                error_data = json.loads(data.decode('utf-8'))
                error_msg = error_data.get('message', 'Registration failed')
                self.status_label.configure(
                    text="✗ {}".format(error_msg),
                    text_color=THEME.ERROR
                )
            except:
                self.status_label.configure(
                    text="✗ Registration failed",
                    text_color=THEME.ERROR
                )
    
    def show_chat_screen(self):
        self.clear_window()
        
        # Main container
        main_container = ctk.CTkFrame(self.root, fg_color=THEME.BACKGROUND)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # ===== SIDEBAR =====
        sidebar = ctk.CTkFrame(
            main_container, 
            width=300, 
            corner_radius=15,
            fg_color=THEME.SURFACE,
            border_width=1,
            border_color=THEME.BORDER
        )
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar.grid_rowconfigure(3, weight=1)
        sidebar.grid_rowconfigure(6, weight=1)
        
        # Profile section with avatar
        profile_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        profile_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        # Avatar with gradient effect
        avatar = ctk.CTkFrame(
            profile_frame, 
            width=55, 
            height=55, 
            corner_radius=27,
            fg_color=THEME.SECONDARY,
            border_width=2,
            border_color=THEME.PRIMARY
        )
        avatar.pack(side="left", padx=(0, 12))
        avatar.pack_propagate(False)
        
        ctk.CTkLabel(
            avatar,
            text=self.client.username[0].upper(),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        info = ctk.CTkFrame(profile_frame, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(
            info, 
            text=self.client.username, 
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x")
        
        self.user_status_label = ctk.CTkLabel(
            info, 
            text="● Online", 
            font=ctk.CTkFont(size=11),
            text_color=THEME.SUCCESS
        )
        self.user_status_label.pack(anchor="w")
        
        # Search bar with icon
        search_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search messages...",
            height=38,
            border_width=2,
            corner_radius=10
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        
        # Channels section
        channels_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        channels_header.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        
        ctk.CTkLabel(
            channels_header,
            text="💬 CHANNELS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME.TEXT_SECONDARY
        ).pack(side="left")
        
        # Channels scrollable area
        channels_scroll = ctk.CTkScrollableFrame(
            sidebar,
            height=260,
            fg_color=THEME.SURFACE_SUB
        )
        channels_scroll.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.channels_container = channels_scroll
        self.channel_buttons = []
        
        # Add channel button
        add_channel_btn = ctk.CTkButton(
            sidebar,
            text="➕ Create Channel",
            height=38,
            command=self.create_channel_dialog,
            fg_color=THEME.SECONDARY,
            hover_color=THEME.SECONDARY_HOVER,
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        add_channel_btn.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        
        # Users section
        users_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        users_header.grid(row=5, column=0, sticky="ew", padx=20, pady=(10, 8))
        
        ctk.CTkLabel(
            users_header,
            text="👥 ONLINE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME.TEXT_SECONDARY
        ).pack(side="left")
        
        self.online_count_label = ctk.CTkLabel(
            users_header,
            text="(0)",
            font=ctk.CTkFont(size=10),
            text_color=THEME.TEXT_SECONDARY
        )
        self.online_count_label.pack(side="left", padx=5)
        
        # Users scrollable area
        users_scroll = ctk.CTkScrollableFrame(
            sidebar,
            height=200,
            fg_color=THEME.SURFACE_SUB
        )
        users_scroll.grid(row=6, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.users_container = users_scroll
        self.user_buttons = []
        
        # Bottom action buttons
        btn_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_container.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            btn_container,
            text="📢 Broadcast",
            height=38,
            command=self.show_broadcast_dialog,
            fg_color=THEME.WARNING,
            hover_color=THEME.WARNING_HOVER,
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(fill="x", pady=3)
        
        ctk.CTkButton(
            btn_container,
            text="🔄 Refresh",
            height=38,
            command=self.refresh_all,
            fg_color=THEME.PRIMARY,
            hover_color=THEME.PRIMARY_HOVER,
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(fill="x", pady=3)
        
        ctk.CTkButton(
            btn_container,
            text="🚪 Logout",
            height=38,
            command=self.do_logout,
            fg_color=THEME.ERROR,
            hover_color=THEME.ERROR_HOVER,
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(fill="x", pady=3)
        
        # ===== CHAT AREA =====
        chat_container = ctk.CTkFrame(
            main_container,
            corner_radius=15,
            fg_color=THEME.SURFACE,
            border_width=1,
            border_color=THEME.BORDER
        )
        chat_container.grid(row=0, column=1, sticky="nsew")
        chat_container.grid_rowconfigure(1, weight=1)
        chat_container.grid_columnconfigure(0, weight=1)
        
        # Chat header with gradient
        header = ctk.CTkFrame(
            chat_container,
            height=75,
            corner_radius=0,
            fg_color=THEME.SURFACE,
            border_width=0
        )
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)
        
        # Separator line
        separator = ctk.CTkFrame(header, height=2, fg_color=THEME.BORDER)
        separator.place(relx=0, rely=1, relwidth=1, anchor="sw")
        
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.grid(row=0, column=0, sticky="w", padx=25, pady=15)
        
        self.channel_label = ctk.CTkLabel(
            header_left,
            text="# general",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        )
        self.channel_label.pack(side="left")
        
        self.channel_lock_icon = ctk.CTkLabel(
            header_left,
            text="",
            font=ctk.CTkFont(size=18),
            text_color=THEME.TEXT_SECONDARY
        )
        self.channel_lock_icon.pack(side="left", padx=8)
        
        self.typing_label = ctk.CTkLabel(
            header_left,
            text="",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=THEME.TEXT_SECONDARY
        )
        self.typing_label.pack(side="left", padx=15)
        
        # Header right
        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.grid(row=0, column=1, sticky="e", padx=25, pady=15)
        
        self.peer_count_label = ctk.CTkLabel(
            header_right,
            text="0 users online",
            font=ctk.CTkFont(size=11),
            text_color=THEME.TEXT_SECONDARY
        )
        self.peer_count_label.pack()
        
        self.port_label = ctk.CTkLabel(
            header_right,
            text="Port: {}".format(self.client.my_port),
            font=ctk.CTkFont(size=10),
            text_color=THEME.TEXT_DISABLED
        )
        self.port_label.pack()
        
        # Messages area
        messages_frame = ctk.CTkFrame(
            chat_container,
            corner_radius=0,
            fg_color=THEME.BACKGROUND
        )
        messages_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        
        self.message_display = ctk.CTkTextbox(
            messages_frame,
            font=ctk.CTkFont(size=13),
            wrap="word",
            state="disabled",
            corner_radius=10
        )
        self.message_display.pack(fill="both", expand=True)
        
        # Configure message tags with enhanced styling
        self.message_display._textbox.tag_config(
            "sender",
            foreground=THEME.SECONDARY,
            font=("Segoe UI", 13, "bold")
        )
        self.message_display._textbox.tag_config(
            "dm_sent",
            foreground=THEME.SECONDARY,
            font=("Segoe UI", 13, "bold")
        )
        self.message_display._textbox.tag_config(
            "dm_recv",
            foreground=THEME.PRIMARY,
            font=("Segoe UI", 13, "bold")
        )
        self.message_display._textbox.tag_config(
            "system",
            foreground=THEME.TEXT_DISABLED,
            font=("Segoe UI", 11, "italic")
        )
        self.message_display._textbox.tag_config(
            "broadcast",
            foreground=THEME.WARNING,
            font=("Segoe UI", 13, "bold")
        )
        self.message_display._textbox.tag_config(
            "timestamp",
            foreground=THEME.TEXT_DISABLED,
            font=("Segoe UI", 10)
        )
        self.message_display._textbox.tag_config(
            "reaction",
            foreground=THEME.SECONDARY,
            font=("Segoe UI", 11)
        )
        self.message_display._textbox.tag_config(
            "search_highlight",
            background="#FFD700",
            foreground="#000000"
        )
        
        # Emoji bar with hover effects
        emoji_frame = ctk.CTkFrame(
            chat_container,
            height=55,
            corner_radius=0,
            fg_color="transparent"
        )
        emoji_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        emoji_frame.grid_propagate(False)
        
        emoji_list = ["😀", "😂", "❤️", "👍", "👎", "🎉", "🔥", "✨", "💯", "🚀"]
        for emoji in emoji_list:
            emoji_btn = ctk.CTkButton(
                emoji_frame,
                text=emoji,
                width=45,
                height=40,
                font=ctk.CTkFont(size=18),
                fg_color="transparent",
                hover_color=THEME.SURFACE_HOVER,
                corner_radius=8,
                command=lambda e=emoji: self.insert_emoji(e)
            )
            emoji_btn.pack(side="left", padx=4)
        
        # Input area with send button
        input_frame = ctk.CTkFrame(
            chat_container,
            height=65,
            corner_radius=0,
            fg_color="transparent"
        )
        input_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_propagate(False)
        
        self.message_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message...",
            height=50,
            font=ctk.CTkFont(size=13),
            border_width=2,
            corner_radius=12
        )
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        self.message_entry.bind('<KeyRelease>', self._on_typing)
        
        send_btn = ctk.CTkButton(
            input_frame,
            text="📤 Send",
            width=110,
            height=50,
            command=self.send_message,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.SUCCESS,
            hover_color=THEME.SUCCESS_HOVER,
            corner_radius=12
        )
        send_btn.grid(row=0, column=1)
        
        # Initialize
        self.refresh_channels()
        self.refresh_users()
        self.join_channel("general")
        self.start_auto_refresh()
    
    def create_list_item(self, parent, text, icon, on_click, item_type="channel"):
        """Create a beautiful list item with indicator and hover effects"""
        # Container frame
        item_frame = ctk.CTkFrame(parent, fg_color="transparent", height=42)
        item_frame.pack(fill="x", pady=2)
        item_frame.pack_propagate(False)
        
        # Left indicator bar (hidden by default)
        indicator = ctk.CTkFrame(
            item_frame,
            width=THEME.INDICATOR_WIDTH,
            corner_radius=THEME.INDICATOR_RADIUS,
            fg_color="transparent"
        )
        indicator.pack(side="left", fill="y", padx=(0, 8))
        
        # Main button
        btn = ctk.CTkButton(
            item_frame,
            text="{} {}".format(icon, text),
            height=42,
            anchor="w",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=THEME.SURFACE_HOVER,
            border_width=0,
            corner_radius=8,
            command=on_click
        )
        btn.pack(side="left", fill="both", expand=True)
        
        # Store references
        btn._indicator = indicator
        btn._item_type = item_type
        btn._item_text = text
        
        return btn
    
    def select_list_item(self, btn, item_type):
        """Apply selection styling to a list item with safe de-selection checks"""

        def safe_clear(old_btn):
            if old_btn and old_btn.winfo_exists():
                try:
                    old_btn.configure(fg_color="transparent")
                    old_btn._indicator.configure(fg_color="transparent")
                except:
                    pass
            return None

        if item_type == "channel":
            # Clear old channel selection
            self.selected_channel_btn = safe_clear(self.selected_channel_btn)

            # Also clear user selection
            self.selected_user_btn = safe_clear(self.selected_user_btn)

            self.selected_channel_btn = btn
            color = THEME.CHANNEL_SELECT

        else:   # item_type == "user"
            # Clear old user selection
            self.selected_user_btn = safe_clear(self.selected_user_btn)

            # Clear channel selection
            self.selected_channel_btn = safe_clear(self.selected_channel_btn)

            self.selected_user_btn = btn
            color = THEME.USER_SELECT

        # Apply new selected style
        if btn and btn.winfo_exists():
            btn.configure(fg_color=color)
            btn._indicator.configure(fg_color=color)
    
    def refresh_channels(self):
        """Refresh channel list with beautiful styling"""
        for widget in self.channels_container.winfo_children():
            widget.destroy()
        self.channel_buttons = []
        
        channels = self.client.get_channel_list()
        
        # Track current channel to restore selection
        current_ch = self.current_channel if self.current_view == "channel" else None
        
        for ch in channels:
            is_private = ch.get('is_private', False)
            unread = self.client.unread_messages_channel.get(ch['name'], 0)
            if unread > 0:
                icon = "💬"
            elif is_private:
                is_owner = ch.get('owner') == self.client.username
                is_member = self.client.username in ch.get('allowed_users', [])
                
                if is_owner or is_member:
                    icon = "🔓"
                else:
                    icon = "🔒"
            else:
                icon = "#"
            
            # Create button with click handler
            btn = self.create_list_item(
                self.channels_container,
                ch['name'] if icon != "💬" else ch['name'] + " [{}]".format(unread),
                icon,
                lambda name=ch['name']: self.on_channel_click(name),
                "channel"
            )
            btn._channel_name = ch['name']
            self.channel_buttons.append(btn)
            
            # Restore selection if this was the current channel
            if current_ch and ch['name'] == current_ch:
                self.select_list_item(btn, "channel")
            
            # Add right-click menu for private channels
            if is_private and (is_owner or is_member):
                btn.bind("<Button-3>", lambda e, name=ch['name']: self.show_channel_context_menu(e, name))
    
    def refresh_users(self):
        """Refresh user list with beautiful styling"""
        for widget in self.users_container.winfo_children():
            widget.destroy()
        self.user_buttons = []
        
        self.client.update_peer_list()
        
        with self.client.lock:
            users = sorted(self.client.peer_list.keys())
        
        # Track current DM user to restore selection
        current_dm = self.client.current_dm_user if self.current_view == "dm" else None
        
        for user in users:
            session_count = len(self.client.peer_list[user])
            unread = self.client.unread_messages.get(user, 0)
            
            # Build display text
            if unread > 0:
                if session_count > 1:
                    display_text = "{} ({}) [{}]".format(user, session_count, unread)
                else:
                    display_text = "{} [{}]".format(user, unread)
                icon = "💬"
            else:
                if session_count > 1:
                    display_text = "{} ({})".format(user, session_count)
                else:
                    display_text = user
                icon = "👤"
            
            # Create button
            btn = self.create_list_item(
                self.users_container,
                display_text,
                icon,
                lambda u=user: self.on_user_click(u),
                "user"
            )
            btn._username = user
            self.user_buttons.append(btn)
            
            # Restore selection if this was the current DM user
            if current_dm and user == current_dm:
                self.select_list_item(btn, "user")
        
        # Update counts
        total_sessions = sum(len(sessions) for sessions in self.client.peer_list.values())
        
        if len(users) > 0:
            self.peer_count_label.configure(
                text="{} users / {} sessions".format(len(users), total_sessions)
            )
            self.online_count_label.configure(text="({})".format(len(users)))
        else:
            self.peer_count_label.configure(text="No users online")
            self.online_count_label.configure(text="(0)")
    
    def on_channel_click(self, channel_name):
        """Handle channel selection"""
        # Find and select button
        for btn in self.channel_buttons:
            if hasattr(btn, '_channel_name') and btn._channel_name == channel_name:
                self.select_list_item(btn, "channel")
                break
        
        # Join channel
        self.join_channel(channel_name)
    
    def on_user_click(self, username):
        """Handle user selection"""
        # Find and select button
        for btn in self.user_buttons:
            if hasattr(btn, '_username') and btn._username == username:
                self.select_list_item(btn, "user")
                break
        
        # Open DM
        self.open_dm(username)
    
    def refresh_all(self):
        self.refresh_channels()
        self.refresh_users()
        self.display_message("System", "✓ Lists refreshed", "system")
    
    def show_channel_context_menu(self, event, channel_name):
        perms = self.client.channel_permissions.get(channel_name, {})
        is_owner = perms.get('owner') == self.client.username
        
        if is_owner:
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(
                label="👥 Manage Members",
                command=lambda: self.show_channel_members_dialog(channel_name)
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
    
    def join_channel(self, channel):
        has_access, error_msg = self.client.check_channel_access(channel, force_refresh=True)
        
        if not has_access:
            messagebox.showerror("Access Denied", "🔒 " + error_msg)
            if channel == self.current_channel:
                self.display_message("System", 
                    "⚠️ You have been removed from #{} and redirected to #general".format(channel), 
                    "system")
                self.join_channel("general")
            return
        
        self.current_channel = channel
        self.current_view = "channel"
        self.client.current_channel = channel
        self.client.unread_messages_channel[channel] = 0
        self.client.current_dm_user = None
        
        self.root.after(0, self.refresh_channels)
        
        perms = self.client.channel_permissions.get(channel, {})
        is_private = perms.get('is_private', False)
        
        self.channel_label.configure(text="# " + channel)
        
        if is_private:
            is_owner = perms.get('owner') == self.client.username
            is_member = self.client.username in perms.get('allowed_users', [])
            
            if is_owner or is_member:
                self.channel_lock_icon.configure(text="🔓")
            else:
                self.channel_lock_icon.configure(text="🔒")
        else:
            self.channel_lock_icon.configure(text="")
        
        self.message_display.configure(state="normal")
        self.message_display.delete("1.0", "end")
        self.message_display.configure(state="disabled")
        
        self.all_messages = []
        
        history = self.client.get_channel_history(channel)
        
        if not history and is_private:
            has_access, error_msg = self.client.check_channel_access(channel, force_refresh=True)
            if not has_access:
                messagebox.showerror("Access Denied", "🔒 " + error_msg)
                self.join_channel("general")
                return
        
        for msg in history:
            sender = msg['username']
            if sender == self.client.username:
                sender = "You"
            
            self.display_message(
                sender,
                msg['content'],
                "channel",
                timestamp=msg.get('timestamp', '')
            )
        
        if is_private:
            if perms.get('owner') == self.client.username:
                self.display_message("System", "🔓 Private channel (You are the owner)", "system")
            else:
                self.display_message("System", "🔓 Private channel (Member access)", "system")
    
    def open_dm(self, username):
        self.current_view = "dm"
        self.client.current_dm_user = username
        
        self.current_channel = None
        self.client.current_channel = None
        
        self.client.unread_messages[username] = 0
        self.refresh_users()
        
        self.channel_label.configure(text="@ " + username)
        self.channel_lock_icon.configure(text="")
        
        self.message_display.configure(state="normal")
        self.message_display.delete("1.0", "end")
        self.message_display.configure(state="disabled")
        
        self.all_messages = []
        
        history = self.client.get_dm_history(username)
        
        for msg in history:
            sender = msg.get('sender', '')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            if sender == self.client.username:
                self.display_message("You", content, "dm_sent", timestamp=timestamp)
            else:
                self.display_message(sender, content, "dm_recv", timestamp=timestamp)
        
        if username not in self.dm_conversations:
            self.dm_conversations[username] = []
    
    def create_channel_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create New Channel")
        dialog.geometry("550x790")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (395)
        dialog.geometry('+{}+{}'.format(x, y))
        
        # Configure dialog style
        dialog.configure(fg_color=THEME.SURFACE)
        
        # Content
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=20)
        
        ctk.CTkLabel(
            content,
            text="Create New Channel",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=THEME.TEXT_PRIMARY
        ).pack(pady=(0, 20))
        
        ctk.CTkLabel(
            content,
            text="Channel Name",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(10, 5))
        
        name_entry = ctk.CTkEntry(
            content,
            placeholder_text="Enter channel name",
            height=40,
            font=ctk.CTkFont(size=13),
            border_width=2,
            corner_radius=10
        )
        name_entry.pack(fill="x")
        name_entry.focus()
        
        ctk.CTkLabel(
            content,
            text="Topic (optional)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(15, 5))
        
        topic_entry = ctk.CTkEntry(
            content,
            placeholder_text="What's this channel about?",
            height=40,
            font=ctk.CTkFont(size=13),
            border_width=2,
            corner_radius=10
        )
        topic_entry.pack(fill="x")
        
        # Access control
        is_private_var = tk.BooleanVar(value=False)
        
        access_frame = ctk.CTkFrame(content, fg_color=THEME.BACKGROUND, corner_radius=10)
        access_frame.pack(fill="x", pady=15)
        
        private_check = ctk.CTkCheckBox(
            access_frame,
            text="🔒 Private Channel (Access Control)",
            variable=is_private_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY
        )
        private_check.pack(anchor="w", padx=15, pady=12)
        
        
        # Members section
        members_section = ctk.CTkFrame(content, fg_color=THEME.BACKGROUND, corner_radius=10)
        members_section.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(
            members_section,
            text="Add Members (optional):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", padx=15, pady=(15, 5))
        
        # Available users (online users)
        users_frame = ctk.CTkFrame(members_section, fg_color=THEME.SURFACE_SUB, corner_radius=8)
        users_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        ctk.CTkLabel(
            users_frame,
            text="Online Users (click to add):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 5))
        
        users_scroll = ctk.CTkScrollableFrame(users_frame, height=80)
        users_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        selected_members = [self.client.username]
        user_buttons_dict = {}
        
        def update_user_buttons():
            for username, btn in user_buttons_dict.items():
                if username in selected_members:
                    btn.configure(fg_color=THEME.USER_SELECT, hover_color=THEME.USER_SELECT_HOVER)
                else:
                    btn.configure(fg_color="transparent", hover_color=THEME.SURFACE_HOVER)
        
        def toggle_user(username):
            if username in selected_members:
                selected_members.remove(username)
            else:
                selected_members.append(username)
            update_user_buttons()
        
        # Populate online users
        with self.client.lock:
            online_users = sorted(self.client.peer_list.keys())
        
        for user in online_users:
            if user != self.client.username:
                btn = ctk.CTkButton(
                    users_scroll,
                    text="👤 {}".format(user),
                    height=32,
                    anchor="w",
                    fg_color="transparent",
                    hover_color=THEME.SURFACE_HOVER,
                    corner_radius=8,
                    font=ctk.CTkFont(size=11),
                    command=lambda u=user: toggle_user(u)
                )
                btn.pack(fill="x", pady=2)
                user_buttons_dict[user] = btn
        
        # Bottom action buttons
        btn_container = ctk.CTkFrame(content, fg_color="transparent")
        btn_container.pack(pady=20)
        
        def create():
            name = name_entry.get().strip()
            topic = topic_entry.get().strip()
            is_private = is_private_var.get()
            
            if name:
                if self.client.create_channel(name, topic, is_private, selected_members):
                    self.refresh_channels()
                    dialog.destroy()
                    icon = "🔒" if is_private else "✅"
                    member_info = " with {} members".format(len(selected_members)) if len(selected_members) > 1 else ""
                    messagebox.showinfo("Success", "{} Channel '{}' created!{}".format(icon, name, member_info))
                else:
                    messagebox.showerror("Error", "✗ Failed to create channel")
        
        create_btn = ctk.CTkButton(
            btn_container,
            text="✅ Create Channel",
            width=180,
            height=45,
            command=create,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.SUCCESS,
            hover_color=THEME.SUCCESS_HOVER,
            corner_radius=12
        )
        create_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_container,
            text="✖️ Cancel",
            width=180,
            height=45,
            command=dialog.destroy,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.ERROR,
            hover_color=THEME.ERROR_HOVER,
            corner_radius=12
        )
        cancel_btn.pack(side="left", padx=5)
    
    def show_broadcast_dialog(self):
        has_access, error_msg = self.client.check_channel_access(
            self.current_channel,
            force_refresh=True
        )
        
        if not has_access:
            messagebox.showerror("Access Denied", 
                "🔒 Cannot broadcast to #{}: {}".format(self.current_channel, error_msg))
            return
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("📢 Broadcast to Channel")
        dialog.geometry("580x500")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=THEME.SURFACE)
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (250)
        dialog.geometry('+{}+{}'.format(x, y))
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Header
        ctk.CTkLabel(
            content,
            text="📢",
            font=ctk.CTkFont(size=48)
        ).pack()
        
        ctk.CTkLabel(
            content,
            text="Broadcast to Channel",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=THEME.TEXT_PRIMARY
        ).pack(pady=(10, 20))
        
        # Channel info
        info_frame = ctk.CTkFrame(content, fg_color=THEME.BACKGROUND, corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        
        with self.client.lock:
            peer_count = len(self.client.peer_list)
        
        ctk.CTkLabel(
            info_frame,
            text="📢 All {} online peers will receive this in the channel".format(peer_count),
            font=ctk.CTkFont(size=11),
            text_color=THEME.TEXT_SECONDARY
        ).pack(pady=5)
        
        ctk.CTkLabel(
            info_frame,
            text="✨ This is a TRUE channel broadcast (P2P)",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color=THEME.TEXT_SECONDARY
        ).pack(pady=(0, 12))
        
        # Message input
        ctk.CTkLabel(
            content,
            text="Message:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(10, 5))
        
        message_entry = ctk.CTkEntry(
            content,
            placeholder_text="Type your broadcast message...",
            height=50,
            font=ctk.CTkFont(size=13),
            border_width=2,
            corner_radius=10
        )
        message_entry.pack(fill="x")
        message_entry.focus()
        
        status_label = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(size=11)
        )
        status_label.pack(pady=10)
        
        def send_broadcast():
            message = message_entry.get().strip()
            if not message:
                status_label.configure(
                    text="⚠️ Please enter a message",
                    text_color=THEME.WARNING
                )
                return
            
            has_access, error_msg = self.client.check_channel_access(
                self.current_channel,
                force_refresh=True
            )
            
            if not has_access:
                messagebox.showerror("Access Denied", "🔒 " + error_msg)
                dialog.destroy()
                return
            
            status_label.configure(
                text="📤 Broadcasting to channel...",
                text_color=THEME.PRIMARY
            )
            dialog.update()
            
            sent_count, total_peers, failed_users, msg_id = self.client.send_broadcast(
                message, self.current_channel
            )
            
            if sent_count == 0 and total_peers == 0:
                status_label.configure(
                    text="✅ Broadcast sent (no peers online)",
                    text_color=THEME.SUCCESS
                )
            
            self.display_message(
                "You (BROADCAST)", 
                message, 
                "broadcast", 
                msg_id=msg_id
            )
            
            if sent_count == total_peers:
                status_label.configure(
                    text="✅ Broadcast sent to all {} peers!".format(sent_count),
                    text_color=THEME.SUCCESS
                )
            else:
                status_label.configure(
                    text="✅ Sent to {}/{} peers".format(sent_count, total_peers),
                    text_color=THEME.WARNING
                )
            
            show_desktop_notification(
                "📢 Broadcast Sent",
                "Message sent to {} peers in #{}".format(sent_count, self.current_channel)
            )
            
            dialog.after(1500, dialog.destroy)
        
        message_entry.bind('<Return>', lambda e: send_broadcast())
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        broadcast_btn = ctk.CTkButton(
            btn_frame,
            text="📢 Broadcast",
            width=180,
            height=45,
            command=send_broadcast,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.WARNING,
            hover_color=THEME.WARNING_HOVER,
            corner_radius=12
        )
        broadcast_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖️ Cancel",
            width=180,
            height=45,
            command=dialog.destroy,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.ERROR,
            hover_color=THEME.ERROR_HOVER,
            corner_radius=12
        )
        cancel_btn.pack(side="left", padx=5)
    
    def show_channel_members_dialog(self, channel_name):
        perms = self.client.channel_permissions.get(channel_name, {})
        is_owner = perms.get('owner') == self.client.username
        
        if not is_owner:
            messagebox.showinfo("Permission Denied", "⚠️ Only channel owner can manage members")
            return
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Manage Channel Members")
        dialog.geometry("550x650")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=THEME.SURFACE)
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (325)
        dialog.geometry('+{}+{}'.format(x, y))
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Header
        ctk.CTkLabel(
            content,
            text="👥 Manage Members",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=THEME.TEXT_PRIMARY
        ).pack(pady=(0, 10))
        
        ctk.CTkLabel(
            content,
            text="Channel: #{}".format(channel_name),
            font=ctk.CTkFont(size=14),
            text_color=THEME.SECONDARY
        ).pack(pady=(0, 20))
        
        # Current members
        ctk.CTkLabel(
            content,
            text="Current Members:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(10, 5))
        
        # Members frame
        members_frame = ctk.CTkFrame(content, fg_color=THEME.BACKGROUND, corner_radius=10)
        members_frame.pack(fill="both", expand=True, pady=5)
        
        members_scroll = ctk.CTkScrollableFrame(members_frame, height=200)
        members_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        member_buttons = {}
        selected_member = tk.StringVar(value="")
        
        def update_member_selection():
            for username, btn in member_buttons.items():
                if username == selected_member.get():
                    btn.configure(fg_color=THEME.USER_SELECT, hover_color=THEME.USER_SELECT_HOVER)
                else:
                    btn.configure(fg_color="transparent", hover_color=THEME.SURFACE_HOVER)
        
        def select_member(username):
            selected_member.set(username)
            update_member_selection()
        
        def refresh_members():
            for widget in members_scroll.winfo_children():
                widget.destroy()
            member_buttons.clear()
            
            members_data = self.client.get_channel_members(channel_name)
            
            owner = members_data.get('owner')
            if owner:
                owner_btn = ctk.CTkButton(
                    members_scroll,
                    text="👑 {} (Owner)".format(owner),
                    height=35,
                    anchor="w",
                    fg_color="transparent",
                    hover_color=THEME.SURFACE_HOVER,
                    state="disabled",
                    font=ctk.CTkFont(size=12),
                    corner_radius=8
                )
                owner_btn.pack(fill="x", pady=2)
            
            # Only show members (exclude owner from removable list)
            for member in members_data.get('members', []):
                # Skip owner in member list so they can't remove themselves
                if member == owner:
                    continue
                
                btn = ctk.CTkButton(
                    members_scroll,
                    text="  👤 {}".format(member),
                    height=35,
                    anchor="w",
                    fg_color="transparent",
                    hover_color=THEME.SURFACE_HOVER,
                    command=lambda m=member: select_member(m),
                    font=ctk.CTkFont(size=12),
                    corner_radius=8
                )
                btn.pack(fill="x", pady=2)
                member_buttons[member] = btn
        
        refresh_members()
        
        # Add member section
        ctk.CTkLabel(
            content,
            text="Add Member:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", pady=(10, 5))
        
        add_frame = ctk.CTkFrame(content, fg_color="transparent")
        add_frame.pack(fill="x", pady=5)
        
        username_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Enter username",
            height=40,
            font=ctk.CTkFont(size=12),
            border_width=2,
            corner_radius=10
        )
        username_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        def add_member():
            username = username_entry.get().strip()
            if not username:
                messagebox.showwarning("Warning", "⚠️ Please enter a username")
                return
            
            success, msg = self.client.add_channel_member(channel_name, username)
            if success:
                messagebox.showinfo("Success", "✅ " + msg)
                username_entry.delete(0, "end")
                selected_member.set("")
                refresh_members()
                self.refresh_channels()
            else:
                messagebox.showerror("Error", "✗ " + msg)
        
        username_entry.bind('<Return>', lambda e: add_member())
        
        add_btn = ctk.CTkButton(
            add_frame,
            text="➕ Add",
            width=100,
            height=40,
            command=add_member,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME.SUCCESS,
            hover_color=THEME.SUCCESS_HOVER,
            corner_radius=10
        )
        add_btn.pack(side="left")
        
        # Remove member
        def remove_member():
            member_to_remove = selected_member.get()
            if not member_to_remove:
                messagebox.showwarning("Warning", "⚠️ Please select a member to remove")
                return
            
            if messagebox.askyesno("Confirm", "Remove {} from channel?".format(member_to_remove)):
                success, msg = self.client.remove_channel_member(channel_name, member_to_remove)
                if success:
                    messagebox.showinfo("Success", "✅ " + msg)
                    selected_member.set("")
                    refresh_members()
                    self.refresh_channels()
                else:
                    messagebox.showerror("Error", "✗ " + msg)
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        remove_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ Remove Selected",
            width=160,
            height=45,
            command=remove_member,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.ERROR,
            hover_color=THEME.ERROR_HOVER,
            corner_radius=12
        )
        remove_btn.pack(side="left", padx=5)
        
        close_btn = ctk.CTkButton(
            btn_frame,
            text="✖️ Close",
            width=160,
            height=45,
            command=dialog.destroy,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME.PRIMARY,
            hover_color=THEME.PRIMARY_HOVER,
            corner_radius=12
        )
        close_btn.pack(side="left", padx=5)
    
    def _on_search_key(self, event):
        query = self.search_entry.get().strip()
        if query:
            self.highlight_search(query)
        else:
            self.message_display._textbox.tag_remove("search_highlight", "1.0", "end")
    
    def highlight_search(self, query):
        self.message_display._textbox.tag_remove("search_highlight", "1.0", "end")
        
        if not query:
            return
        
        found_count = 0
        for msg_data in self.all_messages:
            content = msg_data.get('content', '').lower()
            if query.lower() in content:
                start_pos = "1.0"
                while True:
                    start_pos = self.message_display._textbox.search(
                        msg_data['content'], 
                        start_pos,
                        stopindex="end",
                        nocase=True
                    )
                    if not start_pos:
                        break
                    
                    content_lower = msg_data['content'].lower()
                    match_start = content_lower.find(query.lower())
                    
                    if match_start >= 0:
                        highlight_start = "{}+{}c".format(start_pos, match_start)
                        highlight_end = "{}+{}c".format(highlight_start, len(query))
                        
                        self.message_display._textbox.tag_add("search_highlight", highlight_start, highlight_end)
                        found_count += 1
                    
                    start_pos = "{}+{}c".format(start_pos, len(msg_data['content']))
        
        if found_count > 0:
            self.show_notification("🔍 Found {} matches".format(found_count))
    
    def _on_typing(self, event):
        if self.typing_job:
            self.root.after_cancel(self.typing_job)
        
        if self.current_view == "channel":
            self.client.send_typing_indicator()
        elif self.current_view == "dm":
            self.client.send_typing_indicator(self.client.current_dm_user)
        
        self.typing_job = self.root.after(2000, self.clear_typing_indicator)
    
    def clear_typing_indicator(self):
        pass
    
    def insert_emoji(self, emoji):
        current_text = self.message_entry.get()
        self.message_entry.delete(0, "end")
        self.message_entry.insert(0, current_text + emoji)
        self.message_entry.focus()
    
    def send_message(self):
        message = self.message_entry.get().strip()
        if not message:
            return
        
        if self.current_view == "channel":
            has_access, error_msg = self.client.check_channel_access(
                self.current_channel, 
                force_refresh=True
            )
            
            if not has_access:
                messagebox.showerror("Access Denied", "🔒 " + error_msg)
                self.display_message("System", 
                    "⚠️ Cannot send: {}".format(error_msg), 
                    "system")
                self.join_channel("general")
                return
            
            sent_count, msg_id = self.client.send_message(message, self.current_channel)
            
            if sent_count == -1:
                messagebox.showerror("Access Denied", 
                    "🔒 You no longer have access to this channel")
                self.display_message("System", 
                    "⚠️ Message not sent: Access denied", 
                    "system")
                self.join_channel("general")
                return
            
            self.display_message("You", message, "channel", msg_id=msg_id)
        else:
            target = self.client.current_dm_user
            success, msg, msg_id = self.client.send_dm(target, message)
            
            if success:
                if target not in self.dm_conversations:
                    self.dm_conversations[target] = []
                self.dm_conversations[target].append(
                    (self.client.username, message)
                )
                self.display_message("You", message, "dm_sent", msg_id=msg_id)
            else:
                self.display_message("System", "✗ Failed: " + msg, "system")
        
        self.message_entry.delete(0, "end")
    
    def on_message_received(self, channel, sender, message, msg_type='channel', **kwargs):
        print("Message received: [{}] {}: {}, {}".format(channel, sender, message, msg_type))
        if msg_type == 'typing':
            self.show_typing_indicator(sender)
        elif msg_type == 'reaction':
            msg_id = kwargs.get('msg_id', '')
            self.show_reaction(msg_id, sender, message)
        elif msg_type == 'broadcast':
            msg_id = kwargs.get('msg_id', '')
            self.root.after(
                0,
                lambda: self.display_message(
                    sender + " (BROADCAST from #{})".format(channel), 
                    message, 
                    "broadcast", 
                    msg_id=msg_id,
                    save_to_history=False  # Không lưu vào lịch sử
                )
            )
            show_desktop_notification("📢 Broadcast from #{}".format(channel), "{}: {}".format(sender, message[:50]))
        elif msg_type == 'dm':
            if sender not in self.dm_conversations:
                self.dm_conversations[sender] = []
            self.dm_conversations[sender].append((sender, message))
            
            if self.current_view == 'dm' and self.client.current_dm_user == sender:
                msg_id = kwargs.get('msg_id', '')
                self.root.after(
                    0,
                    lambda: self.display_message(sender, message, "dm_recv", msg_id=msg_id)
                )
                self.client.unread_messages[sender] = 0
            else:
                self.root.after(
                    0,
                    lambda: show_desktop_notification("💬 New DM", "{}: {}".format(sender, message[:50]))
                )
                self.root.after(0, self.refresh_users)
        else:
            if channel == self.current_channel and self.current_view == 'channel':
                msg_id = kwargs.get('msg_id', '')
                self.root.after(
                    0,
                    lambda: self.display_message(sender, message, "channel", msg_id=msg_id)
                )
            elif (self.current_view == 'channel' and  channel != self.current_channel) or self.current_view != 'channel':
                self.root.after(
                    0,
                    lambda: show_desktop_notification("📨 New Message in #{}".format(channel), "{}: {}".format(sender, message[:50]))
                )
                self.root.after(0, self.refresh_channels)
    
    def show_typing_indicator(self, username):
        self.client.typing_users.add(username)
        self.update_typing_display()
        
        def clear_typing():
            if username in self.client.typing_users:
                self.client.typing_users.discard(username)
                self.update_typing_display()
        
        self.root.after(3000, clear_typing)
    
    def update_typing_display(self):
        if not self.client.typing_users:
            self.typing_label.configure(text="")
            return
        
        users = list(self.client.typing_users)
        if len(users) == 1:
            text = "   {} is typing...".format(users[0])
        elif len(users) == 2:
            text = "   {} and {} are typing...".format(users[0], users[1])
        else:
            text = "   Several people are typing..."
        
        self.typing_label.configure(text=text)
    
    def show_reaction(self, msg_id, sender, emoji):
        if not msg_id:
            return
        
        self.message_reactions[msg_id][emoji].append(sender)
        
        self.display_message("System", 
                           "💫 {} reacted with {} to message".format(sender, emoji), 
                           "system")
    
    def show_notification(self, text):
        original = self.root.title()
        self.root.title("🔔 " + text)
        self.root.after(3000, lambda: self.root.title(original))
        
        try:
            self.root.bell()
        except:
            pass
    
    def display_message(self, sender, message, msg_type="channel", timestamp="", msg_id=None, save_to_history=True):
        self.message_display.configure(state="normal")
        
        if msg_type == "system":
            self.message_display._textbox.insert(
                "end",
                "ℹ️ [System] {}\n".format(message),
                "system"
            )
        else:
            if timestamp:
                time_str = parse_timestamp(timestamp)
            else:
                time_str = get_current_time()
            
            self.message_display._textbox.insert("end", "[", "timestamp")
            self.message_display._textbox.insert("end", time_str, "timestamp")
            self.message_display._textbox.insert("end", "] ", "timestamp")
            
            if msg_type in ["dm_sent", "dm_recv"]:
                self.message_display._textbox.insert("end", "{}: ".format(sender), msg_type)
            elif msg_type == "broadcast":
                self.message_display._textbox.insert("end", "{}: ".format(sender), "broadcast")
            else:
                self.message_display._textbox.insert("end", "{}: ".format(sender), "sender")
            
            self.message_display._textbox.insert("end", "{}\n".format(message))
            
            # CHỈ lưu vào all_messages nếu save_to_history = True
            if save_to_history:
                self.all_messages.append({
                    'sender': sender,
                    'content': message,
                    'type': msg_type,
                    'timestamp': time_str
                })
            
            if msg_id and msg_id in self.message_reactions:
                reactions = self.message_reactions[msg_id]
                if reactions:
                    reaction_text = "   "
                    for emoji, users in reactions.items():
                        reaction_text += "{} {} ".format(emoji, len(users))
                    self.message_display._textbox.insert("end", reaction_text + "\n", "reaction")
        
        self.message_display.configure(state="disabled")
        self.message_display._textbox.see("end")
    
    def start_auto_refresh(self):
        def auto_refresh():
            if self.client:
                joined, left = self.client.update_peer_list()

                if joined or left:
                    self.refresh_users()

                    for user in joined:
                        self.display_message("System", "✅ {} joined".format(user), "system")
                        show_desktop_notification("👋 User Joined", "{} is now online".format(user))

                    for user in left:
                        self.display_message("System", "✗ {} left".format(user), "system")

                self.auto_refresh_job = self.root.after(
                    AUTO_REFRESH_INTERVAL,
                    auto_refresh
                )
        
        auto_refresh()
    
    def stop_auto_refresh(self):
        if self.auto_refresh_job:
            self.root.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None
    
    def do_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.stop_auto_refresh()
            if self.client:
                if self.client.p2p_server:
                    self.client.p2p_server.stop()
                self.client.logout()
            self.show_login_screen()
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()


def main():
    if not CTK_AVAILABLE:
        print("CustomTkinter is required! Install with: pip install customtkinter")
        return
    
    root = ctk.CTk()
    root.title("🚀 BK Chat - Beautiful Edition")
    
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    root.minsize(1200, 700)
    
    app = ChatGUI(root)
    
    def on_closing():
        if app.client:
            if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
                app.stop_auto_refresh()
                app.client.logout()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    print("="*70)
    print("🚀 BK CHAT - BEAUTIFUL UI WITH CUSTOMTKINTER")
    print("="*70)
    print("✨ FEATURES:")
    print("  ✓ Beautiful modern interface with enhanced styling")
    print("  ✓ Visual feedback for channel/user selection")
    print("  ✓ Smooth hover effects and transitions")
    print("  ✓ Color-coded indicators (Blue for channels, Green for users)")
    print("  ✓ TRUE Broadcast to channel (P2P)")
    print("  ✓ Desktop notifications")
    print("  ✓ Access control for channels")
    print("  ✓ Search functionality with highlighting")
    print("  ✓ Typing indicators")
    print("  ✓ Emoji reactions")
    print("  ✓ Direct messaging")
    print("  ✓ Enhanced dark theme")
    print("="*70)
    print("Tracker: {}:{}".format(TRACKER_HOST, TRACKER_PORT))
    print("="*70)
    print("\n🎉 Starting Beautiful GUI...\n")
    
    root.mainloop()


if __name__ == "__main__":
    main()