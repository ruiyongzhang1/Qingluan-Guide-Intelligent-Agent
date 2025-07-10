import warnings
# 抑制LangChain弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")
warnings.filterwarnings("ignore", message=".*LangChain agents will continue to be supported.*", category=DeprecationWarning)

from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.tools import Tool
from dotenv import load_dotenv
import os
from pydantic import SecretStr
from typing import List
import requests
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
import markdown
from datetime import datetime
import pdfkit

# 存储每个用户的智能体实例
# 注意：当前使用LangChain agents，已被弃用
# 未来建议迁移到LangGraph以获得更好的功能和性能
user_agents = {}

# 通用系统提示，强制使用 Markdown 格式
GENERAL_SYSTEM_PROMPT = """你是一个专业的AI助手，在回复旅游相关问题时请始终使用Markdown格式回复。

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
1. **需求分析**: 深入分析用户的旅行需求、偏好、预算、随行人数和时间限制
2. **行程设计**: 制定详细的日程安排，包括时间、地点、活动安排，考虑随行人数
3. **路线优化**: 优化旅行路线，减少不必要的往返和时间浪费
4. **预算管理**: 进行成本估算和预算分配，确保在用户预算范围内，考虑随行人数
5. **个性化定制**: 根据用户偏好提供个性化的推荐和建议
6. **备选方案**: 提供备选方案、应急计划和实用建议

## 输出标准：

### 完整旅行规划必须包含：
- **航班预订建议**: 具体航班信息、时间、价格（考虑随行人数）、预订链接
- **住宿推荐**: 酒店信息、地址、价格（考虑随行人数）、特色、预订建议
- **详细行程**: 按天分解的活动安排，包括时间、地点、费用（考虑随行人数）
- **交通规划**: 机场接送、景点间交通、当地交通建议（考虑随行人数）
- **餐饮推荐**: 特色餐厅、美食推荐、用餐预算（考虑随行人数）
- **预算明细**: 详细的费用分解和预算控制建议（考虑随行人数）
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

# PDF生成智能体提示词
PDF_PROMPT = """你是一个专业的旅行攻略PDF生成专家。你的任务是基于对话历史生成完整、实用的旅行攻略PDF报告。

## 核心能力：

### 📊 信息整合
- 从对话历史中提取所有关键旅行信息
- 整理用户需求、偏好、预算等核心要素
- 汇总所有推荐的景点、餐厅、住宿等信息

### 📋 报告结构化
- 按照专业旅行攻略的标准格式组织内容
- 确保信息层次清晰、易于查找
- 提供完整的行动指南和实用信息

### 🎯 实用性优化
- 确保所有信息都是具体可执行的
- 提供详细的联系方式和预订信息
- 包含预算控制和费用估算

## 输出标准：

### 必须包含的章节：
1. **旅行概览** - 目的地、时间、预算、人数等基本信息
2. **详细行程** - 按天分解的完整行程安排，包含时间、地点、活动
3. **交通安排** - 航班信息、住宿详情、当地交通方案
4. **景点推荐** - 必游景点、门票价格、开放时间、游览建议
5. **餐饮指南** - 特色餐厅、美食推荐、用餐预算、预订建议
6. **预算明细** - 详细费用分解、总预算控制、节省建议
7. **实用信息** - 天气、注意事项、紧急联系方式、当地习俗
8. **备选方案** - 应急计划、备用选择、灵活调整建议

### 格式要求：
- 使用Markdown语法，确保结构清晰
- 使用标题、列表、表格等元素组织内容
- 突出重要信息和关键数据
- 保持专业性和可读性

