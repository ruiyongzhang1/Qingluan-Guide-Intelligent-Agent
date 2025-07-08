from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, stream_template
from ai_agent import get_agent_response_stream
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import uuid  # 添加uuid用于生成对话ID
from redis import Redis  # 添加Redis导入

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# 简化用户存储（生产环境应使用数据库）
USER_DB = 'users.json'
HISTORY_DB = 'history.json'

# 初始化数据库函数
def init_databases():
    if not os.path.exists(USER_DB):
        with open(USER_DB, 'w') as f:
            json.dump({}, f)
    
    if not os.path.exists(HISTORY_DB):
        with open(HISTORY_DB, 'w') as f:
            json.dump({}, f)

# 添加用户函数
def add_user(email, password):
    init_databases()
    with open(USER_DB, 'r') as f:
        users = json.load(f)
    
    if email in users:
        return False
    
    users[email] = {'password': password}
    with open(USER_DB, 'w') as f:
        json.dump(users, f)
    return True

# 验证用户函数
def verify_user(email, password):
    init_databases()
    with open(USER_DB, 'r') as f:
        users = json.load(f)
    
    if email in users and users[email]['password'] == password:
        return True
    return False

def save_conversation(email, messages, conv_id):
    init_databases()
    today = datetime.now().strftime('%Y-%m-%d')
    with open(HISTORY_DB, 'r') as f:
        history = json.load(f)
    if email not in history:
        history[email] = []
    # 用传入的 conv_id
    current_conv_id = conv_id
    # 查找并追加消息
    for conv in history[email]:
        if conv['id'] == current_conv_id:
            conv['messages'].extend(messages)
            break
    else:
        # 新建对话
        conversation = {
            'id': current_conv_id,
            'date': today,
            'messages': messages
        }
        history[email].append(conversation)
    with open(HISTORY_DB, 'w') as f:
        json.dump(history, f)

# 获取历史记录函数
def get_history(email):
    init_databases()
    with open(HISTORY_DB, 'r') as f:
        history = json.load(f)
    
    if email not in history or not history[email]:
        return []
    
    # 按日期排序，最新的在前面
    sorted_history = sorted(history[email], key=lambda x: x['date'], reverse=True)
    return sorted_history

# 清除用户历史记录函数
def clear_user_history(email):
    init_databases()
    with open(HISTORY_DB, 'r') as f:
        history = json.load(f)
    
    if email in history:
        del history[email]
    
    with open(HISTORY_DB, 'w') as f:
        json.dump(history, f)
    return True

# 新建对话函数
def new_conversation(email):
    # 生成新的对话ID
    session['current_conv_id'] = str(uuid.uuid4())
    return True

# 首页路由
@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if verify_user(email, password):
            session['email'] = email
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

# 注册路由
@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['password2']

    if not email or not password or not confirm_password:
        return render_template('login.html', error="所有字段都必须填写")
    if password != confirm_password:
        return render_template('login.html', error="两次输入的密码不一致")
    if add_user(email, password):
        session['email'] = email
        return redirect(url_for('chat'))
    else:
        return render_template('login.html', error="Email already exists")

# 聊天页面路由
@app.route('/chat')
def chat():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', email=session['email'])

# 发送消息路由
@app.route('/send_message', methods=['POST'])
def send_message():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    email = session["email"]
    conv_id = session.get("current_conv_id") or str(uuid.uuid4())
    session["current_conv_id"] = conv_id

    try:
        # 使用流式响应
        def generate_response():
            try:
                full_response = ""
                chunk_count = 0
                # 获取流式响应
                for chunk in get_agent_response_stream(user_message, email):
                    if chunk:
                        chunk_count += 1
                        full_response += chunk
                        print(f"Streaming chunk {chunk_count}: {chunk[:50]}...")  # 调试信息
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                print(f"Total chunks: {chunk_count}, Full response length: {len(full_response)}")  # 调试信息
                
                # 保存完整的对话历史，传递 conv_id
                save_conversation(email, [
                    {"text": user_message, "is_user": True},
                    {"text": full_response, "is_user": False},
                ], conv_id)
                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                print(f"Error in generate_response: {e}")  # 调试信息
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        response = Response(generate_response(), mimetype='text/event-stream')
        # 添加SSE所需的headers
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'  # 禁用Nginx缓冲
        response.headers['Connection'] = 'keep-alive'
        return response
    except Exception as e:
        print(f"Error in send_message: {e}")  # 调试信息
        return jsonify({"error": str(e)}), 500

# 加载历史记录路由
@app.route('/load_history', methods=['POST'])
def load_history():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_history = get_history(session['email'])
        return jsonify({'history': user_history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 清除历史记录路由
@app.route('/clear_history', methods=['POST'])
def clear_history():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    email = session["email"]
    conv_id = session.get("current_conv_id")
    # 1. 删文件历史
    clear_user_history(email)
    if conv_id:
        redis_key = f"{email}-{conv_id}"
        # 连接 Redis 并删除
        r = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.delete(redis_key)

    # 3. 清掉当前 conv_id，让后续新对话重建
    session.pop("current_conv_id", None)
    return jsonify({"success": True})

# 新建对话路由
@app.route('/new_conversation', methods=['POST'])
def start_new_conversation():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        new_conversation(session['email'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 退出登录路由
@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))
# 需求表格

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
