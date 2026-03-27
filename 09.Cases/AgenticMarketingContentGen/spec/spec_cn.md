> [English](spec.md) | **中文**

# 技术规范

基于 Microsoft Agent Framework 的自动化营销内容生成系统。

## 技术栈

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontSize': '16px', 'fontFamily': 'Inter, system-ui, sans-serif', 'primaryColor': '#6366f1', 'primaryTextColor': '#f8fafc', 'primaryBorderColor': '#4f46e5', 'lineColor': '#818cf8', 'background': '#0f172a', 'mainBkg': '#1e293b', 'clusterBkg': '#1e293b', 'clusterBorder': '#475569'}}}%%
flowchart LR
    subgraph Framework[" ⚙️ Microsoft Agent Framework "]
        direction TB
        SB["SequentialBuilder"]:::core
        CA["ChatAgent"]:::core
        EX["Executor"]:::core
        SB --- CA --- EX
    end
    
    subgraph LLM[" 🧠 LLM Providers "]
        AO["Azure OpenAI<br/>GPT-5"]:::llm
    end
    
    subgraph Tools[" 🔧 External Tools "]
        direction TB
        TV["🔍 Tavily Search"]:::tool
        FL["🎨 FLUX Image Gen"]:::tool
        SO["🎥 Sora-2 Video Gen"]:::tool
    end
    
    Framework ==> LLM
    Framework ==> Tools
    
    classDef core fill:#6366f1,stroke:#4f46e5,stroke-width:2px,color:#f8fafc,font-weight:bold
    classDef llm fill:#ec4899,stroke:#db2777,stroke-width:2px,color:#f8fafc,font-weight:bold
    classDef tool fill:#06b6d4,stroke:#0891b2,stroke-width:2px,color:#f8fafc,font-weight:bold
```

## 核心组件

### 1. AgenticMarketingWorkflow

主工作流类，负责：
- 初始化 ChatClient 和工具
- 创建 Agent 和 Executor
- 使用 SequentialBuilder 编排工作流
- 处理事件流和调试输出

```python
class AgenticMarketingWorkflow:
    def __init__(self, chat_client, *, config=None):
        # 初始化工具: TavilySearchTools, FluxImageGenerationTools, SoraVideoGenerationTools
        # 创建 Agents: create_marketing_agents()
        # 可选: 创建 DeepResearchExecutor

    async def run(self, topic: str) -> CampaignPackage:
        # 创建工作流并执行
        workflow = self._create_workflow(campaign_dir)
        async for event in workflow.run_stream(topic):
            # 处理事件...
```

### 2. Agent 定义 (agents.py)

四个专业 ChatAgent：

```python
def create_marketing_agents(chat_client, tool_registry=None) -> MarketingAgents:
    return MarketingAgents(
        strategy=_build_agent("strategy_agent", strategy_instructions),
        copywriting=_build_agent("copywriting_agent", copy_instructions),
        image=_build_agent("image_agent", image_instructions),
        video=_build_agent("video_agent", video_instructions),
    )
```

**Strategy Agent** - 执行多轮 web 搜索：
- 规划搜索策略（市场趋势、竞品、用户痛点）
- 至少调用 3 次 `web_search`
- 综合分析输出 MarketingStrategy

**Copywriting Agent** - 知识类种草文案专家：
- 第一人称真实体验感
- 痛点共鸣 → 发现方法 → 效果 → 行动引导
- 输出多平台文案 (LinkedIn, Instagram, 小红书)

**Image Agent** - 图像提示词工程师：
- 设计英文 prompt
- 可选调用 `generate_image` 工具

**Video Agent** - 视频脚本专家：
- 三幕式结构 (Problem/Solution/Transformation)
- 最多 6 场景，总时长 ≤72 秒
- 可选调用 `generate_video` 工具

### 3. DeepResearchExecutor (research.py)

可选的深度研究模式，替换 Strategy Agent。

#### 内部架构

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontSize': '14px', 'fontFamily': 'Inter, system-ui, sans-serif', 'actorBkg': '#6366f1', 'actorTextColor': '#f8fafc', 'actorBorder': '#4f46e5', 'signalColor': '#e2e8f0', 'signalTextColor': '#f8fafc', 'noteBkgColor': '#334155', 'noteTextColor': '#f8fafc', 'noteBorderColor': '#475569', 'activationBkgColor': '#1e293b', 'activationBorderColor': '#475569', 'sequenceNumberColor': '#f8fafc'}}}%%
sequenceDiagram
    autonumber
    participant W as 🚀 Workflow
    participant DRE as 🔬 DeepResearchExecutor
    participant P as 🎯 Planner
    participant R as 🕵️ Researcher
    participant A as 📊 Analyst
    participant T as 🌐 Tavily

    W->>+DRE: handle(conversation)
    Note over DRE: 📝 Extract topic from conversation
    
    rect rgba(6, 182, 212, 0.2)
        Note over DRE,P: 📋 Phase 1: Research Planning
        DRE->>+P: 请为主题制定研究计划
        P-->>-DRE: ResearchPlan JSON
        Note right of P: 3-5 研究维度<br/>搜索策略<br/>优先级排序
    end
    
    rect rgba(14, 165, 233, 0.2)
        Note over DRE,T: 🔍 Phase 2: Research Execution
        DRE->>+R: 执行搜索查询
        loop 每个研究维度 (high → low priority)
            R->>+T: web_search(query, depth=advanced)
            T-->>-R: search results
        end
        R-->>-DRE: ResearchFindings JSON
        Note right of R: 市场洞察<br/>数据点<br/>信息来源
    end
    
    rect rgba(236, 72, 153, 0.2)
        Note over DRE,A: 📈 Phase 3: Strategy Synthesis
        DRE->>+A: 综合研究数据生成策略
        A-->>-DRE: MarketingStrategy JSON
        Note right of A: 目标受众<br/>痛点/卖点<br/>内容框架
    end
    
    DRE-->>-W: ctx.send_message(strategy)
    Note over W: ✅ 传递给下游 Agents
```

