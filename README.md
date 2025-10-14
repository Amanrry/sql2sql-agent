# SQL-to-SQL 医学多智能体系统

基于MIMIC-IV医疗数据库的Text-to-SQL多智能体系统，能够从初始医学查询出发，自动生成衍生分析查询并执行，提供全面的数据洞察。

## 系统架构

### 核心组件

- **Planning Agent**: 负责任务规划、衍生查询生成、结果聚合和迭代控制
- **Execute SubAgent**: 负责Text-to-SQL转换、SQL执行、错误处理和洞察生成
- **工具集成**:
  - SQLite MCP Server: 数据库交互
  - Tavily Search: 医学知识获取

### 执行流程

```
用户查询
   ↓
执行初始查询 (Execute SubAgent)
   ↓
生成衍生查询 (Planning Agent)
   ↓
并行执行衍生查询 (多个Execute SubAgent)
   ↓
聚合和筛选结果 (Planning Agent)
   ↓
判断是否继续迭代
   ↓
生成最终医学报告
```

### 衍生策略

Planning Agent从四个维度生成衍生查询：

1. **理解** (Understanding): 深入解读数据含义
2. **总结** (Summarization): 按科室/时间/患者群体分组分析
3. **比较** (Comparison): 对比不同组别、历史趋势
4. **解释** (Explanation): 分析异常值和根本原因

## 快速开始

### 1. 安装依赖

```bash
pip install langgraph langchain-openai langchain-mcp-adapters langchain-tavily python-dotenv
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenRouter API配置
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_API_BASE=https://openrouter.ai/api/v1

# LLM模型配置
LLM_MODEL=deepseek/deepseek-chat-v3.1:free
LLM_TEMPERATURE=0.1

# Tavily搜索API配置
TAVILY_API_KEY=your_tavily_api_key_here

# LangSmith追踪配置（可选，用于监控Agent执行过程）
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langsmith_api_key_here

# SQLite数据库路径
SQLITE_DB_PATH=D:\Dev Project\mimic_iv\mimic_iv.sqlite
SQLITE_MCP_PATH=D:\Dev Project\mimic_iv\sqlite

# 系统配置
MAX_ITERATIONS=3
MAX_SQL_RETRIES=5
AGENT_RECURSION_LIMIT=100
```

**启用LangSmith监控（可选）**：

如果需要监控Agent的执行过程，可以启用LangSmith：

