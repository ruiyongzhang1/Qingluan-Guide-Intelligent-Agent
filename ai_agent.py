from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.tools import Tool
from langchain_community.utilities import SerpAPIWrapper
from dotenv import load_dotenv
import os
from pydantic import SecretStr
import json
import asyncio
from typing import Dict, List, Any, Optional
import requests

# 存储每个用户的智能体实例
user_agents = {}

# 通用系统提示，强制使用 Markdown 格式
GENERAL_SYSTEM_PROMPT = """你是一个专业的AI助手，请始终使用Markdown格式回复。

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

# 旅行规划系统提示词
TRAVEL_SYSTEM_PROMPT = """你是一个专业的AI旅行规划专家，具备全方位的旅行规划能力。请始终使用Markdown格式回复。

## 核心职责：

### 📊 信息收集与分析
1. **目的地调研**: 收集目的地的景点、文化、气候、安全等基本信息
2. **航班搜索**: 查找最佳航班选项和价格
3. **住宿搜索**: 查找符合用户偏好和预算的住宿选项
4. **餐饮推荐**: 搜索当地特色餐厅、美食推荐，考虑用户的饮食限制
5. **交通规划**: 收集当地交通信息、路线规划、交通费用等
6. **活动搜索**: 根据用户偏好搜索相关的活动、景点、体验项目

### 🗓️ 行程规划与优化
1. **需求分析**: 深入分析用户的旅行需求、偏好、预算和时间限制
2. **行程设计**: 制定详细的日程安排，包括时间、地点、活动安排
3. **路线优化**: 优化旅行路线，减少不必要的往返和时间浪费
4. **预算管理**: 进行成本估算和预算分配，确保在用户预算范围内
5. **个性化定制**: 根据用户偏好提供个性化的推荐和建议
6. **备选方案**: 提供备选方案、应急计划和实用建议

## 输出标准：

### 完整旅行规划必须包含：
- **航班预订建议**: 具体航班信息、时间、价格、预订链接
- **住宿推荐**: 酒店信息、地址、价格、特色、预订建议
- **详细行程**: 按天分解的活动安排，包括时间、地点、费用
- **交通规划**: 机场接送、景点间交通、当地交通建议
- **餐饮推荐**: 特色餐厅、美食推荐、用餐预算
- **预算明细**: 详细的费用分解和预算控制建议
- **实用信息**: 天气预报、重要提醒、紧急联系方式
- **备选方案**: 每个主要环节的备用选择

请确保所有回复都遵循Markdown格式规范，让内容更加清晰易读。"""

# 信息收集智能体提示词
INFORMATION_COLLECTOR_PROMPT = """你是一个专业的旅行信息收集专家。你的任务是搜索和收集全面的旅行相关信息。

## 工作流程：

1. **目的地基础信息**: 地理位置、气候特点、最佳旅行时间、语言、货币、时差等
2. **航班信息**: 搜索航班选项、价格对比、航空公司推荐、机场信息
3. **住宿选择**: 不同价位的酒店选项、特色民宿、位置评估、预订建议
4. **景点信息**: 主要景点介绍、门票价格、开放时间、游览建议
5. **餐饮推荐**: 当地美食、特色餐厅、价格区间、用餐建议
6. **交通信息**: 公共交通、租车选择、交通卡、出行建议
7. **当地实用信息**: 购物、通信、安全、医疗、紧急联系等

## 输出要求：
请将收集到的信息整理成结构化的格式，使用Markdown语法，确保信息详实、准确。
每个分类都应包含具体的数据、价格、联系方式等实用信息。
"""

# 行程规划智能体提示词
ITINERARY_PLANNER_PROMPT = """你是一个专业的旅行行程规划专家。基于收集到的信息，你需要制定详细、实用的旅行方案。

## 规划原则：

1. **时间合理**: 确保行程安排不过于紧张，留有充足的休息和机动时间
2. **路线优化**: 安排合理的游览顺序，减少不必要的往返
3. **预算控制**: 严格控制在用户预算范围内，提供不同档次的选择
4. **个性化**: 充分体现用户的偏好和需求
5. **实用性**: 提供具体可执行的行动指南

## 输出结构：

### 🛫 **航班预订建议**
- 推荐航班（航班号、时间、价格、预订链接）
- 机场交通安排

### 🏨 **住宿安排**
- 具体酒店推荐（名称、地址、价格、特色、预订链接）
- 住宿区域分析

### 📅 **详细日程安排**
- 按天分解的活动安排
- 每日时间表（上午、下午、晚上的具体安排）
- 交通路线和方式
- 预估费用

### 🍽️ **餐饮安排**
- 每餐具体餐厅推荐
- 特色菜品和价格
- 预订建议

