#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_backend
~~~~~~~~~~~~~~~~~

This module provides a simple entry point for deploying backend server process
using the socket framework. It parses command-line arguments to configure the
server's IP address and port, and then launches the backend server.
"""

import socket
import argparse
import socket
import argparse
import sqlite3
import json
from daemon.weaprous import WeApRous
from daemon.response import Response

from daemon import create_backend

# Default port number used if none is specified via command-line arguments.
PORT = 9000 
app = WeApRous()
DB_PATH = 'db/app.db'

@app.route('/login', methods=['POST'])
def handle_login(req):
    """
    Task 1A:
    - Kiểm tra username=admin, password=password
    - Nếu đúng: Set-Cookie: auth=true và trả index.html
    - Nếu sai: trả 401
    """
    resp = Response(req)

    # Parse form-urlencoded
    credentials = {}
    if req.body:
        try:
            for pair in req.body.split('&'):
                key, val = pair.split('=', 1)
                credentials[key] = val
        except:
            pass

    username = credentials.get('username', '')
    password = credentials.get('password', '')

    if username == "admin" and password == "password":
        print("[Backend] Login success")

        resp.headers['Set-Cookie'] = "auth=true; Path=/"

        req.path = "/index.html"
        return resp.build_response(req)

    # Sai thì trả 401
    print("[Backend] Login failed")
    return resp.build_unauthorized()


def serve_protected_file(req):
    """
    Hook này xử lý các file tĩnh CẦN BẢO VỆ.
    Nó kiểm tra cookie 'session' trước khi phục vụ.
    """
    resp = Response(req)
    
    # Logic security (Task 1B) đã chuyển về đây
    if not req.cookies.get('auth'):
        print(f"[Backend] Access DENIED for {req.path}. No session cookie.")
        return resp.build_unauthorized() # Trả về 401
    
    print(f"[Backend] Access GRANTED for {req.path}. Serving file.")
    
    # Nếu OK, dùng logic 'build_response' để tự động đọc file
    # (nó sẽ đọc file tại req.path, ví dụ /index.html)
    return resp.build_response(req)

# --- Đăng ký Hook ---
# Cả hai đường dẫn '/' và '/index.html' đều gọi chung 1 hàm bảo vệ
@app.route('/', methods=['GET'])
def handle_root(req):
    req.path = '/index.html' # Ép request '/' thành '/index.html'
    return serve_protected_file(req)

@app.route('/index.html', methods=['GET'])
def handle_index(req):
    return serve_protected_file(req)

#
# LƯU Ý: Các file tĩnh không cần bảo vệ (như /css/styles.css)
# sẽ tự động được httpadapter xử lý vì không khớp hook nào.
#

if __name__ == "__main__":
    """
    Entry point for launching the backend server.

    This block parses command-line arguments to determine the server's IP address
    and port. It then calls `create_backend(ip, port)` to start the RESTful
    application server.

    :arg --server-ip (str): IP address to bind the server (default: 127.0.0.1).
    :arg --server-port (int): Port number to bind the server (default: 9000).
    """

    parser = argparse.ArgumentParser(
        prog='Backend',
        # ... (phần parser giữ nguyên) ...
    )
    parser.add_argument('--server-ip',
        type=str,
        default='0.0.0.0',
        help='IP address to bind the server. Default is 0.0.0.0'
    )
    parser.add_argument(
        '--server-port',
        type=int,
        default=PORT,
        help='Port number to bind the server. Default is {}.'.format(PORT)
    )
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # --- SỬA LỖI ---
    # Xóa dòng này:
    # create_backend(ip, port)
    
    # Thêm 3 dòng này (giống hệt start_tracker.py):
    print(f"[Backend] Khởi động Backend Server (Login/Static) tại {ip}:{port}")
    app.prepare_address(ip, port)
    app.run()