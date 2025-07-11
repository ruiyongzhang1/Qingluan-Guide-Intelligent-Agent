# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from agent.ai_agent import get_agent_service, clear_user_agent_sessions, get_agent_memory_stats
from agent.attraction_guide import get_attraction_guide_response_stream, clear_tour_guide_agents
from database_self import db
import os
import json
from dotenv import load_dotenv
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# ------------------------ 用户功能函数 ------------------------
def clear_user_agents(email):
    """清除用户的智能体会话和Redis记忆"""
    return clear_user_agent_sessions(email)

def add_user(email, password):
    return db.add_user(email, password)

def verify_user(email, password):
    return db.verify_user(email, password)

def save_conversation(email, messages, conv_id):
    db.save_conversation(email, messages, conv_id)

def get_history(email):
    return db.get_history(email)

def clear_user_history(email):
    """清理用户的所有数据：SQLite历史记录 + Redis智能体记忆"""
    # 1. 清理SQLite数据库中的历史记录
    success = db.clear_user_history(email)
    
    # 2. 清理Redis中的智能体记忆
    if success:
        clear_user_agents(email)
    
    return success

def new_conversation(email):
    session['current_conv_id'] = str(uuid.uuid4())
    return True

# ------------------------ 工具函数 ------------------------
def stream_response(generator, user_message, email, conv_id, agent_type):
    def generate():
        try:
            full_response = ""
            for chunk in generator:
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            save_conversation(email, [
                {"text": user_message, "is_user": True, "agent_type": agent_type},
                {"text": full_response, "is_user": False, "agent_type": agent_type},
            ], conv_id)
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response

# ------------------------ 路由 ------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if verify_user(email, password):
            session['email'] = email
            return redirect(url_for('chat'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('password2', '').strip()

    allowed_domains = ['@qq.com', '@gmail.com', '@outlook.com', '@163.com', '@foxmail.com']

    if not email or not password or not confirm_password:
        return render_template('login.html', error="所有字段都必须填写")
    if password != confirm_password:
        return render_template('login.html', error="两次输入的密码不一致")
    if '@' not in email or not any(email.endswith(domain) for domain in allowed_domains):
        return render_template('login.html', error="仅支持指定邮箱后缀注册")
    if add_user(email, password):
        session['email'] = email
        return redirect(url_for('chat'))
    return render_template('login.html', error="Email already exists")

@app.route('/chat')
def chat():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', email=session['email'])

@app.route('/travel')
def travel():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('travel.html', email=session['email'])

@app.route('/send_message', methods=['POST'])
def send_message():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    user_message = data.get("message", "").strip()
    agent_type = data.get("agent_type", "general")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    email = session["email"]
    conv_id = session.get("current_conv_id") or str(uuid.uuid4())
    session["current_conv_id"] = conv_id

    try:
        agent_service = get_agent_service()
        generator = agent_service.get_response_stream(user_message, email, agent_type, conv_id)
        return stream_response(generator, user_message, email, conv_id, agent_type)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/attraction_guide', methods=['POST'])
def attraction_guide():
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
        generator = get_attraction_guide_response_stream(user_message, email)
        return stream_response(generator, user_message, email, conv_id, "attraction_guide")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/plan_travel', methods=['POST'])
def plan_travel():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    from agent.prompts import format_travel_request_prompt

    data = request.get_json()
    travel_message = format_travel_request_prompt(data)

    email = session["email"]
    conv_id = session.get("current_conv_id") or str(uuid.uuid4())
    session["current_conv_id"] = conv_id

    try:
        agent_service = get_agent_service()
        generator = agent_service.get_response_stream(travel_message, email, "travel", conv_id)
        return stream_response(generator, travel_message, email, conv_id, "travel")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/load_history', methods=['POST'])
def load_history():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        return jsonify({'history': get_history(session['email'])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_conversation', methods=['POST'])
def delete_conversation():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return jsonify({"error": "Missing conversation_id"}), 400

    try:
        success = db.delete_conversation_for_user(session["email"], conversation_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Conversation not found or access denied"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    clear_user_history(session["email"])
    session.pop("current_conv_id", None)
    return jsonify({"success": True})

@app.route('/new_conversation', methods=['POST'])
def start_new_conversation():
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        new_conversation(session['email'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    email = session.get('email')
    if email:
        clear_user_agents(email)
        clear_tour_guide_agents(email)
    session.clear()
    return redirect(url_for('login'))

@app.route('/memory_stats', methods=['GET'])
def memory_stats():
    """获取记忆系统统计信息（管理员接口）"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        stats = get_agent_memory_stats()
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