请确保生成的旅行攻略PDF报告内容完整、结构清晰、实用性强。
"""

class PDFGeneratorTool:
    """PDF生成工具类"""

    def __init__(self):
        pass

    def generate_travel_pdf(self, conversation_data: str, summary: str = "", user_info: str = "") -> str:
        """用 wkhtmltopdf 生成旅行规划PDF，支持表格和代码块，并返回下载链接"""
        try:
            # 创建保存目录
            save_dir = r"C:\new_py\QL_guide\static\pdfs"
            os.makedirs(save_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"{user_info}_旅行规划_{timestamp}.pdf" if user_info else f"旅行规划_{timestamp}.pdf"
            pdf_path = os.path.join(save_dir, pdf_filename)

            # 构建HTML内容
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                body {{ font-family: 'Microsoft YaHei', 'SimSun', 'Arial', sans-serif; }}
                h1, h2, h3 {{ color: #4CAF50; }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                    table-layout: fixed;
                    word-break: break-all;
                }}
                th, td {{
                    border: 1px solid #333;
                    padding: 8px 6px;
                    font-size: 15px;
                    text-align: center;
                    vertical-align: middle;
                    word-break: break-all;
                }}
                th {{
                    background: #f2f2f2;
                    font-weight: bold;
                }}
                pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }}
                code {{ background: #eee; padding: 2px 4px; border-radius: 2px; }}
            </style>
            </head>
            <body>
                <h1>智能旅行规划报告</h1>
                <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                <h2>AI总结报告</h2>
                {markdown.markdown(summary, extensions=['tables', 'fenced_code', 'codehilite']) if summary else ''}
                <h2>完整对话记录</h2>
                {markdown.markdown(conversation_data, extensions=['tables', 'fenced_code', 'codehilite'])}
                <hr>
                <p style="color:#888;">本报告由青鸾向导AI旅行规划系统生成</p>
            </body>
            </html>
            """

            # 指定wkhtmltopdf.exe的路径，请确保这个路径是正确的
            config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
            
            # 从字符串生成PDF
            pdfkit.from_string(html_content, pdf_path, configuration=config, options={"enable-local-file-access": ""})

            # 返回下载链接
            download_link = f"/static/pdfs/{pdf_filename}"
            return f"PDF已成功生成，您可以通过以下链接下载: <a href='{download_link}' target='_blank'>下载PDF</a>"

        except FileNotFoundError:
            return "PDF生成失败: 未找到 wkhtmltopdf.exe。请检查路径 `C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe` 是否正确，或将其添加到系统环境变量 PATH 中。"
        except Exception as e:
            return f"PDF生成失败: {str(e)}"

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
        
        # 获取API配置
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_URL")
        
        if not self.api_key:
            raise ValueError("未配置OpenAI API密钥")
        
        # 创建LLM实例
        self.llm = ChatOpenAI(
            temperature=0.1,
            api_key=SecretStr(self.api_key),
            model="gpt-4.1-nano",
            base_url=self.base_url,
            streaming=True
        )
        
        # 创建PDF生成工具
        self.pdf_tool = PDFGeneratorTool()
        
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
            ),
        ]
        #pdf生成工具
        self.tools_pdf=[
            Tool(
                name="pdf_generator",
                description="生成旅行规划PDF报告，输入对话内容和总结",
                func=self.pdf_tool.generate_travel_pdf
            )
        ]
        
        # 创建记忆
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 创建信息收集智能体
        # 注意：LangChain agents已被弃用，建议未来迁移到LangGraph
        self.collector_agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=False,
            handle_parsing_errors=True,
            agent_kwargs={
                "system_message": INFORMATION_COLLECTOR_PROMPT
            }
        )
        
        # 创建行程规划智能体（使用相同的工具集）
        # 注意：LangChain agents已被弃用，建议未来迁移到LangGraph
        self.planner_agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
            handle_parsing_errors=True,
            agent_kwargs={
                "system_message": ITINERARY_PLANNER_PROMPT
            }
        )
        #pdf生成智能体
        # 注意：LangChain agents已被弃用，建议未来迁移到LangGraph
        self.pdf_agent = initialize_agent(
            tools=self.tools_pdf,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
            handle_parsing_errors=True,
            agent_kwargs={
                "system_message": PDF_PROMPT
            }
        )
    
    def collect_travel_information_stream(self, travel_request: str, messages: list[BaseMessage]):
        """流式收集旅行信息"""
        # 构建完整的提示词
        full_prompt = f"""
{INFORMATION_COLLECTOR_PROMPT}

历史对话记忆：
{self._format_messages_for_prompt(messages)}

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
        
        # 使用智能体流式调用
        try:
            for chunk in self.collector_agent.stream({"input": full_prompt}):
                if "output" in chunk and chunk["output"]:
                    yield chunk["output"]
                elif "content" in chunk and chunk["content"]:
                    yield chunk["content"]
        except Exception as e:
            # 如果智能体调用失败，回退到直接LLM调用
            yield f"\n\n⚠️ 信息收集智能体调用失败，使用备用方案...\n\n"
            collect_prompt = f"""{INFORMATION_COLLECTOR_PROMPT}\n{full_prompt}"""
            for chunk in self.llm.stream([SystemMessage(content=collect_prompt)]):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
    
    def create_detailed_itinerary_stream(self, travel_request: str, collected_info: str):
        """流式创建详细行程"""
        # 构建完整的提示词
        full_prompt = f"""
{ITINERARY_PLANNER_PROMPT}

