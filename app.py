"""
app.py — SyncSpace Backend (Python / Flask port of HttpChatServer.java)
Runs on port 8080. Open browser to http://localhost:8080

ALL ROUTES (unchanged from the Java version so index.html works as-is):
  GET  /                → serves index.html
  POST /login           → login user
  POST /signup          → register new user
  POST /changeusername  → change username
  POST /changepassword  → change password
  POST /send            → send group message
  GET  /messages        → get group messages  ?group=GroupName
  POST /creategroup     → create a new group with passcode
  POST /joingroup       → verify passcode to enter group
  GET  /groups          → list all groups
  POST /sendprivate     → send private DM
  GET  /privatemessages → get DM history     ?user1=a&user2=b
  POST /react           → toggle group message reaction
  GET  /reactions       → get group message reactions ?group=xxx
  POST /reactprivate    → toggle DM reaction
  GET  /dmreactions     → get DM reactions   ?user1=a&user2=b
  POST /cleargroup      → clear a group's messages
  POST /cleardm         → clear a DM thread
  GET  /contacts        → DM contacts with last message id ?username=xxx
  GET  /users           → get all users      ?except=username
  GET  /mygroups        → groups user has joined  ?username=xxx
  GET  /groupmembers    → members of a group      ?group=xxx
  POST /leavegroup      → leave a group
  POST /removemember    → admin removes a member
  POST /renamegroup     → admin renames a group
  GET  /themes/<file>   → static theme wallpaper images
"""
import os
import socket

from flask import Flask, request, jsonify, send_from_directory, Response

import db
from dao import group_dao, message_dao, private_message_dao, reaction_dao, user_dao

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)


