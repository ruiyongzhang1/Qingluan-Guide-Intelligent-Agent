# AI Agent 代码重构说明

## 文件结构

### 1. `ai_agent.py` (主文件)
- **PDFGeneratorTool类**: PDF生成工具
- **MultiAgentTravelPlanner类**: 多智能体旅行规划系统
- **工具函数**: 各种处理函数和响应流处理
- **MCP工具集成**: MCP工具加载和管理

### 2. `prompts.py` (新增 - 提示词配置)
- **GENERAL_SYSTEM_PROMPT**: 通用系统提示词
- **TRAVEL_SYSTEM_PROMPT**: 旅行规划系统提示词
- **INFORMATION_COLLECTOR_PROMPT**: 信息收集智能体提示词
- **ITINERARY_PLANNER_PROMPT**: 行程规划智能体提示词
- **PDF_PROMPT**: PDF生成智能体提示词

## 重构优势

1. **提示词集中管理**: 所有提示词现在在单独的文件中，便于维护和修改
2. **代码更简洁**: 主文件现在专注于核心逻辑，不被大量提示词内容干扰
3. **易于扩展**: 新增提示词只需在prompts.py中添加，然后在ai_agent.py中导入
4. **版本控制友好**: 提示词修改不会影响主代码，减少合并冲突

## 使用方法

代码的使用方式保持不变，所有原有的API和接口都没有改变。只是内部结构更加清晰和模块化。

## 注意事项

- 确保`prompts.py`文件与`ai_agent.py`在同一目录下
- 如果需要修改提示词，只需编辑`prompts.py`文件
- 导入使用了相对导入和绝对导入的fallback机制，确保兼容性
