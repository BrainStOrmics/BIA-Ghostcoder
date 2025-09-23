# BIA-Ghostcoder

> **AI-Powered Bioinformatics Analysis Agent**  
> 一个基于多模型协作的智能生物信息学分析代理，自动生成、执行和优化分析代码

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🎯 项目简介

**BIA-Ghostcoder** 是一个基于大语言模型（LLM）和 LangGraph 框架的智能生物信息学分析代理系统。它能够根据用户的自然语言描述，自动规划分析流程、生成执行代码、并进行结果评估与优化，特别专注于单细胞RNA测序（scRNA-seq）等生物信息学分析任务。

### 🌟 核心功能

- **🤖 智能任务规划**: 基于任务描述自动分解复杂的生物信息学分析流程
- **📝 自动代码生成**: 支持 Python/R 双语言代码生成，集成主流生物信息学工具包
- **🔄 迭代优化**: 自动执行代码、评估结果，并根据反馈进行改进
- **🗃️ 知识检索**: 内置生物信息学代码库，支持RAG（检索增强生成）
- **🐳 容器化执行**: 基于 Docker 的安全代码执行环境

### 💡 主要亮点

1. **多模型协作架构**: Chat/Code/Embedding 模型分工协作，针对不同任务优化
2. **专业领域知识**: 内置单细胞分析工作流指南和参考代码库
3. **安全执行环境**: Docker 容器隔离，支持多种预配置分析环境
4. **自适应数据感知**: 智能识别数据格式并选择合适的分析语言和工具
5. **Web 检索集成**: 结合 Tavily 搜索，获取最新的分析方法和工具

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Docker
- Git

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/BIA-Ghostcoder.git
cd BIA-Ghostcoder
```

2. **安装依赖**
```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

3. **配置环境**
```bash
# 复制配置模板
cp example_config.yaml config.yaml

# 编辑配置文件，填入你的 API 密钥
nano config.yaml
```

### 配置示例

```yaml
llm_config:
  CHAT_MODEL_API:
    api: "your_openai_api_key"
    url: "https://api.openai.com/v1"
    model: "gpt-4o"
    type: openai
  
  CODE_MODEL_API:
    api: "your_openai_api_key" 
    url: "https://api.openai.com/v1"
    model: "gpt-4o"
    type: openai

  EMBED_MODEL_API:
    api: "your_openai_api_key"
    url: "https://api.openai.com/v1"  
    model: "text-embedding-3-small"
    type: openai

tavily_config:
  API_KEY: "your_tavily_api_key"
  MAX_RESULTS: 7

ghostcoder_config:
  DB_RETRIEVE: true
  MAX_ITER: 5
  TASK_ID: "your_task_name"
```

### 快速示例

```python
import scanpy as sc
from langchain_openai import ChatOpenAI
from ghostcoder import GhostCoder
from ghostcoder.utils import *

# 初始化模型
chat_model = ChatOpenAI(api_key="your_key", model="gpt-4o")
code_model = ChatOpenAI(api_key="your_key", model="gpt-4o")

# 创建 GhostCoder 实例
agent = GhostCoder(
    chat_model=chat_model,
    code_model=code_model,
    max_retry=3
)

# 准备数据
adata = sc.datasets.pbmc3k()

# 包装输入变量
input_wrap = create_input_wrapper([adata])

# 执行分析任务
task = "对单细胞数据进行质量控制，过滤低质量细胞，并进行基本的预处理"
codeblock, execution_result = agent.Run(
    task=task,
    input_wrap=input_wrap,
    task_id="pbmc_qc_demo"
)

print("生成的代码:")
print(codeblock)
print("\n执行结果:")
print(execution_result)
```

---

## 📁 项目结构

```
BIA-Ghostcoder/
├── ghostcoder/                 # 核心代码包
│   ├── graph/                  # LangGraph 工作流模块
│   │   ├── ghostcoder.py      # 主工作流图
│   │   ├── coder.py           # 代码生成子图
│   │   ├── retriever.py       # 知识检索子图
│   │   ├── filemanager.py     # 文件管理子图
│   │   ├── executor.py        # 代码执行模块
│   │   └── webcrawler.py      # 网络爬虫模块
│   ├── prompts/               # 提示词模板
│   │   ├── ghostcoder.*.md    # 主流程提示词
│   │   ├── coder.*.md         # 代码生成提示词
│   │   └── workflow_guidlines/ # 工作流指南
│   ├── docker/                # Docker 配置
│   │   └── BIA_dockers.json   # 预配置镜像
│   ├── utils/                 # 工具函数
│   │   ├── data.py           # 数据处理工具
│   │   ├── execute.py        # 执行工具
│   │   └── io.py             # 输入输出工具
│   ├── Agent.py              # 主代理类
│   └── config.py             # 配置管理
├── RefcodeDB/                 # 参考代码数据库
│   ├── BuildVectorDB.ipynb   # 向量数据库构建
│   └── RefCodeDB.csv         # 代码库数据
├── Experiments/              # 实验示例
│   └── DEMO.ipynb           # 演示笔记本
├── Test/                     # 测试文件
├── example_config.yaml       # 配置文件模板
└── pyproject.toml           # 项目配置
```

### 核心模块说明

- **`ghostcoder/graph/`**: 基于 LangGraph 的多代理工作流系统
  - `ghostcoder.py`: 主控制流程，协调各子模块
  - `coder.py`: 代码生成与执行，支持批评-改进循环
  - `retriever.py`: RAG 检索系统，从代码库和网络获取相关知识
  - `filemanager.py`: 数据文件管理和环境配置