# ================================================================
# CORS — applied to every response, mirrors handleCORS()/sendResponse()
# in the Java version (Access-Control-Allow-Origin: *)
# ================================================================
@app.after_request
def add_cors_headers(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


def fail(message: str, code: int = 400):
    return jsonify({"status": "fail", "message": message}), code


def ok(extra: dict | None = None, code: int = 200):
    body = {"status": "success"}
    if extra:
        body.update(extra)
    return jsonify(body), code


def form(key: str) -> str:
    """Read a form-encoded body param, defaulting to ''."""
    return (request.form.get(key) or "").strip()


def query(key: str) -> str:
    return (request.args.get(key) or "").strip()


# ================================================================
# GET / → serves index.html
# ================================================================
@app.route("/", methods=["GET"])
def index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(index_path):
        return "index.html not found! Put it in the same folder as app.py.", 404
    return send_from_directory(BASE_DIR, "index.html")


# ================================================================
# GET /themes/<filename> → static theme wallpaper images
# ================================================================
@app.route("/themes/<path:filename>", methods=["GET"])
def themes(filename):
    themes_dir = os.path.join(BASE_DIR, "themes")
    if not os.path.exists(os.path.join(themes_dir, filename)):
        return "", 404
    return send_from_directory(themes_dir, filename)


# ================================================================
# POST /login
# ================================================================
@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    password = form("password")
    print(f"[LOGIN] Attempt for username: {username}")

    if not username or not password:
        return fail("Fields cannot be empty")

    if user_dao.login_user(username, password):
        return ok({"username": username})
    return fail("Invalid username or password", 401)


# ================================================================
# POST /signup
# ================================================================
@app.route("/signup", methods=["POST", "OPTIONS"])
def signup():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    password = form("password")
    print(f"[SIGNUP] Attempt for username: {username}")

    if not username or not password:
        return fail("Fields cannot be empty")

    if user_dao.register_user(username, password):
        return ok()
    return fail("Username already taken", 409)


# ================================================================
# POST /changeusername
# ================================================================
@app.route("/changeusername", methods=["POST", "OPTIONS"])
def change_username():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    new_username = form("newUsername")

    if not username or not new_username:
        return fail("Fields cannot be empty")
    if len(new_username) < 2:
        return fail("Username too short")
    if username == new_username:
        return fail("New username must differ")

    if user_dao.change_username(username, new_username):
        return ok()
    return fail("Username unavailable", 409)


# ================================================================
# POST /changepassword
# ================================================================
@app.route("/changepassword", methods=["POST", "OPTIONS"])
def change_password():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    old_password = form("oldPassword")
    new_password = form("newPassword")

    if not username or not old_password or not new_password:
        return fail("Fields cannot be empty")
    if len(new_password) < 4:
        return fail("New password too short")

    if user_dao.change_password(username, old_password, new_password):
        return ok()
    return fail("Invalid username or current password", 401)


# ================================================================
# GET /contacts?username=xxx
# Returns: [{"user":"alice","lastId":123}, ...]
# ================================================================
@app.route("/contacts", methods=["GET"])
def contacts():
    username = query("username")
    if not username:
        return jsonify([])
    contacts_map = private_message_dao.get_dm_contacts(username)
    return jsonify([{"user": u, "lastId": last_id} for u, last_id in contacts_map.items()])


# ================================================================
# POST /react
# ================================================================
@app.route("/react", methods=["POST", "OPTIONS"])
def react():
    if request.method == "OPTIONS":
        return "", 204

    group = form("group")
    username = form("username")
    emoji = form("emoji")
    msg_id_str = form("msgId")

    if not group or not username or not emoji or not msg_id_str:
        return fail("Missing fields")
    try:
        msg_id = int(msg_id_str)
    except ValueError:
        return fail("Invalid msgId")

    reaction_dao.toggle_group_reaction(group, msg_id, emoji, username)
    return ok()


# ================================================================
# GET /reactions?group=xxx
# ================================================================
@app.route("/reactions", methods=["GET"])
def reactions():
    group = query("group")
    if not group:
        return fail("Missing group")
    react_map = reaction_dao.get_group_reactions(group)
    # JSON object keys must be strings
    return jsonify({str(k): v for k, v in react_map.items()})


# ================================================================
# POST /reactprivate
# ================================================================
@app.route("/reactprivate", methods=["POST", "OPTIONS"])
def react_private():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    other = form("other")
    emoji = form("emoji")
    msg_id_str = form("msgId")

    if not username or not other or not emoji or not msg_id_str:
        return fail("Missing fields")
    try:
        msg_id = int(msg_id_str)
    except ValueError:
        return fail("Invalid msgId")

    reaction_dao.toggle_dm_reaction(username, other, msg_id, emoji, username)
    return ok()


# ================================================================
# GET /dmreactions?user1=a&user2=b
# ================================================================
@app.route("/dmreactions", methods=["GET"])
def dm_reactions():
    user1 = query("user1")
    user2 = query("user2")
    if not user1 or not user2:
        return fail("Missing users")
    react_map = reaction_dao.get_dm_reactions(user1, user2)
    return jsonify({str(k): v for k, v in react_map.items()})


# ================================================================
# POST /send → group message
# ================================================================
@app.route("/send", methods=["POST", "OPTIONS"])
def send():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    message = form("message")
    group = form("group")

    if not username or not message or not group:
        return fail("Missing fields")

    message_dao.save_message(group, username, message)
    return ok()


# ================================================================
# GET /messages?group=General
# Returns: [{"id": N, "sender": "user", "message": "text"}, ...]
# ================================================================
@app.route("/messages", methods=["GET"])
def messages():
    group = query("group") or "General"
    return jsonify(message_dao.get_messages_with_ids(group))


# ================================================================
# POST /creategroup
# ================================================================
@app.route("/creategroup", methods=["POST", "OPTIONS"])
def create_group():
    if request.method == "OPTIONS":
        return "", 204

    group_name = form("groupName")
    passcode = form("passcode")
    admin = form("username")
    print(f"[CREATE GROUP] name={group_name} admin={admin}")

    if not group_name or not passcode or not admin:
        return fail("Missing fields")

    result = group_dao.create_group(group_name, passcode, admin)
    if result == "success":
        return ok()
    return fail(result, 409)


# ================================================================
# POST /joingroup
# ================================================================
@app.route("/joingroup", methods=["POST", "OPTIONS"])
def join_group():
    if request.method == "OPTIONS":
        return "", 204

    group_name = form("groupName")
    passcode = form("passcode")
    username = form("username")
    print(f"[JOIN GROUP] name={group_name}")

    # If user is already a member, let them in without passcode
    if group_dao.is_member(group_name, username):
        admin = group_dao.get_admin(group_name)
        return ok({"admin": admin, "alreadyMember": True})

    if group_dao.verify_passcode(group_name, passcode):
        group_dao.add_member(group_name, username)  # persist membership
        admin = group_dao.get_admin(group_name)
        return ok({"admin": admin, "alreadyMember": False})

    return fail("Wrong passcode", 401)


# ================================================================
# GET /groups
# ================================================================
@app.route("/groups", methods=["GET"])
def groups():
    return jsonify(group_dao.get_all_groups())


# ================================================================
# POST /sendprivate
# ================================================================
@app.route("/sendprivate", methods=["POST", "OPTIONS"])
def send_private():
    if request.method == "OPTIONS":
        return "", 204

    sender = form("sender")
    receiver = form("receiver")
    message = form("message")

    if not sender or not receiver or not message:
        return fail("Missing fields")

    private_message_dao.save_private_message(sender, receiver, message)
    return ok()


# ================================================================
# GET /privatemessages?user1=john&user2=alice
# ================================================================
@app.route("/privatemessages", methods=["GET"])
def private_messages():
    user1 = query("user1")
    user2 = query("user2")
    if not user1 or not user2:
        return jsonify([])
    return jsonify(private_message_dao.get_private_messages(user1, user2))


# ================================================================
# GET /users?except=john
# ================================================================
@app.route("/users", methods=["GET"])
def users():
    except_user = query("except")
    return jsonify(private_message_dao.get_all_users(except_user))


# ================================================================
# GET /mygroups?username=xxx
# Returns only the groups this user is a member of
# ================================================================
@app.route("/mygroups", methods=["GET"])
def my_groups():
    username = query("username")
    if not username:
        return jsonify([])
    return jsonify(group_dao.get_groups_for_user(username))


# ================================================================
# GET /groupmembers?group=xxx
# Returns list of members in a group: [{username, isAdmin}]
# ================================================================
@app.route("/groupmembers", methods=["GET"])
def group_members():
    group = query("group")
    if not group:
        return jsonify([])
    members = group_dao.get_members(group)
    admin = group_dao.get_admin(group)
    return jsonify([{"username": m, "isAdmin": m == admin} for m in members])


# ================================================================
# POST /leavegroup
# Body: username=xxx&groupName=yyy
# ================================================================
@app.route("/leavegroup", methods=["POST", "OPTIONS"])
def leave_group():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    group_name = form("groupName")
    if not username or not group_name:
        return fail("Missing fields")

    result = group_dao.leave_group(group_name, username)
    if result == "success":
        return ok()
    if result == "admin_cannot_leave":
        return fail("Admins cannot leave their own group. Delete the group instead.", 403)
    return fail("Server error", 500)


# ================================================================
# POST /removemember
# Body: adminUsername=xxx&groupName=yyy&targetUsername=zzz
# ================================================================
@app.route("/removemember", methods=["POST", "OPTIONS"])
def remove_member():
    if request.method == "OPTIONS":
        return "", 204

    admin_username = form("adminUsername")
    group_name = form("groupName")
    target_username = form("targetUsername")
    if not admin_username or not group_name or not target_username:
        return fail("Missing fields")

    result = group_dao.remove_member(group_name, admin_username, target_username)
    if result == "success":
        return ok()
    if result == "not_admin":
        return fail("Only the group admin can remove members", 403)
    return fail(result, 500)


# ================================================================
# POST /cleargroup
# Body: username=xxx&groupName=yyy
# ================================================================
@app.route("/cleargroup", methods=["POST", "OPTIONS"])
def clear_group():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    group_name = form("groupName")
    if not username or not group_name:
        return fail("Missing fields")
    if not group_dao.is_member(group_name, username):
        return fail("Not a member of this group", 403)

    message_dao.clear_group_messages(group_name)
    reaction_dao.clear_group_reactions(group_name)
    return ok()


# ================================================================
# POST /cleardm
# Body: username=xxx&other=yyy
# ================================================================
@app.route("/cleardm", methods=["POST", "OPTIONS"])
def clear_dm():
    if request.method == "OPTIONS":
        return "", 204

    username = form("username")
    other = form("other")
    if not username or not other:
        return fail("Missing fields")

    private_message_dao.clear_direct_messages(username, other)
    reaction_dao.clear_dm_reactions(username, other)
    return ok()


# ================================================================
# POST /renamegroup
# ================================================================
@app.route("/renamegroup", methods=["POST", "OPTIONS"])
def rename_group():
    if request.method == "OPTIONS":
        return "", 204

    old_name = form("oldName")
    new_name = form("newName")
    admin_username = form("adminUsername")
    if not old_name or not new_name or not admin_username:
        return fail("Missing fields")

    result = group_dao.rename_group(old_name, new_name, admin_username)
    if result == "success":
        return ok()
    if result == "not_admin":
        return fail("Only group admin can rename", 403)
    return fail(result, 409)


# ================================================================
# Startup: DB connectivity check + banner (mirrors main() in Java)
# ================================================================
def _detect_wifi_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "run ipconfig to find"


def _print_banner():
    print("Connecting to MySQL... ", end="")
    try:
        conn = db.get_connection()
        conn.close()
        print("\u2714  MySQL connected successfully!")
    except Exception as db_ex:
        print(f"\u2718  MySQL connection FAILED: {db_ex}")
        print("   Check config.py — DB_HOST, DB_USER, DB_PASSWORD.")

    ip = _detect_wifi_ip()
    print("\u2554" + "\u2550" * 40 + "\u2557")
    print("\u2551     SyncSpace Server is running!     \u2551")
    print("\u2551                                      \u2551")
    print("\u2551   Local:  http://localhost:8080      \u2551")
    line = f"   WiFi:   http://{ip}:8080"
    pad = " " * max(0, 36 - len(line))
    print("\u2551" + line + pad + "  \u2551")
    print("\u2551   Open the WiFi URL on your phone!   \u2551")
    print("\u255a" + "\u2550" * 40 + "\u255d")


if __name__ == "__main__":
    _print_banner()
    # threaded=True mirrors the Java version's fixed thread pool of 20,
    # allowing multiple concurrent requests to be handled.
    app.run(host="0.0.0.0", port=8080, threaded=True)
