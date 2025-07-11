#!/usr/bin/env python3
"""
调试脚本，用于测试智能体响应功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.ai_agent import get_agent_response_stream
from dotenv import load_dotenv

def test_agent_response():
    """测试智能体响应"""
    load_dotenv()
    
    # 测试参数
    user_message = "帮我规划一次北京到上海的旅行"
    user_email = "test@example.com"
    agent_type = "travel"
    
    print("开始测试智能体响应...")
    print(f"用户消息: {user_message}")
    print(f"用户邮箱: {user_email}")
    print(f"智能体类型: {agent_type}")
    print("-" * 50)
    
    try:
        response_gen = get_agent_response_stream(user_message, user_email, agent_type)
        print(f"生成器类型: {type(response_gen)}")
        
        # 检查是否是异步生成器
        if hasattr(response_gen, '__aiter__'):
            print("错误：返回的是异步生成器，但应该是同步生成器")
            return False
        
        # 尝试迭代生成器
        full_response = ""
        chunk_count = 0
        
        for chunk in response_gen:
            chunk_count += 1
            full_response += chunk
            print(f"Chunk {chunk_count}: {chunk[:100]}...")
        
        print(f"\n总共收到 {chunk_count} 个chunk")
        print(f"完整响应长度: {len(full_response)} 字符")
        print("测试成功！")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_agent_response()