### 💰 **详细预算**
- 各项费用明细
- 总预算控制
- 节省建议

### 📝 **实用指南**
- 注意事项
- 紧急联系方式
- 备选方案

使用Markdown格式，确保内容清晰、易读、可执行。
"""

# 搜索工具类
class TravelSearchTool:
    """旅行搜索工具类"""
    
    def __init__(self):
        load_dotenv()
        self.search_api_key = os.getenv("SEARCHAPI_API_KEY")  # 对应您的配置
        if not self.search_api_key:
            print("Warning: SEARCHAPI_API_KEY not found, search functionality will be limited")
    
    def search_travel_info(self, query: str) -> str:
        """通用旅行信息搜索"""
        if not self.search_api_key:
            return f"搜索功能暂不可用，但我可以基于常识为您提供关于'{query}'的基本信息。"
        
        try:
            # 使用SearchAPI进行搜索
            url = "https://www.searchapi.io/api/v1/search"
            params = {
                "api_key": self.search_api_key,
                "q": query,
                "num": 10
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("organic_results", [])[:5]:
                    results.append(f"**{item.get('title', '')}**\n{item.get('snippet', '')}\n链接: {item.get('link', '')}")
                return "\n\n".join(results) if results else "未找到相关信息"
            else:
                return f"搜索暂时不可用，状态码: {response.status_code}"
        except Exception as e:
            return f"搜索过程中出现错误: {str(e)}"
    
    def search_flights(self, query: str) -> str:
        """航班搜索"""
        search_query = f"flights {query} booking price schedule"
        return self.search_travel_info(search_query)
    
    def search_hotels(self, query: str) -> str:
        """酒店搜索"""
        search_query = f"hotels accommodation {query} booking price review"
        return self.search_travel_info(search_query)
    
    def search_attractions(self, query: str) -> str:
        """景点搜索"""
        search_query = f"tourist attractions {query} tickets opening hours reviews"
        return self.search_travel_info(search_query)
    
    def search_restaurants(self, query: str) -> str:
        """餐厅搜索"""
        search_query = f"restaurants food {query} local cuisine recommendations"
        return self.search_travel_info(search_query)

# 多智能体旅行规划系统
class MultiAgentTravelPlanner:
    """多智能体旅行规划系统（LangChain版）"""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.search_tool = TravelSearchTool()
        load_dotenv()
        
        # 获取API配置 - 使用OpenAI API
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_URL")
        
        if not self.api_key:
            raise ValueError("未配置OpenAI API密钥")
        
        # 创建LLM实例 - 使用OpenAI的gpt-4.1-nano模型
        self.llm = ChatOpenAI(
            temperature=0.1,
            api_key=SecretStr(self.api_key),
            model="gpt-4.1-nano",  # 使用gpt-4.1-nano模型
            base_url=self.base_url,
            streaming=True
        )
        
        # 创建搜索工具
        self.tools = [
            Tool(
                name="travel_search",
                description="搜索旅行相关信息",
                func=self.search_tool.search_travel_info
            ),
            Tool(
                name="flight_search",
                description="搜索航班信息和价格",
                func=self.search_tool.search_flights
            ),
            Tool(
                name="hotel_search",
                description="搜索酒店住宿信息",
                func=self.search_tool.search_hotels
            ),
            Tool(
                name="attraction_search",
                description="搜索景点和活动信息",
                func=self.search_tool.search_attractions
            ),
            Tool(
                name="restaurant_search",
                description="搜索餐厅和美食信息",
                func=self.search_tool.search_restaurants
            )
        ]
        
        # 创建记忆
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 创建信息收集智能体
        self.collector_agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=False
        )
        
        # 创建行程规划智能体（不需要搜索工具）
        self.planner_agent = initialize_agent(
            tools=[],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False
        )
    
    def collect_travel_information_stream(self, travel_request: str):
        """流式收集旅行信息"""
        collection_prompt = f"""
{INFORMATION_COLLECTOR_PROMPT}

用户旅行需求：
{travel_request}

请按照以下步骤收集信息：
1. 搜索目的地基本信息
2. 搜索航班选项
3. 搜索住宿选择
4. 搜索主要景点
5. 搜索餐厅推荐
6. 整理所有信息

请使用搜索工具获取最新、准确的信息，并以Markdown格式整理输出。
"""
        
        # 流式运行信息收集
        for chunk in self.llm.stream([SystemMessage(content=collection_prompt)]):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
    
    def create_detailed_itinerary_stream(self, travel_request: str, collected_info: str):
        """流式创建详细行程"""
        planning_prompt = f"""
{ITINERARY_PLANNER_PROMPT}

用户旅行需求：
{travel_request}

