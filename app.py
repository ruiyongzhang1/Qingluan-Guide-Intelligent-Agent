from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, stream_template
from ai_agent import get_agent_response_stream, clear_user_agents
from attraction_guide import get_attraction_guide_response_stream, clear_tour_guide_agents
from database_self import db
import os
import json
from dotenv import load_dotenv
from datetime import datetime

import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

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
        # 使用流式响应
        def generate_response():
            try:
                full_response = ""
                chunk_count = 0
                
                # 获取流式响应，传入智能体类型
                for chunk in get_agent_response_stream(user_message, email, agent_type):
                    if chunk:
                        chunk_count += 1
                        full_response += chunk
                        print(f"Streaming chunk {chunk_count}: {chunk[:50]}...")
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                print(f"Total chunks: {chunk_count}, Full response length: {len(full_response)}")
                
                # 保存完整的对话历史
                save_conversation(email, [
                    {"text": user_message, "is_user": True, "agent_type": agent_type},
                    {"text": full_response, "is_user": False, "agent_type": agent_type},
                ], conv_id)
                
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

# 景点讲解路由
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
        # 使用流式响应
        def generate_attraction_response():
            try:
                full_response = ""
                chunk_count = 0
                
                # 获取流式响应
                for chunk in get_attraction_guide_response_stream(user_message, email):
                    if chunk:
                        chunk_count += 1
                        full_response += chunk
                        print(f"Streaming chunk {chunk_count}: {chunk[:50]}...")
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                print(f"Total chunks: {chunk_count}, Full response length: {len(full_response)}")
                
                # 保存完整的对话历史
                save_conversation(email, [
                    {"text": user_message, "is_user": True, "agent_type": "attraction_guide"},
                    {"text": full_response, "is_user": False, "agent_type": "attraction_guide"},
                ], conv_id)
                
                # 发送完成信号
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                print(f"Error in generate_attraction_response: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        response = Response(generate_attraction_response(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Connection'] = 'keep-alive'
        return response
    except Exception as e:
        print(f"Error in attraction_guide: {e}")
        return jsonify({"error": str(e)}), 500

# 旅行规划表单处理路由
@app.route('/plan_travel', methods=['POST'])
def plan_travel():
    if "email" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    
    # 构建旅行规划消息
    travel_message = f"""
请为我制定一个完整的旅行规划方案：

【基本信息】:
- 出发地：{data.get('source', '')}
- 目的地：{data.get('destination', '')}
- 旅行日期：{data.get('start_date', '')} 到 {data.get('end_date', '')}
- 预算：${data.get('budget', 0)} 美元
- 旅行偏好：{', '.join(data.get('preferences', []))}
- 住宿类型偏好：{data.get('accommodation_type', '')}
- 交通方式偏好：{', '.join(data.get('transportation_mode', []))}
- 饮食限制：{', '.join(data.get('dietary_restrictions', []))}

【请提供以下完整信息】:
1. 目的地概况和必游景点推荐
2. 航班搜索和预订建议（具体航班信息和价格）
3. 住宿推荐和预订建议（具体酒店信息和价格）
4. 详细的日程安排（按天分解，包括时间、地点、活动）
5. 当地交通和路线规划
6. 餐厅推荐和美食指南
7. 详细的预算分配和费用估算
8. 实用信息（天气、注意事项、紧急联系方式等）
9. 备选方案和应急计划

请确保所有推荐都在预算范围内，并充分考虑我的偏好和限制条件。
"""

    email = session["email"]
    conv_id = session.get("current_conv_id") or str(uuid.uuid4())
    session["current_conv_id"] = conv_id

    try:
        def generate_travel_response():
            try:
                full_response = ""
                chunk_count = 0
                
                # 使用旅行智能体类型
                for chunk in get_agent_response_stream(travel_message, email):
                    if chunk:
                        chunk_count += 1
                        full_response += chunk
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                # 保存对话历史
                save_conversation(email, [
                    {"text": travel_message, "is_user": True, "agent_type": "travel"},
                    {"text": full_response, "is_user": False, "agent_type": "travel"},
                ], conv_id)
                
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
        clear_tour_guide_agents(email)  # 清除景点讲解智能体
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)