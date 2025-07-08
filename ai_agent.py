from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv
import os
from pydantic import SecretStr
import json

# 存储每个用户的智能体实例
user_agents = {}

# 系统提示，强制使用 Markdown 格式
SYSTEM_PROMPT = """你是一个专业的AI助手，请始终使用Markdown格式回复。

回复要求：
1. 使用Markdown语法格式化所有内容
2. 使用标题（# ## ###）来组织内容结构
3. 使用列表（- 或 1.）来列举项目
4. 使用**粗体**和*斜体*来强调重要信息
5. 使用代码块（```）来展示代码
6. 使用行内代码（`code`）来标记技术术语
7. 使用引用块（>）来引用重要信息
8. 使用表格来展示结构化数据
9. 使用分割线（---）来分隔不同部分

请确保所有回复都遵循Markdown格式规范，让内容更加清晰易读。"""

def get_agent_response_stream(user_message, user_email):
    """流式获取AI响应"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_URL")
    if not api_key:
        raise ValueError("DeepSeek API key not configured")
    
    # 为每个用户创建独立的LLM实例（保留对话记忆）
    if user_email not in user_agents:
        llm = ChatOpenAI(
            temperature=0,
            api_key=SecretStr(api_key),
            model="gpt-4.1-nano",
            base_url=base_url,
            streaming=True
        )
        
        memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True
        )
        
        user_agents[user_email] = {
            'llm': llm,
            'memory': memory
        }
    
    user_agent = user_agents[user_email]
    llm = user_agent['llm']
    memory = user_agent['memory']
    
    try:
        # 获取历史对话
        chat_history = memory.chat_memory.messages
        
        # 构建消息列表，添加系统提示
        from langchain.schema import BaseMessage
        messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
        
        # 添加历史对话（限制长度以避免token超限）
        for msg in chat_history[-10:]:  # 只保留最近10条消息
            if isinstance(msg, HumanMessage):
                messages.append(HumanMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(AIMessage(content=msg.content))
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))
        
        # 使用流式调用
        full_response = ""
        buffer = ""  # 添加缓冲区来处理不完整的chunk
        in_code_block = False  # 跟踪是否在代码块中
        code_block_start = -1  # 记录代码块开始位置
        
        for chunk in llm.stream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                # 确保chunk内容不包含不必要的换行符
                content = chunk.content
                buffer += content
                full_response += content
                
                # 检查是否进入或退出代码块
                if '```' in content:
                    if not in_code_block:
                        # 进入代码块
                        in_code_block = True
                        code_block_start = len(buffer) - content.find('```') - 3
                    else:
                        # 退出代码块
                        in_code_block = False
                        # 立即yield完整的代码块
                        yield buffer
                        buffer = ""
                        continue
                
                # 在代码块中，使用更保守的分割策略
                if in_code_block:
                    # 代码块中只在代码块结束时分割，或者缓冲区过大时强制分割
                    if len(buffer) > 500:  # 代码块中允许更长的缓冲区
                        yield buffer
                        buffer = ""
                else:
                    # 普通文本使用原来的分割策略
                    if (buffer.endswith(('.', '。', '!', '！', '?', '？', '\n\n')) or 
                        len(buffer) > 50):
                        yield buffer
                        buffer = ""
                    
            elif isinstance(chunk, str) and chunk.strip():
                # 确保字符串chunk不包含不必要的换行符
                content = chunk.strip()
                if content:  # 只处理非空内容
                    buffer += content
                    full_response += content
                    
                    # 检查是否进入或退出代码块
                    if '```' in content:
                        if not in_code_block:
                            # 进入代码块
                            in_code_block = True
                            code_block_start = len(buffer) - content.find('```') - 3
                        else:
                            # 退出代码块
                            in_code_block = False
                            # 立即yield完整的代码块
                            yield buffer
                            buffer = ""
                            continue
                    
                    # 应用相同的分割逻辑
                    if in_code_block:
                        if len(buffer) > 500:
                            yield buffer
                            buffer = ""
                    else:
                        if (buffer.endswith(('.', '。', '!', '！', '?', '？', '\n\n')) or 
                            len(buffer) > 50):
                            yield buffer
                            buffer = ""
        
        # 最后yield剩余的缓冲区内容
        if buffer:
            yield buffer
        
        # 保存到记忆
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(full_response)
                    
    except Exception as e:
        # 清理无效的智能体实例
        if user_email in user_agents:
            del user_agents[user_email]
        raise e

# 保留原来的函数用于兼容性
def get_agent_response(user_message, user_email):
    """获取完整的AI响应（非流式）"""
    response_text = ""
    for chunk in get_agent_response_stream(user_message, user_email):
        response_text += chunk
    return response_text