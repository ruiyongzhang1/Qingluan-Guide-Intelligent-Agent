from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, stream_template
from agent.ai_agent import (
    get_agent_response, 
    get_agent_response_stream, 
    get_mcp_response_sync, 
    multi_agent_travel_planning_sync,
    user_agents
)
from database_self import db
from dotenv import load_dotenv
from datetime import datetime
import os
import uuid
import json
import time

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# 清理用户智能体实例
def clear_user_agents(email):
    # 删除与该用户相关的所有智能体实例
    keys_to_delete = []
    for key in user_agents:
        if key.startswith(email):
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del user_agents[key]
    
    return True

# 添加用户函数
def add_user(email, password):
    return db.add_user(email, password)

# 验证用户函数
def verify_user(email, password):
    return db.verify_user(email, password)

def save_conversation(email, messages, conv_id):
    db.save_conversation(email, messages, conv_id)

# 获取历史记录函数
def get_history(email):
    return db.get_history(email)

# 清除用户历史记录函数
def clear_user_history(email):
    success = db.clear_user_history(email)
    if success:
        # 清理智能体实例
        clear_user_agents(email)
    return success

# 新建对话函数
def new_conversation(email):
    # 生成新的对话ID
    session['current_conv_id'] = str(uuid.uuid4())
    return True

# 首页路由
@app.route('/')
def index():
    # 直接渲染首页，无需登录验证
    return render_template('index.html')

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

# 旅行规划页面路由
@app.route('/travel')
def travel():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('travel.html', email=session['email'])


# 发送消息路由
@app.route('/send_message', methods=['POST'])
def send_message():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    user_message = data.get("message", "").strip()
    agent_type = data.get("agent_type", "general")  # 新增智能体类型参数
    
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    email = session["email"]
    conv_id = session.get("current_conv_id") or str(uuid.uuid4())
    session["current_conv_id"] = conv_id

    try:
        # 直接使用MCP响应函数获取完整响应
        def generate_response():
            try:
                print(f"[Flask] 使用MCP响应处理消息: {user_message[:100]}...")
                # 首先尝试使用MCP响应
                mcp_response = get_mcp_response_sync(user_message, email, agent_type)
                
                if mcp_response:
                    print(f"[Flask] 成功获取MCP响应，长度: {len(mcp_response)}")
                    # 模拟流式输出，将完整响应分块发送
                    chunk_size = 50
                    for i in range(0, len(mcp_response), chunk_size):
                        chunk = mcp_response[i:i+chunk_size]
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        time.sleep(0.01)  # 添加小延迟使前端体验更流畅
                else:
                    print("[Flask] MCP响应失败，使用备用响应")
                    # 如果MCP失败，使用备用的流式响应
                    for chunk in get_agent_response_stream(user_message, email, agent_type, conv_id):
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        time.sleep(0.01)
                
                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                print(f"Error in generate_response: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        response = Response(generate_response(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Connection'] = 'keep-alive'
        return response
    except Exception as e:
        print(f"Error in send_message: {e}")
        return jsonify({"error": str(e)}), 500

# 旅行规划表单处理路由
@app.route('/plan_travel', methods=['POST'])
def plan_travel():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    
    # 使用新的提示词模板格式化旅行请求
    from agent.prompts import format_travel_request_prompt
    travel_message = format_travel_request_prompt(data)

    email = session["email"]
    conv_id = session.get("current_conv_id") or str(uuid.uuid4())
    session["current_conv_id"] = conv_id

    try:
        # 使用多智能体系统处理旅行规划
        def generate_travel_response():
            try:
                print(f"[Flask] 使用多智能体系统处理旅行规划请求")
                # 使用多智能体流水线进行旅行规划
                multi_agent_response = multi_agent_travel_planning_sync(travel_message, email)
                
                if multi_agent_response:
                    print(f"[Flask] 成功获取多智能体旅行规划响应，长度: {len(multi_agent_response)}")
                    # 模拟流式输出，将完整响应分块发送
                    chunk_size = 50
                    for i in range(0, len(multi_agent_response), chunk_size):
                        chunk = multi_agent_response[i:i+chunk_size]
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        time.sleep(0.01)  # 添加小延迟使前端体验更流畅
                else:
                    print("[Flask] 多智能体响应失败，使用备用MCP响应")
                    # 如果多智能体失败，回退到单智能体MCP响应
                    mcp_response = get_mcp_response_sync(travel_message, email, agent_type="travel")
                    if mcp_response:
                        chunk_size = 50
                        for i in range(0, len(mcp_response), chunk_size):
                            chunk = mcp_response[i:i+chunk_size]
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            time.sleep(0.01)
                    else:
                        print("[Flask] 所有MCP响应失败，使用最终备用响应")
                        # 最终备用响应
                        for chunk in get_agent_response_stream(travel_message, email, agent_type="travel", conv_id=conv_id):
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            time.sleep(0.01)
                
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        response = Response(generate_travel_response(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Connection'] = 'keep-alive'
        return response
    except Exception as e:
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

# 删除特定对话路由
@app.route('/delete_conversation', methods=['POST'])
def delete_conversation():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    email = session["email"]
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return jsonify({"error": "Missing conversation_id"}), 400
    
    try:
        # 验证对话是否属于当前用户
        success = db.delete_conversation_for_user(email, conversation_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Conversation not found or access denied"}), 404
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return jsonify({"error": str(e)}), 500

# 清除历史记录路由
@app.route('/clear_history', methods=['POST'])
def clear_history():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    email = session["email"]
    
    # 清除历史记录和智能体
    clear_user_history(email)
    
    # 清除当前对话ID
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
    email = session.get('email')
    if email:
        clear_user_agents(email)
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)