import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import re

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI-PM 工作流", page_icon="⚡", layout="wide")

# ── 服务商配置 ────────────────────────────────────────────────────────────────
PROVIDERS = {
    "DeepSeek (推荐·性价比最高)":       {"base_url": "https://api.deepseek.com/v1",                            "model": "deepseek-chat"},
    "Claude 3.5 Sonnet (OpenRouter)":   {"base_url": "https://openrouter.ai/api/v1",                          "model": "anthropic/claude-3.5-sonnet"},
    "Gemini 1.5 Pro (Google)":          {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/","model": "gemini-1.5-pro"},
    "Qwen Max (通义千问)":               {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",     "model": "qwen-max"},
    "Kimi (月之暗面)":                   {"base_url": "https://api.moonshot.cn/v1",                            "model": "moonshot-v1-8k"},
    "OpenAI GPT-4o":                    {"base_url": "https://api.openai.com/v1",                             "model": "gpt-4o"},
    "GLM-4 (智谱 AI)":                  {"base_url": "https://open.bigmodel.cn/api/paas/v4/",                 "model": "glm-4"},
}

# 产品类型 → 动态调整所有 Agent 的 System Prompt 语境
PRODUCT_TYPES = {
    "📱 To C 消费品":    "面向普通消费者的移动应用或小程序，核心关注用户留存、病毒传播和极低摩擦体验",
    "🏢 To B SaaS":      "面向企业客户的软件服务，核心关注采购决策链、ROI 可量化和实施部署成本",
    "🛠️ 内部效率工具":   "面向公司内部员工的工具，核心关注工作流集成、权限管理和降低学习成本",
    "🏛️ 平台/双边市场":  "连接供需两侧的平台，核心关注冷启动策略、网络效应和双边增长飞轮",
    "🤖 AI Native 产品": "以 AI 能力为核心卖点，核心关注模型效果评估、Prompt 工程和用户信任建立",
}

INDUSTRIES = [
    "通用", "教育 / EdTech", "医疗健康 / HealthTech", "金融 / FinTech",
    "电商 / 零售", "企业协作 / HR", "出行 / 本地生活", "游戏 / 娱乐",
    "内容 / 媒体", "政务 / 公共服务",
]

# PRD 深度 → 控制哪些 Agent 被激活
DEPTH_CONFIG = {
    "⚡ 闪电版":   {"agents": ["A", "B"],              "label": "~1 min", "desc": "主文档 + QA 异常流"},
    "📋 标准版":   {"agents": ["A", "B", "C", "D"],    "label": "~2 min", "desc": "+ 架构图 + 质量评估"},
    "🔬 深度版":   {"agents": ["A", "B", "C", "D", "E", "F"], "label": "~4 min", "desc": "+ 竞品分析 + 商业化路径"},
}

AGENT_META = {
    "A": ("📝", "主 PRD 生成",      "根据架构蓝图填充完整需求文档"),
    "B": ("🛡️", "QA 异常流分析",    "边界条件、并发冲突、降级策略"),
    "C": ("🎨", "Mermaid 架构图",   "核心业务流程可视化"),
    "D": ("⚖️", "MECE 质量评估",    "逻辑闭环率 · 边界覆盖度 · 可执行性"),
    "E": ("🔍", "竞品格局分析",     "竞品对比表 · 差异化定位一句话"),
    "F": ("💰", "商业化路径",       "商业模式 · 定价策略 · 冷启动 · 里程碑"),
}

# ── Session State 初始化 ──────────────────────────────────────────────────────
_defaults = {
    "stage": "IDEATION",
    "blueprint": "",
    "final_prd": "",
    "mermaid_code": "",
    "eval_scores": {},
    "eval_comment": "",
    "user_idea": "",
    "word_count": 0,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 全局样式 ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.stApp { background: #f5f3ef; }

[data-testid="stSidebar"] { background: #181820 !important; border-right: 1px solid #28283a !important; }
[data-testid="stSidebar"] * { color: #a8a4be !important; }
[data-testid="stSidebar"] h3 { color: #e8e4f8 !important; font-family: 'DM Serif Display', serif !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #28283a !important; color: #e8e4f8 !important;
    border: 1px solid #3a3a52 !important;
}

.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3rem; letter-spacing: -0.015em;
    color: #111018; line-height: 1.1; margin-bottom: 0.2rem;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem; color: #8884a0;
    letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 1.8rem;
}

.step-badge {
    display: inline-block; padding: 0.45rem 1.1rem;
    border-radius: 6px; font-size: 0.8rem; font-weight: 600;
    letter-spacing: 0.01em;
}
.step-active { background: #111018; color: #f5f3ef !important; }
.step-done   { background: #dcfce7; color: #166534 !important; }
.step-wait   { background: #e8e4f5; color: #8884a0 !important; }

.stButton > button {
    background: #111018 !important; color: #f5f3ef !important;
    border: none !important; border-radius: 7px !important;
    font-weight: 600 !important; font-size: 0.86rem !important;
    padding: 0.55rem 1.5rem !important; letter-spacing: 0.01em;
    transition: background 0.15s;
}
.stButton > button:hover { background: #2a2a3c !important; }

.agent-card {
    background: #ffffff; border: 1px solid #e4e0f0;
    border-radius: 10px; padding: 0.8rem 1.1rem;
    margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.75rem;
}
.agent-card.running { border-color: #7c6af7; background: #faf9ff; }
.agent-card.done    { border-color: #86efac; background: #f0fdf4; }
.agent-card.wait    { opacity: 0.4; }
.agent-icon { font-size: 1.25rem; flex-shrink: 0; }
.agent-name { font-weight: 600; font-size: 0.84rem; color: #111018; }
.agent-desc { font-size: 0.74rem; color: #8884a0; }

.score-card {
    background: #ffffff; border: 1px solid #e4e0f0;
    border-radius: 10px; padding: 1rem 0.9rem; text-align: center;
}
.score-num { font-family: 'DM Serif Display', serif; font-size: 2.6rem; color: #111018; line-height: 1; }
.score-label { font-size: 0.7rem; color: #8884a0; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.25rem; }
.score-bar-bg { height: 5px; border-radius: 3px; margin-top: 0.7rem; background: #ede8f5; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #7c6af7, #c084fc); }

.prd-box {
    background: #ffffff; border: 1px solid #e4e0f0;
    border-radius: 12px; padding: 2rem 2.5rem;
    box-shadow: 0 2px 16px rgba(0,0,0,0.03);
    font-size: 0.95rem; line-height: 1.75;
}
.stat-pill {
    display: inline-block; background: #ede8f5;
    color: #6c5fdb; border-radius: 20px;
    padding: 3px 11px; font-size: 0.71rem;
    font-family: 'JetBrains Mono', monospace;
    margin-right: 0.4rem; font-weight: 500; margin-bottom: 0.4rem;
}
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.67rem; color: #8884a0;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.6rem;
}
.config-card {
    background: #ffffff; border: 1px solid #e4e0f0;
    border-radius: 10px; padding: 1.1rem 1.3rem;
    font-size: 0.86rem;
}
</style>
""", unsafe_allow_html=True)


# ── 工具函数 ──────────────────────────────────────────────────────────────────
def render_mermaid(code: str):
    components.html(f"""
        <div class="mermaid" style="display:flex;justify-content:center;padding:1.5rem 0;">
            {code}
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{startOnLoad:true, theme:'neutral',
                themeVariables:{{fontSize:'14px', fontFamily:'DM Sans, sans-serif'}}}});
        </script>
    """, height=420, scrolling=True)

def extract_mermaid(text: str) -> str:
    m = re.search(r'```mermaid\n(.*?)\n```', text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

def parse_scores(text: str) -> dict:
    patterns = {
        "逻辑闭环率": r"逻辑闭环[率度].*?[：:]\s*(\d+)",
        "边界覆盖度": r"边界覆盖[度率].*?[：:]\s*(\d+)",
        "可执行性":   r"可执行[性度].*?[：:]\s*(\d+)",
    }
    return {label: int(m.group(1)) if (m := re.search(p, text)) else 75
            for label, p in patterns.items()}

def word_count(text: str) -> int:
    cn = len(re.findall(r'[\u4e00-\u9fff]', text))
    en = len(re.findall(r'\b[a-zA-Z]+\b', text))
    return cn + en

def reading_time(wc: int) -> str:
    return f"约 {max(1, round(wc / 400))} 分钟阅读"


# ── 动态 System Prompt 构建器 ─────────────────────────────────────────────────
def build_blueprint_prompt(pt_key, industry, agents):
    pt_desc = PRODUCT_TYPES[pt_key]
    extras = []
    if "E" in agents: extras.append("竞品对标（占位）")
    if "F" in agents: extras.append("商业化路径（占位）")
    extra_hint = f"，骨架末尾请为 {' 和 '.join(extras)} 各保留一个章节标题占位" if extras else ""
    return f"""你是一个在腾讯/字节有 8 年经验的资深技术产品总监，精通 MECE 原则和 OKR 方法论。

【产品上下文】
- 产品类型：{pt_key} — {pt_desc}
- 所属行业：{industry}

【任务】仅输出 PRD 骨架大纲（只有标题，不写正文）。
要求：
1. 结构必须 MECE（不重叠、无遗漏），章节数 7～10 个
2. 必须包含「核心用户故事」「验收标准」「数据监控指标」三个章节
3. 针对 {pt_key} 类型加入最相关的特有章节（如 To B 需含「采购决策链分析」，AI Native 需含「模型评估与 Prompt 策略」）
4. 每个标题旁标注 RICE 优先级 (H/M/L){extra_hint}

只输出 Markdown 标题大纲，禁止写任何正文内容。"""

def build_prd_prompt(pt_key, industry):
    return f"""你是一个在腾讯/字节有 8 年经验的资深技术产品总监，精通 MECE 原则、AARRR 增长模型和 OKR 方法论。

【产品上下文】
- 产品类型：{pt_key} — {PRODUCT_TYPES[pt_key]}
- 所属行业：{industry}

【写作最高准则（违反即视为失败）】
1. 严格遵守架构蓝图的每一个章节，禁止合并/删除/重组任何章节
2. 每章必须有实质内容，禁止写"待定"或空洞口号
3. 用户故事：「作为…我希望…以便于…」格式，并附 RICE 优先级评分
4. 验收标准：必须是可量化指标，如「首屏加载 ≤ 1.5s (P99)」「错误率 < 0.1%」
5. 数据监控指标按 AARRR 漏斗分层（Acquisition→Activation→Retention→Revenue→Referral）
6. 针对 {pt_key} 类型，重点阐述该类产品最关键的 1～2 个差异化章节

直接输出专业 Markdown PRD 正文，不要任何开场白。"""

def build_qa_prompt():
    return """你是一个有 10 年经验的资深 QA 工程师，专注于系统边界测试和异常流分析。

请补充一节完整的【异常流与边界条件分析】，必须涵盖：
- 网络异常（弱网/断网/超时）及对应降级策略
- 并发冲突（多端同时操作、重复提交、幂等性）
- 数据边界（空输入/超长输入/特殊字符/SQL 注入/XSS 风险）
- AI 专项（若产品含 AI）：模型响应慢、Hallucination、内容安全过滤触发的降级方案

输出格式：Markdown 正文，每类异常用小标题区分。直接输出，无前言。"""

def build_competitive_prompt(pt_key, industry, idea):
    return f"""你是专注于 {industry} 行业的战略分析师，熟悉主流竞品格局。

产品背景：{pt_key} · {idea}

请输出一节【竞品格局与差异化定位】，必须包含：
1. 列出 3～5 个直接或间接竞品，从「核心功能/目标用户/商业模式/核心优劣势」4 维度对比（Markdown 表格）
2. 竞争空白点：哪些痛点目前未被充分满足？
3. 差异化定位一句话（电梯演讲）：「对于…的…，我们提供…，不同于…，我们的核心优势是…」

数据允许合理估算，需注明「参考数据」。直接输出正文，无前言。"""

def build_monetization_prompt(pt_key, industry):
    return f"""你是精通商业模式设计的产品增长专家，专注 {industry} 行业 {pt_key} 赛道。

请根据 PRD 产品定义，输出一节【商业化路径与增长策略】，包含：
1. 推荐主要商业模式（订阅/抽佣/广告/增值服务等，说明选择理由）
2. 定价策略建议（Free tier 边界？Pro 版门槛？付费转化路径）
3. 冷启动策略（前 1000 个用户从哪来？用什么钩子拉新和留存？）
4. 12 个月里程碑（M1/M3/M6/M12 各阶段的核心目标与北极星指标）
5. 核心增长飞轮（文字描述飞轮各环节）

直接输出 Markdown 正文，无前言。"""

def build_arch_prompt():
    return """你是一个系统架构师。根据 PRD 核心业务逻辑，输出一段合法的 Mermaid 流程图（graph TD）。
要求：节点用中文，清晰展示核心用户操作路径和系统响应，至少包含一个判断分支和一个错误处理分支。
只输出代码块（```mermaid ... ```），不要任何其他文字。"""

def build_eval_prompt():
    return """你是产品总监，正在进行 MECE 闭环审查。请严格按以下模板输出，不要改变格式：

逻辑闭环率：XX分 — [一句话点评]
边界覆盖度：XX分 — [一句话点评]
可执行性：XX分 — [一句话点评]

总评：[2～3句话，指出最大亮点和最需改进的一个点]"""


# ── 侧边栏 ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ 引擎配置")
    st.divider()

    provider_name = st.selectbox("大模型服务商", list(PROVIDERS.keys()))
    sel = PROVIDERS[provider_name]
    api_key  = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("Base URL", value=sel["base_url"])
    model    = sel["model"]
    st.caption(f"当前模型：`{model}`")

    st.divider()
    st.markdown("### 🎛️ PRD 配置")

    product_type_key = st.selectbox("产品类型", list(PRODUCT_TYPES.keys()))
    industry         = st.selectbox("所属行业", INDUSTRIES)
    depth_key        = st.radio("生成深度", list(DEPTH_CONFIG.keys()), index=1)
    depth_cfg        = DEPTH_CONFIG[depth_key]
    st.caption(f"预计耗时 {depth_cfg['label']} · {depth_cfg['desc']}")

    st.divider()
    with st.expander("📥 导入已有骨架（跳过 Stage 1）"):
        imported = st.text_area("粘贴骨架 Markdown", height=110,
                                label_visibility="collapsed", placeholder="粘贴已有 PRD 大纲...")
        if st.button("导入并进入审阅", use_container_width=True):
            if imported.strip():
                st.session_state.blueprint = imported.strip()
                st.session_state.stage = "REVIEW"
                st.rerun()

    if st.button("🔄 重置工作流", use_container_width=True):
        for k, v in _defaults.items():
            st.session_state[k] = v
        st.rerun()


# ── 客户端工厂 ────────────────────────────────────────────────────────────────
def get_client():
    if not api_key:
        st.error("⚠️ 请先在侧边栏填入 API Key。")
        st.stop()
    return OpenAI(api_key=api_key.strip(), base_url=base_url.strip())

def call_llm(client, system, user, stream=False):
    try:
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            stream=stream,
        )
    except Exception as e:
        err = str(e)
        if "401" in err or "auth" in err.lower():
            st.error("🔐 API Key 验证失败，请检查 Key 和 Base URL 是否匹配。")
        elif "404" in err or "model" in err.lower():
            st.error(f"🤖 模型 `{model}` 不可用，请换一个试试。")
        elif "connect" in err.lower() or "timeout" in err.lower():
            st.error("🌐 网络连接失败，请检查 Base URL 是否可访问。")
        else:
            st.error(f"❌ 请求失败：\n```\n{err}\n```")
        st.stop()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">AI-PM 智能工作流</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Multi-Agent PRD Generator v5.0 · Human-in-the-Loop</div>', unsafe_allow_html=True)

# 进度步骤
stages_map = {"IDEATION": 1, "REVIEW": 2, "FINAL": 3}
cur = stages_map[st.session_state.stage]
sc1, sc2, sc3 = st.columns(3)
for col, i, label in zip([sc1, sc2, sc3], [1, 2, 3],
                          ["Step 1 · 需求原点", "Step 2 · 架构审阅", "Step 3 · 最终交付"]):
    with col:
        cls = "step-active" if cur == i else ("step-done" if cur > i else "step-wait")
        icon = "🟢 " if cur == i else ("✅ " if cur > i else "⚪ ")
        st.markdown(f'<div class="step-badge {cls}">{icon}{label}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 【阶段 1：需求原点】
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == "IDEATION":
    left, right = st.columns([3, 2], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<p class="section-label">💡 输入产品灵感</p>', unsafe_allow_html=True)
            idea = st.text_area(
                label="idea", height=140, label_visibility="collapsed",
                placeholder="例如：打工人经常忘记会议 Action Item，想做一个自动提取纪要并推送到飞书的 AI 机器人...",
            )

            st.caption("⚡ 快速示例（点击填入）：")
            examples = [
                "帮大学生改简历的 AI 小程序",
                "AI 驱动的 B2B 合同审核 SaaS",
                "连接独立咨询师与中小企业的双边平台",
            ]
            ex_cols = st.columns(3)
            for col, ex in zip(ex_cols, examples):
                with col:
                    if st.button(ex, key=f"ex_{ex}", use_container_width=True):
                        st.session_state._prefill = ex
                        st.rerun()

            if "_prefill" in st.session_state:
                idea = st.session_state.pop("_prefill")

            if st.button("⚡ 拆解需求架构 →", use_container_width=True):
                if not idea or not idea.strip():
                    st.warning("哪怕只是一句话，也要填点想法哦！")
                else:
                    st.session_state.user_idea = idea.strip()
                    client = get_client()
                    with st.spinner("主控 Agent 正在规划 PRD 骨架..."):
                        resp = call_llm(client,
                                        build_blueprint_prompt(product_type_key, industry, depth_cfg["agents"]),
                                        idea.strip())
                        st.session_state.blueprint = resp.choices[0].message.content
                        st.session_state.stage = "REVIEW"
                        st.rerun()

    with right:
        st.markdown('<p class="section-label">🎯 当前配置预览</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="config-card">'
                    f'<b>产品类型</b> {product_type_key}<br>'
                    f'<small style="color:#8884a0">{PRODUCT_TYPES[product_type_key]}</small><br><br>'
                    f'<b>行业</b> {industry}<br><br>'
                    f'<b>生成深度</b> {depth_key}<br>'
                    f'<small style="color:#8884a0">预计 {depth_cfg["label"]} · {depth_cfg["desc"]}</small>'
                    f'</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-label">🤖 将激活的 Agent</p>', unsafe_allow_html=True)
        for ag_id, (icon, name, desc) in AGENT_META.items():
            active = ag_id in depth_cfg["agents"]
            check = "✅" if active else "⬜"
            opacity = "1" if active else "0.35"
            st.markdown(
                f'<div style="opacity:{opacity};font-size:0.82rem;padding:0.25rem 0;">'
                f'{check} <b>{icon} Agent {ag_id}</b> — {name}</div>',
                unsafe_allow_html=True
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 【阶段 2：架构审阅（Human-in-the-Loop）】
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "REVIEW":
    st.info("💡 **Human-in-the-Loop**：下方是 AI 生成的骨架大纲，你的每一行修改都会被后续所有 Agent 严格遵守。可直接增删章节、调整优先级，然后启动深度生成。")

    with st.container(border=True):
        st.markdown('<p class="section-label">🏗️ PRD 架构蓝图（可直接编辑）</p>', unsafe_allow_html=True)
        edited = st.text_area("蓝图", value=st.session_state.blueprint,
                              height=400, label_visibility="collapsed")

    c1, c2, c3, _ = st.columns([2.5, 1.8, 1.8, 4])
    with c1:
        if st.button("🚀 启动 Multi-Agent 深度生成", use_container_width=True):
            st.session_state.blueprint = edited
            st.session_state.stage = "FINAL"
            st.rerun()
    with c2:
        if st.button("🔁 重新生成骨架", use_container_width=True):
            client = get_client()
            with st.spinner("重新规划骨架中..."):
                resp = call_llm(client,
                                build_blueprint_prompt(product_type_key, industry, depth_cfg["agents"]),
                                st.session_state.user_idea)
                st.session_state.blueprint = resp.choices[0].message.content
                st.rerun()
    with c3:
        if st.button("← 返回修改想法", use_container_width=True):
            st.session_state.stage = "IDEATION"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 【阶段 3：最终交付（Multi-Agent 协作）】
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "FINAL":
    agents_to_run = depth_cfg["agents"]

    # ── 首次执行（尚未缓存）──────────────────────────────────────────────────
    if not st.session_state.final_prd:
        client = get_client()

        # Agent 状态卡面板
        st.markdown('<p class="section-label">🤖 Multi-Agent 协作进行中</p>', unsafe_allow_html=True)
        ph_map = {}
        for ag_id, (icon, name, desc) in AGENT_META.items():
            if ag_id in agents_to_run:
                ph = st.empty()
                ph.markdown(
                    f'<div class="agent-card wait"><span class="agent-icon">{icon}</span>'
                    f'<div><div class="agent-name">Agent {ag_id}：{name}</div>'
                    f'<div class="agent-desc">{desc}</div></div></div>',
                    unsafe_allow_html=True
                )
                ph_map[ag_id] = ph

        def set_agent_state(ag_id, state):
            if ag_id not in ph_map: return
            icon, name, desc = AGENT_META[ag_id][0], AGENT_META[ag_id][1], AGENT_META[ag_id][2]
            suffix = " ⏳" if state == "running" else (" ✅" if state == "done" else "")
            cls = {"running": "running", "done": "done"}.get(state, "wait")
            ph_map[ag_id].markdown(
                f'<div class="agent-card {cls}"><span class="agent-icon">{icon}</span>'
                f'<div><div class="agent-name">Agent {ag_id}：{name}{suffix}</div>'
                f'<div class="agent-desc">{desc}</div></div></div>',
                unsafe_allow_html=True
            )

        # ── Agent A：流式主 PRD ──────────────────────────────────────────────
        set_agent_state("A", "running")
        st.markdown('<p class="section-label" style="margin-top:1rem">📄 PRD 实时生成中...</p>',
                    unsafe_allow_html=True)
        prd_ph = st.empty()
        base_prd = ""
        stream = call_llm(
            client,
            build_prd_prompt(product_type_key, industry),
            f"原始需求：{st.session_state.user_idea}\n\n架构蓝图（必须严格遵守）：\n{st.session_state.blueprint}",
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                base_prd += delta.content
                prd_ph.markdown(f'<div class="prd-box">{base_prd} ▌</div>', unsafe_allow_html=True)
        prd_ph.empty()
        set_agent_state("A", "done")
        final_prd = base_prd

        # ── Agent B：QA 异常流 ────────────────────────────────────────────────
        if "B" in agents_to_run:
            set_agent_state("B", "running")
            resp = call_llm(client, build_qa_prompt(), final_prd)
            final_prd += "\n\n---\n### 🛡️ 异常流与边界条件分析\n" + resp.choices[0].message.content
            set_agent_state("B", "done")

        # ── Agent E：竞品分析 ─────────────────────────────────────────────────
        if "E" in agents_to_run:
            set_agent_state("E", "running")
            resp = call_llm(client,
                            build_competitive_prompt(product_type_key, industry, st.session_state.user_idea),
                            final_prd)
            final_prd += "\n\n---\n### 🔍 竞品格局与差异化定位\n" + resp.choices[0].message.content
            set_agent_state("E", "done")

        # ── Agent F：商业化路径 ───────────────────────────────────────────────
        if "F" in agents_to_run:
            set_agent_state("F", "running")
            resp = call_llm(client, build_monetization_prompt(product_type_key, industry), final_prd)
            final_prd += "\n\n---\n### 💰 商业化路径与增长策略\n" + resp.choices[0].message.content
            set_agent_state("F", "done")

        # ── Agent C：Mermaid 架构图 ───────────────────────────────────────────
        if "C" in agents_to_run:
            set_agent_state("C", "running")
            resp = call_llm(client, build_arch_prompt(), final_prd)
            st.session_state.mermaid_code = extract_mermaid(resp.choices[0].message.content)
            set_agent_state("C", "done")

        # ── Agent D：质量评估 ─────────────────────────────────────────────────
        if "D" in agents_to_run:
            set_agent_state("D", "running")
            resp = call_llm(client, build_eval_prompt(), final_prd)
            eval_text = resp.choices[0].message.content
            st.session_state.eval_scores  = parse_scores(eval_text)
            st.session_state.eval_comment = eval_text
            set_agent_state("D", "done")

        st.session_state.final_prd  = final_prd
        st.session_state.word_count = word_count(final_prd)
        st.rerun()

    # ── 展示最终成果 ──────────────────────────────────────────────────────────

    # 顶部操作栏
    a1, a2, a3, _ = st.columns([2.2, 1.8, 1.8, 3])
    with a1:
        st.download_button("📥 下载 PRD (Markdown)", data=st.session_state.final_prd,
                           file_name="Multi_Agent_PRD.md", mime="text/markdown", use_container_width=True)
    with a2:
        if st.button("🔁 重新生成", use_container_width=True):
            for k in ["final_prd", "mermaid_code", "eval_scores", "eval_comment"]:
                st.session_state[k] = {} if k == "eval_scores" else ""
            st.rerun()
    with a3:
        if st.button("✏️ 返回调整骨架", use_container_width=True):
            st.session_state.stage = "REVIEW"
            st.session_state.final_prd = ""
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 统计徽章
    wc = st.session_state.word_count
    st.markdown(
        f'<span class="stat-pill">📄 {wc:,} 字</span>'
        f'<span class="stat-pill">⏱️ {reading_time(wc)}</span>'
        f'<span class="stat-pill">🤖 {len(depth_cfg["agents"])} Agent</span>'
        f'<span class="stat-pill">{product_type_key}</span>'
        f'<span class="stat-pill">🏭 {industry}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 评估分数卡 ────────────────────────────────────────────────────────────
    if st.session_state.eval_scores:
        st.markdown('<p class="section-label">⚖️ LLM-as-a-Judge · MECE 质量评估</p>',
                    unsafe_allow_html=True)
        score_items = list(st.session_state.eval_scores.items())
        avg_score = round(sum(v for _, v in score_items) / len(score_items))
        sc1, sc2, sc3, sc4 = st.columns([1, 1, 1, 2])
        for col, (label, score) in zip([sc1, sc2, sc3], score_items):
            with col:
                st.markdown(
                    f'<div class="score-card">'
                    f'<div class="score-num">{score}</div>'
                    f'<div class="score-label">{label}</div>'
                    f'<div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%"></div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with sc4:
            with st.container(border=True):
                st.markdown(f"**综合评分：{avg_score} / 100**")
                # 提取总评（去掉三行打分行）
                comment_lines = [
                    l for l in st.session_state.eval_comment.strip().split("\n")
                    if l.strip() and not any(k in l for k in ["逻辑闭环", "边界覆盖", "可执行性"])
                ]
                st.caption("\n".join(comment_lines[:5]))
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Mermaid 图 ────────────────────────────────────────────────────────────
    if st.session_state.mermaid_code:
        st.markdown('<p class="section-label">🗺️ 核心业务流程图（自动渲染）</p>', unsafe_allow_html=True)
        with st.container(border=True):
            render_mermaid(st.session_state.mermaid_code)
        with st.expander("🔍 查看 Mermaid 源码"):
            st.code(st.session_state.mermaid_code, language="text")
        st.markdown("<br>", unsafe_allow_html=True)

    # ── 主 PRD 文档 ───────────────────────────────────────────────────────────
    st.markdown('<p class="section-label">📄 产品需求文档（PRD）</p>', unsafe_allow_html=True)

    with st.container(border=True):
        # 单节重新生成（高级）
        with st.expander("🔧 单节重新生成（高级）"):
            st.caption("指定章节关键词，AI 将在不改动其他章节的前提下单独重写该节，写完后自动替换。")
            col_input, col_btn = st.columns([3, 1])
            with col_input:
                section_kw = st.text_input("章节关键词", placeholder="例如：验收标准",
                                           label_visibility="collapsed")
            with col_btn:
                regen_btn = st.button("重写该节")
            if regen_btn and section_kw.strip():
                client = get_client()
                with st.spinner(f"正在重新生成「{section_kw}」节..."):
                    resp = call_llm(
                        client,
                        f"你是资深产品经理。请仅重新撰写 PRD 中的【{section_kw}】这一节，内容更专业详实，"
                        f"保持与整体文档风格一致。直接输出该节 Markdown 正文（不含章节标题）。",
                        f"完整 PRD 上下文：\n{st.session_state.final_prd}",
                    )
                    new_content = resp.choices[0].message.content
                    updated = re.sub(
                        rf'(##+ [^\n]*{re.escape(section_kw)}[^\n]*\n)(.*?)(\n##+ |\Z)',
                        lambda m: m.group(1) + new_content + "\n" + m.group(3),
                        st.session_state.final_prd,
                        flags=re.DOTALL,
                    )
                    if updated != st.session_state.final_prd:
                        st.session_state.final_prd = updated
                        st.success(f"「{section_kw}」节已重新生成！")
                        st.rerun()
                    else:
                        st.warning(f"未找到包含「{section_kw}」的章节，请检查关键词。")

        st.markdown(st.session_state.final_prd)