1. 在 [LangSmith](https://smith.langchain.com/) 注册账号并获取API Key
2. 在 `.env` 中设置：
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key_here
   ```
3. 运行系统时会自动上传追踪数据到LangSmith
4. 在LangSmith控制台查看详细的执行流程和工具调用

### 3. 验证配置

```bash
python main.py --validate-config
```

### 4. 运行系统

#### 方式一：命令行模式

```bash
# 直接执行查询
python main.py "统计患者总数"

# 指定最大迭代次数
python main.py "查询急性心肌梗死患者的平均住院天数" --max-iterations 5

# 保存报告到文件
python main.py "按科室统计住院患者数量" -o report.md
```

#### 方式二：交互模式

```bash
# 启动交互式界面
python main.py
```

进入交互模式后：
- 输入医学查询，系统自动执行
- 输入 `help` 查看示例查询
- 输入 `quit` 或 `exit` 退出

## 使用示例

### 示例1：基础统计查询

```bash
python main.py "统计患者总数"
```

系统会：
1. 执行初始查询获取患者总数
2. 自动生成衍生查询（如按性别/年龄分组统计）
3. 并行执行所有衍生查询
4. 生成综合分析报告

### 示例2：复杂医学分析

```bash
python main.py "统计本季度因急性心肌梗死入院患者的平均住院天数和30天再入院率"
```

系统可能生成的衍生查询：
- 按科室分组统计心肌梗死患者的治疗指标
- 对比不同年龄段患者的住院时长
- 分析心肌梗死患者的常用药物处方
- 统计患者的主要合并症
- 对比历史趋势

### 示例3：交互模式

```
$ python main.py

🏥 SQL-to-SQL医学多智能体系统 - 交互模式
============================================================

🔍 请输入查询 > 统计ICU患者数量

[系统执行...]

📄 报告
============================================================
...
```

## 项目结构

```
sql2sql_agent/
├── .env.example          # 环境变量模板
├── config.py             # 配置管理
├── state.py              # LangGraph状态定义
├── tools.py              # 工具配置 (MCP + Tavily)
├── prompts.py            # Agent提示词模板
├── execute_agent.py      # Execute SubAgent实现
├── planning_agent.py     # Planning Agent实现
├── graph.py              # LangGraph图定义
├── main.py               # 主入口
└── README.md             # 项目文档
```

## 核心功能

### Execute SubAgent

负责将自然语言查询转换为SQL并执行：

1. **理解查询**: 分析医学术语，必要时搜索医学知识
2. **获取Schema**: 使用MCP工具获取数据库结构
3. **生成SQL**: 根据理解生成准确的SQL语句
4. **执行和重试**: 执行SQL，失败时自动重试（最多5次）
5. **生成洞察**: 解读查询结果的医学意义

### Planning Agent

负责整体规划和协调：

1. **分析结果**: 理解当前查询结果
2. **生成衍生查询**: 从理解、总结、比较、解释四个维度生成3-5个衍生查询
3. **迭代控制**: 判断是否需要继续探索
4. **报告生成**: 综合所有结果生成医学报告

## 技术特点

- ✅ **多智能体协作**: Planning Agent和多个Execute SubAgent协同工作
- ✅ **并行执行**: 衍生查询并行执行，提高效率
- ✅ **智能重试**: SQL执行失败自动分析错误并重试
- ✅ **迭代优化**: 支持多轮迭代，逐步深入分析
- ✅ **医学知识增强**: 集成Tavily搜索获取医学领域知识
- ✅ **灵活配置**: 支持自定义迭代次数、模型参数等
- ✅ **可观测性**: 可选LangSmith追踪，监控Agent执行全过程

## 数据库说明

系统使用MIMIC-IV医疗数据库，包含以下核心表：

- `patients`: 患者基本信息
- `admissions`: 住院记录
- `diagnoses_icd`: ICD诊断编码
- `procedures_icd`: ICD手术编码
- `labevents`: 实验室检查结果
- `prescriptions`: 药物处方
- `chartevents`: 生命体征监护
- `icustays`: ICU住院记录
- `transfers`: 科室转移记录

## 常见问题

### Q: 配置验证失败怎么办？

A: 确保：
1. 已复制 `.env.example` 为 `.env`
2. 填写了所有必需的API Key
3. SQLite数据库路径正确
4. SQLite MCP路径正确

### Q: 如何获取API Key？

A:
- OpenRouter API Key: https://openrouter.ai/
- Tavily API Key: https://tavily.com/
- LangSmith API Key (可选): https://smith.langchain.com/

### Q: 如何启用LangSmith监控？

A: LangSmith是LangChain提供的可观测性平台，用于监控Agent执行过程：

1. 注册LangSmith账号：https://smith.langchain.com/
2. 获取API Key
3. 在 `.env` 中配置：
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_xxxxx
   ```
4. 运行系统，在LangSmith控制台可以看到：
   - 每个Agent的思考过程
   - 工具调用的详细信息
   - SQL生成和执行记录
   - 错误和重试记录
   - 完整的执行时间线

### Q: 支持哪些LLM模型？

A: 支持所有OpenRouter提供的模型，在 `.env` 中配置 `LLM_MODEL` 即可。推荐：
- `deepseek/deepseek-chat-v3.1:free` (免费)
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4`

### Q: 如何调整迭代次数？

A:
- 在 `.env` 中设置 `MAX_ITERATIONS`
- 或在命令行使用 `--max-iterations` 参数

### Q: 查询执行失败怎么办？

A: 系统会自动重试最多5次。如果仍失败，检查：
1. 查询是否包含不存在的表或字段
2. SQL语法是否符合SQLite规范
3. 数据库连接是否正常

## 开发说明

### 测试单个模块

```bash
# 测试配置
python config.py

# 测试状态定义
python state.py

# 测试工具
python tools.py

# 测试Execute Agent
python execute_agent.py

# 测试Planning Agent
python planning_agent.py

# 测试LangGraph图
python graph.py
```

### 自定义提示词

编辑 `prompts.py` 文件中的 `EXECUTE_AGENT_PROMPT` 和 `PLANNING_AGENT_PROMPT` 来自定义Agent行为。

### 添加新工具

在 `tools.py` 中添加新的工具，然后在 `get_all_tools()` 函数中返回。

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 致谢

- MIMIC-IV数据库: https://physionet.org/content/mimic-iv-demo/
- LangGraph: https://github.com/langchain-ai/langgraph
- LangChain: https://github.com/langchain-ai/langchain