- **`ghostcoder/prompts/`**: 精心设计的提示词模板库
  - 包含任务解析、代码生成、结果评估等各环节的专业提示词
  - 内置生物信息学工作流指南（如 scRNA-seq 分析流程）

- **`RefcodeDB/`**: 生物信息学参考代码知识库
  - 收录常用分析任务的高质量代码示例
  - 支持向量化检索，提供上下文感知的代码建议

---

## 🛠️ 高级用法

### 自定义分析流程

```python
# 复杂的分析任务
complex_task = """
对单细胞RNA测序数据执行完整分析流程：
1. 质量控制和数据预处理
2. 降维和聚类分析  
3. 差异基因表达分析
4. 细胞类型注释
5. 生成可视化结果
"""

codeblock, result = agent.Run(
    task=complex_task,
    input_wrap=input_wrap,
    task_id="full_scrna_analysis",
    use_reg=True  # 启用RAG检索
)
```

### 使用自定义 Docker 环境

```python
# 修改配置以使用特定的分析环境
import ghostcoder.config as config
config.docker_config.DEFAULT_DOCKER_PROFILE = "custom_bio_env.json"
```

### 可视化工作流

```python
# 绘制代理工作流图
agent.draw_graph()
```

---

## 🤝 贡献指南

我们欢迎社区贡献！请按照以下步骤参与项目：

### 提交 Issue

- 🐛 **Bug 报告**: 使用 `bug` 标签，提供复现步骤和环境信息
- 💡 **功能建议**: 使用 `enhancement` 标签，详细描述需求和用例
- 📖 **文档改进**: 使用 `documentation` 标签

### 提交 Pull Request

1. **Fork** 项目到你的 GitHub 账户
2. **创建特性分支**: `git checkout -b feature/amazing-feature`
3. **提交更改**: `git commit -m 'Add some amazing feature'`
4. **推送分支**: `git push origin feature/amazing-feature`
5. **创建 Pull Request**

### 代码规范

- 使用 Python 3.12+ 特性
- 遵循 PEP 8 代码风格
- 添加必要的类型注解
- 编写清晰的文档字符串
- 确保通过现有测试

### Commit 规范

```
type(scope): description

[optional body]

[optional footer]
```

**类型说明**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

---

## 📊 API 参考

### GhostCoder 类

```python
class GhostCoder:
    def __init__(
        self,
        chat_model: LanguageModelLike,
        code_model: LanguageModelLike,
        *,
        max_retry: int = 3,
        name: Optional[str] = "ghostcoder",
        debug: bool = False
    )
    
    def Run(
        self,
        task: str,                    # 分析任务描述
        input_wrap: dict,             # 输入数据包装
        task_id: str = "test",        # 任务标识符
        previous_codeblock: str = "", # 前置代码
        use_reg: bool = True          # 是否使用RAG检索
    ) -> Tuple[str, str]             # 返回: (代码, 执行结果)
```

### 工具函数

```python
# 数据包装
def create_input_wrapper(variables: list) -> dict

# 持久化变量
def persistent_vars(var_names: list, file_path: str = "vars.pkl")

# 数据观察
def observe_data(obj, var_name: str = "data") -> str
```

---

## ❓ 常见问题

### Q: 如何处理大型数据文件？
A: BIA-Ghostcoder 会自动识别大型生物信息学文件（如 .fastq, .bam），并生成适当的处理代码而不是直接加载到内存。

### Q: 支持哪些生物信息学工具？
A: 目前主要支持：
- **Python**: scanpy, pandas, matplotlib, seaborn, scipy
- **R**: Seurat, Monocle, SingleCellExperiment
- 可通过 Docker 扩展支持更多工具

### Q: 如何自定义提示词？
A: 修改 `ghostcoder/prompts/` 目录下的 markdown 文件，或通过配置指定自定义提示词路径。

### Q: 代码执行失败怎么办？
A: 系统具有自动重试和错误修复机制，会尝试最多 `max_retry` 次。可通过增加 `coder_config.MAX_ERROR` 提高容错性。

### Q: 如何添加新的参考代码？
A: 编辑 `RefcodeDB/RefCodeDB.csv`，添加新的代码示例和对应的任务描述，然后重新构建向量数据库。

---

## 🗺️ 开发路线

### 近期计划 (v0.2.0)
- [ ] 支持更多 LLM 提供商 (Anthropic, Google, etc.)
- [ ] 添加结果可视化模板库
- [ ] 优化错误处理和调试功能
- [ ] 扩展多组学数据分析支持

### 中期计划 (v0.3.0)
- [ ] 图形化用户界面 (Web UI)
- [ ] 协作分析工作空间
- [ ] 分析流程模板库
- [ ] 性能优化和缓存机制

### 长期愿景
- [ ] 多模态数据分析（图像、文本、序列）
- [ ] 社区驱动的插件生态
- [ ] 云端服务集成
- [ ] 教育和培训模块

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

```
MIT License

Copyright (c) 2025 Qi Xin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 致谢

感谢以下开源项目的支持：
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用开发框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 多代理工作流编排
- [Scanpy](https://github.com/scverse/scanpy) - 单细胞分析工具包
- [Seurat](https://github.com/satijalab/seurat) - R 单细胞分析包
- [Docker](https://www.docker.com/) - 容器化平台

---

## 📞 联系方式

- **项目维护者**: Qi Xin
- **GitHub Issues**: [提交问题](https://github.com/your-username/BIA-Ghostcoder/issues)
- **讨论区**: [GitHub Discussions](https://github.com/your-username/BIA-Ghostcoder/discussions)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

[⬆ 回到顶部](#bia-ghostcoder)

</div>
