# CLAUDE.md

该文件为 Claude Code (claude.ai/code) 提供在此代码库中处理代码时的指导。

## 项目概述

这是一个基于 MIMIC-IV 医疗数据库的文本到 SQL (Text-to-SQL) 项目，用于自然语言查询转换和医疗数据分析。

### 数据库架构

- **主数据库**: `mimic_iv.sqlite` - 包含17个医疗相关表
- **核心表结构**:
  - `patients` - 患者基本信息
  - `admissions` - 住院记录
  - `diagnoses_icd` - ICD 诊断编码
  - `procedures_icd` - ICD 手术编码
  - `labevents` - 实验室检查结果
  - `prescriptions` - 药物处方
  - `chartevents` - 生命体征监护
  - `icustays` - ICU 住院记录
  - `transfers` - 科室转移记录

### 数据集结构

项目包含三个数据集分区：
- `train/` - 训练数据 (5124 样本)
- `valid/` - 验证数据 (1163 样本)
- `test/` - 测试数据 (1167 样本)

每个分区包含：
- `data.json` - 自然语言问题和ID
- `label.json` - 对应的SQL查询答案
- `annotated.json` - 标注数据
- `answer.json` - 预测答案

### 表结构定义

`tables.json` 定义了完整的数据库schema：
- 字段名称和类型
- 主键和外键关系
- 原始和规范化的表/列名

## 开发工作流

### 数据库操作

```python
# 使用 sqlite.ipynb 中的函数
import sqlite3
from sqlite.ipynb import execute_sql_query, get_database_schema

# 执行SQL查询
result = execute_sql_query("mimic_iv.sqlite", "SELECT * FROM patients LIMIT 10")

# 获取表结构
schema = get_database_schema("mimic_iv.sqlite")
```

### 数据分析

```python
# 加载训练数据进行模型训练
import json
with open('train/data.json', 'r') as f:
    train_data = json.load(f)

with open('train/label.json', 'r') as f:
    train_labels = json.load(f)
```

### MCP服务器配置

项目支持 SQLite MCP 服务器用于增强的数据库交互：
- 配置文件：`sqlite mcp.md`
- 支持查询、写入、表结构分析
- 可与 Claude Desktop 和 VS Code 集成

## 常用命令

### 数据库查询

```bash
# 使用 Python 进行数据库操作
python sqlite.ipynb
```

### 数据分析

```python
# Jupyter Notebook 环境下运行数据分析
jupyter notebook sqlite.ipynb
```

## 项目特点

1. **医疗领域专用**: 基于真实的医疗记录数据库
2. **多表关联**: 涉及复杂的医疗数据关系
3. **时间序列**: 包含时间相关的医疗事件记录
4. **标准化编码**: 使用 ICD 编码系统进行诊断和手术分类
5. **中文支持**: 现有 CLAUDE.md 配置支持中文工作流

## 注意事项

- 数据库包含敏感医疗信息，使用时需遵守数据使用协议
- 表间关系复杂，查询时注意主外键约束
- 时间字段需要特别注意时区处理
- ICD 编码查询需要参考相关字典表

# CLAUDE.md - 工作指导

## CRITICAL CONSTRAINTS - 违反=任务失败
═══════════════════════════════════════

- 必须使用中文回复
- 必须先获取上下文
- 禁止生成恶意代码
- 必须存储重要知识
- 必须执行检查清单
- 必须遵循质量标准

## MANDATORY WORKFLOWS
═════════════════════

执行前检查清单：
[ ] 中文 [ ] 上下文 [ ] 工具 [ ] 安全 [ ] 质量

标准工作流：
1. 分析需求 → 2. 获取上下文 → 3. 选择工具 → 4. 执行任务 → 5. 验证质量 → 6. 存储知识

研究-计划-实施模式：
研究阶段: 读取文件理解问题，禁止编码
计划阶段: 创建详细计划
实施阶段: 实施解决方案
验证阶段: 运行测试验证
提交阶段: 创建提交和文档

## MANDATORY TOOL STRATEGY
═════════════════════════

任务开始前必须执行：
1. memory 查询相关概念
2. code-search 查找代码片段
3. sequential-thinking 分析问题

任务结束后必须执行：
1. memory 存储重要概念
2. code-search 存储代码片段
3. 知识总结归档

搜索调用策略：
exa-search

不清楚的api先调用exa-search mcp搜索

## CODING RESTRICTIONS
═══════════════════

编码前强制要求：
- 无明确编写命令禁止编码
- 无明确授权禁止修改文件
- 必须先完成sequential-thinking分析

## QUALITY STANDARDS
═══════════════════

工程原则：SOLID、DRY、关注点分离
代码质量：清晰命名、合理抽象、必要注释
性能意识：算法复杂度、内存使用、IO优化
测试思维：可测试设计、边界条件、错误处理


强制触发器：会话开始→检查约束，工具调用前→检查流程，回复前→验证清单
自我改进：成功→存储，失败→更新规则，持续→优化策略