#### 三个内部 Agent

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **Planner** | 分析主题，制定研究维度 | topic | ResearchPlan |
| **Researcher** | 执行多轮 web_search | ResearchPlan | ResearchFindings |
| **Analyst** | 综合分析，生成策略 | Plan + Findings | MarketingStrategy |

#### 实现代码

```python
class DeepResearchExecutor(Executor):
    def __init__(self, chat_client, search_tool, debug=False):
        self._research_agents = create_research_agents(chat_client, search_tool)

    @handler
    async def handle(self, conversation, ctx):
        topic = self._extract_topic(conversation)
        
        # Phase 1: Research Planning
        plan = await self._run_planning(topic)
        # -> {"research_dimensions": [...], "target_insights": [...]}
        
        # Phase 2: Execute Research (多轮搜索)
        findings = await self._run_research(topic, plan)
        # -> {"research_findings": [...], "market_overview": "..."}
        
        # Phase 3: Synthesize Strategy
        strategy = await self._run_analysis(topic, plan, findings)
        # -> MarketingStrategy JSON
        
        await ctx.send_message([...conversation, strategy_message])
```

### 4. 工具实现 (tools.py)

**TavilySearchTools** - Web 搜索：
```python
@ai_function
def web_search(query, search_depth="basic", max_results=5) -> dict
```

**FluxImageGenerationTools** - FLUX 图像生成：
```python
@ai_function
def generate_image(prompt, prompt_id, size="1024x1024") -> dict
```

**SoraVideoGenerationTools** - Sora-2 视频生成：
```python
@ai_function  
def generate_video(prompt, scene_id, seconds=5, size="1280x720") -> dict
```

### 5. PackagingExecutor

收集所有 Agent 输出，组装为 CampaignPackage：

```python
class _PackagingExecutor(Executor):
    @handler
    async def handle(self, conversation, ctx):
        package = self._build_package(conversation)
        package = package.with_package_path(
            self._packaging_tools.persist_package(package)
        )
        await ctx.yield_output(package)
```

## 工作流编排

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontSize': '16px', 'fontFamily': 'Inter, system-ui, sans-serif', 'primaryColor': '#6366f1', 'primaryTextColor': '#f8fafc', 'primaryBorderColor': '#4f46e5', 'lineColor': '#818cf8', 'background': '#0f172a', 'mainBkg': '#1e293b', 'clusterBkg': '#1e293b', 'clusterBorder': '#475569'}}}%%
flowchart LR
    subgraph Pipeline[" ⛓️ SequentialBuilder.participants "]
        direction LR
        S["🎯 Strategy"]:::phase1 
        C["✍️ Copywriting"]:::phase2
        I["🖼️ Image"]:::phase2
        V["🎬 Video"]:::phase2
        P["📦 Packaging"]:::phase3
        
        S ==> C ==> I ==> V ==> P
    end
    
    P ==> O(["🎁 CampaignPackage"]):::output
    
    classDef phase1 fill:#06b6d4,stroke:#0891b2,stroke-width:2px,color:#f8fafc,font-weight:bold
    classDef phase2 fill:#0ea5e9,stroke:#0284c7,stroke-width:2px,color:#f8fafc,font-weight:bold
    classDef phase3 fill:#f97316,stroke:#ea580c,stroke-width:2px,color:#f8fafc,font-weight:bold
    classDef output fill:#ec4899,stroke:#db2777,stroke-width:2px,color:#f8fafc,font-weight:bold
```

```python
builder = SequentialBuilder().participants([
    strategy_participant,  # Strategy Agent 或 DeepResearchExecutor
    self._agents.copywriting,
    self._agents.image,
    self._agents.video,
    packaging_executor,
])
workflow = builder.with_checkpointing(checkpoint_storage).build()
```

## 配置选项

```python
@dataclass
class MarketingWorkflowConfig:
    persist_output: bool = True
    output_dir: str = "artifacts/campaigns"
    enable_image_generation: bool = False
    enable_video_generation: bool = False
    enable_deep_research: bool = False
    debug: bool = False
```

## 环境变量

```env
# 必需
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=
Tvly_API_KEY=

# 可选 - 图像生成
AZURE_IMAGE_ENDPOINT=
AZURE_IMAGE_API_KEY=

# 可选 - 视频生成
AZURE_VIDEO_ENDPOINT=
AZURE_VIDEO_API_KEY=
```

## 约束与限制

- **Sora-2 视频**: 时长只能是 4/8/12 秒，API 并发限制 2
- **FLUX 图像**: Prompt 必须英文
- **GPT-5**: 推理模型，不支持自定义 temperature