用户旅行需求：
{travel_request}

收集到的信息：
{collected_info}

请基于以上信息制定详细的旅行方案，确保方案实用、可执行，并严格控制在用户预算范围内，以Markdown格式整理输出。
"""
        
        # 使用智能体流式调用
        try:
            for chunk in self.planner_agent.stream({"input": full_prompt}):
                if "output" in chunk and chunk["output"]:
                    yield chunk["output"]
                elif "content" in chunk and chunk["content"]:
                    yield chunk["content"]
        except Exception as e:
            # 如果智能体调用失败，回退到直接LLM调用
            yield f"\n\n⚠️ 行程规划智能体调用失败，使用备用方案...\n\n"
            planning_prompt = f"""{ITINERARY_PLANNER_PROMPT}\n{full_prompt}"""

            for chunk in self.llm.stream([SystemMessage(content=planning_prompt)]):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
    
    def _format_messages_for_prompt(self, messages: list[BaseMessage]) -> str:
        """格式化消息列表为提示词"""
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append(f"用户: {msg.content}")
            elif isinstance(msg, AIMessage):
                formatted_messages.append(f"助手: {msg.content}")
            elif isinstance(msg, SystemMessage):
                formatted_messages.append(f"系统: {msg.content}")
        
        return "\n".join(formatted_messages)

# 智能体类型枚举
# 使用 langchain.agents.AgentType，避免自定义覆盖

def get_agent_response_stream(user_message, user_email, agent_type="general", conv_id=None):
    """获取智能体响应流"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_URL")
    
    if not api_key:
        raise ValueError("OPENAI API key not configured")
    
    # 选择系统提示
    if agent_type == "travel":
        system_prompt = TRAVEL_SYSTEM_PROMPT
    elif agent_type == "pdf_generator":
        system_prompt = PDF_PROMPT
    else:
        system_prompt = GENERAL_SYSTEM_PROMPT
    
    # 生成智能体标识（包含用户、类型和对话ID）
    agent_key = f"{user_email}_{agent_type}_{conv_id}" if conv_id else f"{user_email}_{agent_type}"
    
    # 为每个用户创建独立的LLM实例
    if agent_key not in user_agents:
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
        
        user_agents[agent_key] = {
            'llm': llm,
            'memory': memory,
            'agent_type': agent_type,
            'conv_id': conv_id
        }
    
    user_agent = user_agents[agent_key]
    llm = user_agent['llm']
    memory = user_agent['memory']
    
    try:
        # 获取历史对话
        chat_history = memory.chat_memory.messages
        
        # 构建消息列表
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        
        # 添加历史对话（限制长度）
        for msg in chat_history[-30:]:
            if isinstance(msg, HumanMessage):
                messages.append(HumanMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(AIMessage(content=msg.content))
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))
        
        # 根据智能体类型处理
        if agent_type == "travel":
            yield from handle_travel_planning_stream(user_message, user_email, messages, conv_id)
            return
        elif agent_type == "pdf_generator":
            # 对于PDF生成，直接返回生成的内容（非流式）
            pdf_content = generate_pdf_content(user_message, user_email, messages, conv_id)
            yield pdf_content
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
        if agent_key in user_agents:
            del user_agents[agent_key]
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

