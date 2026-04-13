import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import re

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI-PM 工作流", page_icon="⚡", layout="wide")

# ── 服务商配置 ────────────────────────────────────────────────────────────────
PROVIDERS = {
    "DeepSeek (推荐)":       {"base_url": "https://api.deepseek.com/v1",                             "model": "deepseek-chat"},
    "Claude 3.5 Sonnet (OpenRouter)":   {"base_url": "https://openrouter.ai/api/v1",                           "model": "anthropic/claude-3.5-sonnet"},
    "Gemini 1.5 Pro (Google)":          {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/","model": "gemini-1.5-pro"},
    "Qwen Max (通义千问)":               {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",      "model": "qwen-max"},
    "Kimi (月之暗面)":                   {"base_url": "https://api.moonshot.cn/v1",                             "model": "moonshot-v1-8k"},
    "OpenAI GPT-5.3":                    {"base_url": "https://api.openai.com/v1",                              "model": "gpt-5.3"},
    "GLM-4 (智谱 AI)":                  {"base_url": "https://open.bigmodel.cn/api/paas/v4/",                  "model": "glm-4"},
}

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

DEPTH_CONFIG = {
    "⚡ 闪电版":  {"agents": ["A", "B"],                    "label": "~1 min", "desc": "主文档 + QA 异常流"},
    "📋 标准版":  {"agents": ["A", "B", "C", "D"],          "label": "~2 min", "desc": "+ 架构图 + 质量评估"},
    "🔬 深度版":  {"agents": ["A", "B", "C", "D", "E", "F"],"label": "~4 min", "desc": "+ 竞品分析 + 商业化路径"},
}

AGENT_META = {
    "A": ("📝", "主 PRD 生成",    "根据架构蓝图填充完整需求文档"),
    "B": ("🛡️", "QA 异常流分析", "边界条件、并发冲突、降级策略"),
    "C": ("🎨", "Mermaid 架构图", "核心业务流程可视化"),
    "D": ("⚖️", "MECE 质量评估", "逻辑闭环率 · 边界覆盖度 · 可执行性"),
    "E": ("🔍", "竞品格局分析",  "竞品对比表 · 差异化定位一句话"),
    "F": ("💰", "商业化路径",    "商业模式 · 定价策略 · 冷启动 · 里程碑"),
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

# ── 工具函数 ──────────────────────────────────────────────────────────────────
def render_mermaid(code: str):
    components.html(f"""
        <div class="mermaid" style="display:flex;justify-content:center;padding:1rem 0;">
            {code}
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{startOnLoad:true,theme:'neutral'}});
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
    return len(re.findall(r'[\u4e00-\u9fff]', text)) + len(re.findall(r'\b[a-zA-Z]+\b', text))

def reading_time(wc: int) -> str:
    return f"约 {max(1, round(wc / 400))} 分钟阅读"

# ── System Prompt 构建器 ──────────────────────────────────────────────────────
def build_blueprint_prompt(pt_key, industry, agents):
    pt_desc = PRODUCT_TYPES[pt_key]
    extras = []
    if "E" in agents: extras.append("竞品对标（占位）")
    if "F" in agents: extras.append("商业化路径（占位）")
    extra_hint = f"，骨架末尾请为 {' 和 '.join(extras)} 各保留一个章节标题占位" if extras else ""
    return f"""你是在腾讯/字节有 8 年经验的资深技术产品总监，精通 MECE 原则和 OKR 方法论。

【产品上下文】
- 产品类型：{pt_key} — {pt_desc}
- 所属行业：{industry}

【任务】仅输出 PRD 骨架大纲（只有标题，不写正文）。
要求：
1. 结构必须 MECE，章节数 7～10 个
2. 必须包含「核心用户故事」「验收标准」「数据监控指标」三个章节
3. 针对 {pt_key} 类型加入最相关的特有章节
4. 每个标题旁标注 RICE 优先级 (H/M/L){extra_hint}

只输出 Markdown 标题大纲，禁止写任何正文内容。"""

def build_prd_prompt(pt_key, industry):
    return f"""你是在腾讯/字节有 8 年经验的资深技术产品总监，精通 MECE 原则、AARRR 增长模型和 OKR 方法论。

【产品上下文】
- 产品类型：{pt_key} — {PRODUCT_TYPES[pt_key]}
- 所属行业：{industry}

【写作最高准则】
1. 严格遵守架构蓝图的每一个章节，禁止合并/删除/重组任何章节
2. 每章必须有实质内容，禁止写"待定"或空洞口号
3. 用户故事：「作为…我希望…以便于…」格式，附 RICE 优先级评分
4. 验收标准：必须是可量化指标，如「首屏加载 ≤ 1.5s (P99)」
5. 数据监控指标按 AARRR 漏斗分层
6. 针对 {pt_key} 类型，重点阐述该类产品最关键的差异化章节

直接输出专业 Markdown PRD 正文，不要任何开场白。"""

def build_qa_prompt():
    return """你是有 10 年经验的资深 QA 工程师，专注于系统边界测试和异常流分析。
请补充一节完整的【异常流与边界条件分析】，涵盖：
- 网络异常（弱网/断网/超时）及降级策略
- 并发冲突（多端同时操作、重复提交、幂等性）
- 数据边界（空输入/超长输入/特殊字符/XSS 风险）
- AI 专项（若适用）：模型响应慢、Hallucination、内容安全过滤触发的降级方案
直接输出 Markdown 正文，无前言。"""

def build_competitive_prompt(pt_key, industry, idea):
    return f"""你是专注于 {industry} 行业的战略分析师。
产品背景：{pt_key} · {idea}
请输出一节【竞品格局与差异化定位】，包含：
1. 3～5 个竞品的 4 维对比表（核心功能/目标用户/商业模式/核心优劣势）
2. 竞争空白点分析
3. 差异化定位一句话（电梯演讲格式）
直接输出 Markdown 正文，无前言。"""

def build_monetization_prompt(pt_key, industry):
    return f"""你是精通商业模式设计的产品增长专家，专注 {industry} 行业 {pt_key} 赛道。
请输出一节【商业化路径与增长策略】，包含：
1. 推荐主要商业模式及选择理由
2. 定价策略建议（Free tier 边界、Pro 版门槛）
3. 冷启动策略（前 1000 个用户从哪来）
4. 12 个月里程碑（M1/M3/M6/M12）
5. 核心增长飞轮
直接输出 Markdown 正文，无前言。"""

def build_arch_prompt():
    return """你是系统架构师。根据 PRD 核心业务逻辑，输出合法的 Mermaid 流程图（graph TD）。
节点用中文，展示核心用户操作路径和系统响应，包含至少一个判断分支和错误处理分支。
只输出代码块（```mermaid ... ```），不要其他文字。"""

def build_eval_prompt():
    return """你是产品总监，正在进行 MECE 闭环审查。严格按以下模板输出：

逻辑闭环率：XX分 — [一句话点评]
边界覆盖度：XX分 — [一句话点评]
可执行性：XX分 — [一句话点评]

总评：[2～3句话，指出最大亮点和最需改进的一个点]"""

# ── 侧边栏 ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 配置")

    st.subheader("引擎")
    provider_name = st.selectbox("大模型服务商", list(PROVIDERS.keys()), label_visibility="collapsed")
    sel      = PROVIDERS[provider_name]
    api_key  = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("Base URL", value=sel["base_url"])
    model    = sel["model"]
    st.caption(f"当前模型：`{model}`")

    st.divider()

    st.subheader("PRD 配置")
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

# ── Header + 进度步骤 ─────────────────────────────────────────────────────────
st.title("⚡ AI-PM 智能工作流")
st.caption("Multi-Agent PRD Generator v5.0 · Human-in-the-Loop")

stages_map = {"IDEATION": 1, "REVIEW": 2, "FINAL": 3}
cur = stages_map[st.session_state.stage]
sc1, sc2, sc3 = st.columns(3)
for col, i, label in zip([sc1, sc2, sc3], [1, 2, 3],
                          ["Step 1 · 需求原点", "Step 2 · 架构审阅", "Step 3 · 最终交付"]):
    with col:
        if cur == i:
            st.info(f"🟢 **{label}**")
        elif cur > i:
            st.success(f"✅ {label}")
        else:
            st.markdown(f"⚪ {label}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# 【阶段 1：需求原点】
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == "IDEATION":
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.subheader("💡 输入产品灵感")
        idea = st.text_area(
            "描述你的产品想法", height=150,
            placeholder="例如：打工人经常忘记会议 Action Item，想做一个自动提取会议纪要并推送到飞书的 AI 机器人...",
        )

        st.caption("⚡ 快速示例（点击填入）")
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

        if st.button("⚡ 拆解需求架构 →", type="primary", use_container_width=True):
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
        st.subheader("🎯 当前配置")
        st.write(f"**产品类型：** {product_type_key}")
        st.caption(PRODUCT_TYPES[product_type_key])
        st.write(f"**行业：** {industry}")
        st.write(f"**生成深度：** {depth_key}")
        st.caption(f"预计 {depth_cfg['label']} · {depth_cfg['desc']}")
        st.divider()
        st.caption("将激活的 Agent：")
        for ag_id, (icon, name, desc) in AGENT_META.items():
            active = ag_id in depth_cfg["agents"]
            check = "✅" if active else "⬜"
            st.caption(f"{check} **{icon} Agent {ag_id}** — {name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 【阶段 2：架构审阅（Human-in-the-Loop）】
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.stage == "REVIEW":
    st.subheader("🏗️ PRD 架构蓝图审阅")
    st.info("💡 **Human-in-the-Loop**：下方是 AI 生成的骨架大纲，你的每一行修改都会被后续所有 Agent 严格遵守。可直接增删章节、调整优先级，然后启动深度生成。")

    edited = st.text_area("蓝图编辑区", value=st.session_state.blueprint, height=420)

    c1, c2, c3, _ = st.columns([2.5, 1.8, 1.8, 4])
    with c1:
        if st.button("🚀 启动 Multi-Agent 深度生成", type="primary", use_container_width=True):
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

    # ── 首次执行 ─────────────────────────────────────────────────────────────
    if not st.session_state.final_prd:
        client = get_client()

        st.subheader("🤖 Multi-Agent 协作进行中")
        ph_map = {}
        for ag_id, (icon, name, desc) in AGENT_META.items():
            if ag_id in agents_to_run:
                ph_map[ag_id] = st.empty()
                ph_map[ag_id].markdown(f"⬜ **Agent {ag_id} {icon} {name}** — {desc}")

        def set_agent(ag_id, state):
            if ag_id not in ph_map: return
            icon, name, desc = AGENT_META[ag_id]
            prefix = {"running": "⏳", "done": "✅"}.get(state, "⬜")
            ph_map[ag_id].markdown(f"{prefix} **Agent {ag_id} {icon} {name}** — {desc}")

        # Agent A：流式主 PRD
        set_agent("A", "running")
        st.subheader("📄 PRD 实时生成中...")
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
                prd_ph.markdown(base_prd + " ▌")
        prd_ph.empty()
        set_agent("A", "done")
        final_prd = base_prd

        # Agent B：QA 异常流
        if "B" in agents_to_run:
            set_agent("B", "running")
            resp = call_llm(client, build_qa_prompt(), final_prd)
            final_prd += "\n\n---\n### 🛡️ 异常流与边界条件分析\n" + resp.choices[0].message.content
            set_agent("B", "done")

        # Agent E：竞品分析
        if "E" in agents_to_run:
            set_agent("E", "running")
            resp = call_llm(client,
                            build_competitive_prompt(product_type_key, industry, st.session_state.user_idea),
                            final_prd)
            final_prd += "\n\n---\n### 🔍 竞品格局与差异化定位\n" + resp.choices[0].message.content
            set_agent("E", "done")

        # Agent F：商业化路径
        if "F" in agents_to_run:
            set_agent("F", "running")
            resp = call_llm(client, build_monetization_prompt(product_type_key, industry), final_prd)
            final_prd += "\n\n---\n### 💰 商业化路径与增长策略\n" + resp.choices[0].message.content
            set_agent("F", "done")

        # Agent C：Mermaid 架构图
        if "C" in agents_to_run:
            set_agent("C", "running")
            resp = call_llm(client, build_arch_prompt(), final_prd)
            st.session_state.mermaid_code = extract_mermaid(resp.choices[0].message.content)
            set_agent("C", "done")

        # Agent D：质量评估
        if "D" in agents_to_run:
            set_agent("D", "running")
            resp = call_llm(client, build_eval_prompt(), final_prd)
            eval_text = resp.choices[0].message.content
            st.session_state.eval_scores  = parse_scores(eval_text)
            st.session_state.eval_comment = eval_text
            set_agent("D", "done")

        st.session_state.final_prd  = final_prd
        st.session_state.word_count = word_count(final_prd)
        st.rerun()

    # ── 展示成果 ──────────────────────────────────────────────────────────────

    # 操作栏
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

    # 统计
    wc = st.session_state.word_count
    st.caption(
        f"📄 {wc:,} 字　·　⏱️ {reading_time(wc)}　·　"
        f"🤖 {len(depth_cfg['agents'])} Agent　·　{product_type_key}　·　{industry}"
    )
    st.divider()

    # 评估分数
    if st.session_state.eval_scores:
        st.subheader("⚖️ LLM-as-a-Judge · 质量评估")
        score_items = list(st.session_state.eval_scores.items())
        avg_score = round(sum(v for _, v in score_items) / len(score_items))
        sc1, sc2, sc3, sc4 = st.columns([1, 1, 1, 2])
        for col, (label, score) in zip([sc1, sc2, sc3], score_items):
            with col:
                st.metric(label=label, value=f"{score} / 100")
        with sc4:
            st.metric(label="综合评分", value=f"{avg_score} / 100")
            comment_lines = [
                l for l in st.session_state.eval_comment.strip().split("\n")
                if l.strip() and not any(k in l for k in ["逻辑闭环", "边界覆盖", "可执行性"])
            ]
            st.caption("\n".join(comment_lines[:4]))
        st.divider()

    # Mermaid 图
    if st.session_state.mermaid_code:
        st.subheader("🗺️ 核心业务流程图")
        render_mermaid(st.session_state.mermaid_code)
        with st.expander("查看 Mermaid 源码"):
            st.code(st.session_state.mermaid_code, language="text")
        st.divider()

    # 主 PRD 文档
    st.subheader("📄 产品需求文档（PRD）")

    with st.expander("🔧 单节重新生成（高级）"):
        st.caption("输入章节关键词，AI 将精准替换该节内容，其他章节完全不动。")
        col_in, col_btn = st.columns([3, 1])
        with col_in:
            section_kw = st.text_input("章节关键词", placeholder="例如：验收标准",
                                       label_visibility="collapsed")
        with col_btn:
            if st.button("重写该节", type="primary"):
                if section_kw.strip():
                    client = get_client()
                    with st.spinner(f"正在重新生成「{section_kw}」节..."):
                        resp = call_llm(
                            client,
                            f"你是资深产品经理。请仅重新撰写 PRD 中的【{section_kw}】这一节，"
                            f"内容更专业详实，保持与整体文档风格一致。直接输出该节 Markdown 正文（不含章节标题）。",
                            f"完整 PRD 上下文：\n{st.session_state.final_prd}",
                        )
                        new_content = resp.choices[0].message.content
                        updated = re.sub(
                            rf'(##+ [^\n]*{re.escape(section_kw)}[^\n]*\n)(.*?)(\n##+ |\Z)',
                            lambda m: m.group(1) + new_content + "\n" + m.group(3),
                            st.session_state.final_prd, flags=re.DOTALL,
                        )
                        if updated != st.session_state.final_prd:
                            st.session_state.final_prd = updated
                            st.success(f"「{section_kw}」节已重新生成！")
                            st.rerun()
                        else:
                            st.warning("未找到该章节，请检查关键词。")

    st.markdown(st.session_state.final_prd)
