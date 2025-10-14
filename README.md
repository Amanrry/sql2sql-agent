# SQL-to-SQL医学Multi-Agent系统

基于MIMIC-IV电子健康记录数据库的SQL-to-SQL自动化分析系统。

## 特性

- 🤖 **Multi-Agent协作**: 4个专业Agent分工协作
- ⚡ **并行执行**: 扩展查询并行执行，性能提升3-10倍
- 🔄 **ReAct模式**: Data Profiling和Execute Agent采用ReAct模式
- 🏥 **医学智能**: 结合外部医学知识库增强查询准确性
- 📊 **迭代探索**: 多轮迭代逐步揭示数据洞察

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenAI兼容API配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.siliconflow.cn/v1
MODEL_NAME=deepseek-ai/DeepSeek-V3.2-Exp

# 搜索API密钥
TAVILY_API_KEY=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
```

### 3. 准备数据库

确保 `mimic_iv.sqlite` 和 `tables.json` 在项目根目录。

### 4. 运行示例

```bash
python main.py
```

## 项目结构

```
mimic_iv/
├── sql2sql_agent/          # 核心代码
│   ├── agents/             # Agent实现
│   ├── prompts/            # Prompt模板
│   ├── tools/              # 工具封装
│   ├── utils/              # 工具函数
│   ├── config.py           # 配置管理
│   ├── state.py            # State定义
│   └── graph.py            # LangGraph工作流
├── examples/               # 示例代码
├── tests/                  # 测试代码
├── main.py                 # 主入口
├── requirements.txt        # 依赖包
├── .env.example            # 环境变量模板
└── SQL2SQL_SYSTEM_DESIGN.md  # 系统设计文档
```

## 使用示例

```python
from sql2sql_agent.graph import create_sql2sql_graph
from sql2sql_agent.config import Config

# 加载配置
config = Config.from_env()
config.validate_config()

# 创建工作流
app = create_sql2sql_graph(config)

# 定义输入
initial_state = {
    "user_query": "分析本季度因急性心肌梗死入院患者的住院天数和再入院情况",
    "seed_sql": """
        SELECT AVG(JULIANDAY(dischtime) - JULIANDAY(admittime)) as avg_los
        FROM admissions a
        JOIN diagnoses_icd d ON a.hadm_id = d.hadm_id
        WHERE d.icd_code = '41071' AND a.admittime >= '2024-10-01'
    """,
    "db_path": config.db_path,
    "max_iterations": config.max_iterations,
    ...
}

# 运行分析
final_state = await app.ainvoke(initial_state)
print(final_state["final_report"])
```

## 性能优势

- **并行执行**: 3个查询从30秒降至10秒（3倍提升）
- **容错性强**: 单个查询失败不影响其他查询
- **资源高效**: 充分利用异步IO

## 文档

- [系统设计文档](./SQL2SQL_SYSTEM_DESIGN.md)
- [数据集说明](./dataset.md)
- [SQLite MCP配置](./sqlite%20mcp.md)

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