收集到的信息：
{collected_info}

请基于以上信息制定详细的旅行方案，确保方案实用、可执行，并严格控制在用户预算范围内。
"""
        
        # 流式运行行程规划
        for chunk in self.llm.stream([SystemMessage(content=planning_prompt)]):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content

# 智能体类型枚举
# 使用 langchain.agents.AgentType，避免自定义覆盖

def get_agent_response_stream(user_message, user_email, agent_type="general"):
    """获取智能体响应流"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_URL")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured")
    
    # 选择系统提示
    if agent_type == "travel":
        system_prompt = TRAVEL_SYSTEM_PROMPT
    else:
        system_prompt = GENERAL_SYSTEM_PROMPT
    
    # 为每个用户创建独立的LLM实例
    if f"{user_email}_{agent_type}" not in user_agents:
        llm = ChatOpenAI(
            temperature=0,
            api_key=SecretStr(api_key),
            model="gpt-4.1-nano",  # 使用gpt-4.1-nano模型
            base_url=base_url,
            streaming=True
        )
        
        memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True
        )
        
        user_agents[f"{user_email}_{agent_type}"] = {
            'llm': llm,
            'memory': memory,
            'agent_type': agent_type
        }
    
    user_agent = user_agents[f"{user_email}_{agent_type}"]
    llm = user_agent['llm']
    memory = user_agent['memory']
    
    try:
        # 获取历史对话
        chat_history = memory.chat_memory.messages
        
        # 构建消息列表
        from langchain.schema import BaseMessage
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        
        # 添加历史对话（限制长度）
        for msg in chat_history[-10:]:
            if isinstance(msg, HumanMessage):
                messages.append(HumanMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(AIMessage(content=msg.content))
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))
        
        # 如果是旅行规划请求，使用多智能体系统
        if agent_type == "travel" and is_travel_planning_request(user_message):
            yield from handle_travel_planning_stream(user_message, user_email)
            return
        
        # 普通流式响应
        full_response = ""
        buffer = ""
        in_code_block = False
        
        for chunk in llm.stream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                buffer += content
                full_response += content
                
                # 检查代码块
                if '```' in content:
                    in_code_block = not in_code_block
                    if not in_code_block:
                        yield buffer
                        buffer = ""
                        continue
                
                # 分割策略
                if in_code_block:
                    if len(buffer) > 500:
                        yield buffer
                        buffer = ""
                else:
                    if (buffer.endswith(('.', '。', '!', '！', '?', '？', '\n\n')) or 
                        len(buffer) > 50):
                        yield buffer
                        buffer = ""
                    
        # 最后yield剩余内容
        if buffer:
            yield buffer
        
        # 保存到记忆
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(full_response)
                    
    except Exception as e:
        # 清理无效的智能体实例
        if f"{user_email}_{agent_type}" in user_agents:
            del user_agents[f"{user_email}_{agent_type}"]
        raise e

def is_travel_planning_request(message: str) -> bool:
    """判断是否为旅行规划请求"""
    travel_keywords = [
        '旅行', '旅游', '出行', '行程', '规划', '计划',
        '机票', '酒店', '住宿', '景点', '路线',
        'travel', 'trip', 'vacation', 'itinerary', 'plan',
        'flight', 'hotel', 'attraction', 'route'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in travel_keywords)

def handle_travel_planning_stream(travel_request: str, user_email: str):
    """处理旅行规划请求的流式响应"""
    try:
        planner = MultiAgentTravelPlanner(user_email)
        
        # 阶段1：信息收集
        yield "\n\n## 🔍 正在收集旅行信息...\n\n"
        
        collected_info = ""
        for chunk in planner.collect_travel_information_stream(travel_request):
            yield chunk
            if isinstance(chunk, str):
                collected_info += chunk
            else:
                collected_info += str(chunk)
        
        # 阶段2：行程规划
        yield "\n\n---\n\n## 📋 正在制定详细行程...\n\n"
        
        for chunk in planner.create_detailed_itinerary_stream(travel_request, collected_info):
            yield chunk
            
    except Exception as e:
        yield f"\n\n❌ 旅行规划过程中出现错误: {str(e)}\n\n"

# 保留原来的函数用于兼容性
def get_agent_response(user_message, user_email, agent_type="general"):
    """获取完整的AI响应（非流式）"""
    response_text = ""
    for chunk in get_agent_response_stream(user_message, user_email, agent_type):
        response_text += chunk
    return response_text

# 清理用户智能体
def clear_user_agents(user_email: str):
    """清理用户的所有智能体实例"""
    keys_to_remove = [key for key in user_agents.keys() if key.startswith(user_email)]
    for key in keys_to_remove:
        del user_agents[key]