def handle_travel_planning_stream(travel_request: str, user_email: str, messages: list[BaseMessage], conv_id=None):
    """处理旅行相关请求的流式响应"""
    try:
        planner = MultiAgentTravelPlanner(user_email)
        
        # 初始化完整响应变量
        full_response = ""
        
        # 判断是否为完整的旅行规划请求
        if is_travel_planning_request(travel_request):
            # 完整的旅行规划请求 - 使用两阶段处理
            yield "\n\n## 🔍 正在收集旅行信息...\n\n"
            
            collected_info = ""
            for chunk in planner.collect_travel_information_stream(travel_request, messages):
                yield chunk
                if isinstance(chunk, str):
                    collected_info += chunk
                    full_response += chunk
                else:
                    collected_info += str(chunk)
                    full_response += str(chunk)
            
            # 阶段2：行程规划
            yield "\n\n---\n\n## 📋 正在制定详细行程...\n\n"
            
            for chunk in planner.create_detailed_itinerary_stream(travel_request, collected_info):
                yield chunk
                if isinstance(chunk, str):
                    full_response += chunk
                else:
                    full_response += str(chunk)
        else:
            # 一般的旅行问题 - 直接调用LLM
            for chunk in planner.llm.stream([SystemMessage(content=TRAVEL_SYSTEM_PROMPT), HumanMessage(content=travel_request)]):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    full_response += str(chunk.content)
        
        # 保存到记忆
        agent_key = f"{user_email}_travel_{conv_id}" if conv_id else f"{user_email}_travel"
        if agent_key in user_agents:
            memory = user_agents[agent_key]['memory']
            memory.chat_memory.add_user_message(travel_request)
            memory.chat_memory.add_ai_message(full_response)
            
    except Exception as e:
        yield f"\n\n❌ 旅行规划过程中出现错误: {str(e)}\n\n"

"""
此函数已被generate_pdf_content取代，保留此注释以便于代码维护
"""

def generate_pdf_content(user_message: str, user_email: str, messages: list[BaseMessage], conv_id=None):
    """生成PDF内容（非流式）"""
    try:
        # 创建PDF智能体实例
        planner = MultiAgentTravelPlanner(user_email)
        
        # 从历史消息中提取对话内容，过滤掉系统消息
        conversation_content = ""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                conversation_content += f"用户: {msg.content}\n\n"
            elif isinstance(msg, AIMessage):
                conversation_content += f"助手: {msg.content}\n\n"
        
        # 如果对话内容为空，提供默认提示
        if not conversation_content.strip():
            conversation_content = "暂无对话历史，请先进行旅行规划对话。"
        
        try:
            # 生成摘要
            summary_prompt = f"""
请为以下旅行对话生成一个简洁的摘要，突出关键的旅行信息（目的地、时间、预算、人数等）。
这个摘要将用于PDF报告的开头部分。请保持在300字以内，使用Markdown格式。

对话内容：
{conversation_content}

用户需求：
{user_message}

一定要使用Markdown格式输出摘要，确保内容清晰易读,表格要让pdfkit能够渲染。
"""
            summary_response = planner.llm.invoke([SystemMessage(content=summary_prompt)])
            summary = summary_response.content
            # 确保 summary 是字符串类型
            if not isinstance(summary, str):
                summary = str(summary)
                
            # 提取目的地信息（如果有）
            destination = "旅行"
            import re
            destination_match = re.search(r'(前往|去|到|游览|旅行)[到至]?([\u4e00-\u9fa5a-zA-Z]+)', conversation_content)
            if destination_match:
                destination = destination_match.group(2)
            
            # 调用PDF生成工具，传递用户邮箱和目的地信息
            user_info = f"{user_email}_{destination}"
            pdf_result = planner.pdf_tool.generate_travel_pdf(conversation_content, summary, user_info)
            
            # 记录到用户记忆（如果存在）
            agent_key = f"{user_email}_pdf_generator_{conv_id}" if conv_id else f"{user_email}_pdf_generator"
            if agent_key in user_agents:
                memory = user_agents[agent_key]['memory']
                memory.chat_memory.add_user_message(user_message)
                memory.chat_memory.add_ai_message(f"已生成PDF报告: {pdf_result}")
            
            return pdf_result
            
        except Exception as e:
            return f"PDF生成失败: {str(e)}"
        
    except Exception as e:
        return f"PDF生成过程中出现错误: {str(e)}"

# 保留原来的函数用于兼容性
def get_agent_response(user_message, user_email, agent_type="general", conv_id=None):
    """获取完整的AI响应（非流式）"""
    response_text = ""
    for chunk in get_agent_response_stream(user_message, user_email, agent_type, conv_id):
        response_text += chunk
    return response_text

# 清理用户智能体
def clear_user_agents(user_email: str, conv_id=None):
    """清理用户的所有智能体实例"""
    if conv_id:
        # 清理特定对话的智能体
        agent_keys = [key for key in user_agents.keys() if key.startswith(f"{user_email}_") and conv_id in key]
    else:
        # 清理用户的所有智能体
        agent_keys = [key for key in user_agents.keys() if key.startswith(f"{user_email}_")]
    
    for key in agent_keys:
        del user_agents[key]