import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import re

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI-PM 工作流", page_icon="⚡", layout="wide")

# ── 预设服务商配置 (全面涵盖市面最强模型) ─────────────────────────────────────────
PROVIDERS = {
    "DeepSeek (深度求索 - 推荐)": {
        "base_url": "https://api.deepseek.com/v1", 
        "model": "deepseek-chat"
    },
    "Claude 3.5 Sonnet (需通过 OpenRouter)": {
        "base_url": "https://openrouter.ai/api/v1", 
        "model": "anthropic/claude-3.5-sonnet"
    },
    "Gemini 1.5 Pro (Google)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", 
        "model": "gemini-1.5-pro"
    },
    "Qwen (通义千问 Max)": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", 
        "model": "qwen-max"
    },
    "Kimi (月之暗面)": {
        "base_url": "https://api.moonshot.cn/v1", 
        "model": "moonshot-v1-8k"
    },
    "OpenAI (ChatGPT 4o)": {
        "base_url": "https://api.openai.com/v1", 
        "model": "gpt-4o"
    },
    "GLM (智谱 AI)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/", 
        "model": "glm-4"
    }
}

# ── 初始化 Session State ──────────────────────────────────────────────────────
if 'stage' not in st.session_state:
    st.session_state.stage = "IDEATION"
if 'blueprint' not in st.session_state:
    st.session_state.blueprint = ""
if 'final_prd' not in st.session_state:
    st.session_state.final_prd = ""
if 'mermaid_code' not in st.session_state:
    st.session_state.mermaid_code = ""
if 'eval_report' not in st.session_state:
    st.session_state.eval_report = ""
if 'user_idea' not in st.session_state:
    st.session_state.user_idea = ""

# ── 极简美学 CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans SC', sans-serif !important;
}

.hero-title {
    font-size: 2.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.hero-sub {
    font-size: 0.9rem;
    color: #64748b;
    font-weight: 500;
    letter-spacing: 0.05em;
    margin-bottom: 2rem;
}

.stButton > button {
    background-color: #0f172a !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background-color: #334155 !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.download-btn > button {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
}
.download-btn > button:hover {
    background-color: #f1f5f9 !important;
}
</style>
""", unsafe_allow_html=True)

# ── 核心组件：Mermaid 渲染器 ──────────────────────────────────────────────────
def render_mermaid(code: str):
    """在 Streamlit 中渲染 Mermaid 图表"""
    components.html(
        f"""
        <div class="mermaid" style="display: flex; justify-content: center; margin-top: 20px;">
            {code}
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
        </script>
        """,
        height=350, scrolling=True
    )

def extract_mermaid(text: str) -> str:
    """提取大模型输出中的 Mermaid 代码块"""
    match = re.search(r'```mermaid\n(.*?)\n```', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

# ── 侧边栏：引擎配置 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 引擎配置")
    with st.container(border=True):
        provider_name = st.selectbox("大模型服务商", options=list(PROVIDERS.keys()))
        selected_provider = PROVIDERS[provider_name]
        api_key = st.text_input("API Key", type="password", placeholder="sk-...")
        base_url = st.text_input("接口地址 (Base URL)", value=selected_provider["base_url"])
        model = selected_provider["model"]
    
    if st.button("🔄 重置工作流", use_container_width=True):
        st.session_state.stage = "IDEATION"
        st.session_state.blueprint = ""
        st.session_state.final_prd = ""
        st.session_state.mermaid_code = ""
        st.session_state.eval_report = ""
        st.rerun()

# ── 顶部 Header 与进度流 ──────────────────────────────────────────────────────
st.markdown('<div class="hero-title">AI-PM 智能工作流</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Multi-Agent PRD Generator v4.0</div>', unsafe_allow_html=True)

stages = {"IDEATION": 1, "REVIEW": 2, "FINAL": 3}
current_step = stages[st.session_state.stage]

col1, col2, col3 = st.columns(3)
with col1:
    if current_step == 1: st.info("🟢 **Step 1: 需求原点**")
    else: st.markdown("✅ Step 1: 需求原点")
with col2:
    if current_step == 2: st.info("🟢 **Step 2: 架构审阅**")
    elif current_step > 2: st.markdown("✅ Step 2: 架构审阅")
    else: st.markdown("⚪ Step 2: 架构审阅")
with col3:
    if current_step == 3: st.info("🟢 **Step 3: 最终交付**")
    else: st.markdown("⚪ Step 3: 最终交付")
st.markdown("---")

def get_client():
    if not api_key: 
        st.error("⚠️ 请先在左侧侧边栏填入 API Key。")
        st.stop()
    return OpenAI(api_key=api_key, base_url=base_url)

# ── 核心工作流 ────────────────────────────────────────────────────────────────

# 【阶段 1：需求原点】
if st.session_state.stage == "IDEATION":
    with st.container(border=True):
        st.markdown("#### 💡 输入你的产品灵感")
        idea = st.text_area("描述产品痛点：", height=120, placeholder="例如：打工人经常忘记会议 To-Do，想做一个自动提取纪要的机器人...", label_visibility="collapsed")
        
        if st.button("⚡ 拆解需求架构"):
            if idea:
                st.session_state.user_idea = idea
                client = get_client()
                with st.spinner("主控 Agent 正在为你规划 PRD 骨架..."):
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": "你是一个严谨的产品总监。请将用户的想法转化为一份清晰的 PRD 骨架大纲，不写废话，只需骨架大纲。"},
                                  {"role": "user", "content": idea}]
                    )
                    st.session_state.blueprint = resp.choices[0].message.content
                    st.session_state.stage = "REVIEW"
                    st.rerun()
            else:
                st.warning("哪怕只是一句话，也要填点想法哦！")

# 【阶段 2：架构审阅】
elif st.session_state.stage == "REVIEW":
    with st.container(border=True):
        st.markdown("#### 🏗️ 架构蓝图审阅")
        st.caption("AI 已生成初步架构。请进行专业审阅并微调核心逻辑（Human-in-the-loop）：")
        edited_blueprint = st.text_area("蓝图编辑区", value=st.session_state.blueprint, height=350, label_visibility="collapsed")
        
        c1, c2, _ = st.columns([2, 2, 5])
        with c1:
            if st.button("🚀 启动 Multi-Agent 深度生成"):
                st.session_state.blueprint = edited_blueprint
                st.session_state.stage = "FINAL"
                st.rerun()
        with c2:
            if st.button("← 返回修改"):
                st.session_state.stage = "IDEATION"
                st.rerun()

# 【阶段 3：最终交付 (极速流式 + 后台 Agent 协作)】
elif st.session_state.stage == "FINAL":
    if not st.session_state.final_prd:
        client = get_client()
        
        # 1. 主 PRD 流式输出 (打字机效果) - 消除感知延迟
        st.markdown("#### 📄 产品需求文档 (PRD) - 正在实时生成中...")
        prd_container = st.container(border=True)
        prd_placeholder = prd_container.empty()
        
        base_prd = ""
        # 强约束的 System Prompt：确保 AI 绝对尊重用户的修改，不乱合并不乱删
        system_prompt = """你是腾讯/字节的高级产品经理。
        请根据用户的【原始需求】和【架构蓝图】，输出专业极简的 PRD。
        【最高指令】：你必须绝对、严格地保留【架构蓝图】中所有的原标题、编号和章节结构！绝不允许擅自合并、删除或重组用户的原有章节！
        你的任务仅仅是在用户给定的骨架下“填充血肉”（包含：业务背景、用户故事、交互说明等细节）。
        如果用户在蓝图末尾或中间加了零散的短句，请自动将其转化为一个独立的新章节并为其填充专业内容，但绝不能破坏其他已有章节的结构。"""
        
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": f"需求：{st.session_state.user_idea}\n蓝图：{st.session_state.blueprint}"}],
            stream=True 
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                base_prd += chunk.choices[0].delta.content
                prd_placeholder.markdown(base_prd + " ▌")
        prd_placeholder.markdown(base_prd)
        
        # 2. 启动后台附属 Agent 团队 (采用全平台兼容 Emoji)
        with st.status("✅ 主 PRD 已完成！附属 Agent 团队正在进行高阶扩展...", expanded=True) as status:
            
            st.write("🛡️ Agent B (资深 QA) 正在进行边界条件与异常流压测...")
            resp_b = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "你是一个严苛的QA工程师。请阅读前置PRD，补充一节完整的【异常流与边界条件分析】（网络、并发、极限值等），直接输出Markdown正文，无需客套。"},
                          {"role": "user", "content": base_prd}]
            )
            final_full_prd = base_prd + "\n\n### 异常流与边界条件分析\n" + resp_b.choices[0].message.content
            
            st.write("🎨 Agent C (架构画师) 正在生成 Mermaid 业务逻辑图...")
            resp_c = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "你是一个架构师。请根据PRD逻辑，输出一段合法的 Mermaid 流程图代码 (graph TD)。只输出代码，不要任何多余文字。"},
                          {"role": "user", "content": final_full_prd}]
            )
            st.session_state.mermaid_code = extract_mermaid(resp_c.choices[0].message.content)
            
            st.write("⚖️ Agent D (评审专家) 正在进行 MECE 闭环打分...")
            resp_d = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "你是产品总监。请从“逻辑闭环率”、“边界覆盖度”、“可执行性”三个维度给下方PRD打分（总分100），并给出简短的雷达点评（不超过100字）。"},
                          {"role": "user", "content": final_full_prd}]
            )
            
            st.session_state.final_prd = final_full_prd
            st.session_state.eval_report = resp_d.choices[0].message.content
            status.update(label="🚀 所有 Agent 协作彻底完成！", state="complete", expanded=False)
        st.rerun()
            
    # 展示渲染成果
    if st.session_state.mermaid_code:
        st.markdown("#### 🗺️ 核心业务流程图 (自动渲染)")
        with st.container(border=True):
            render_mermaid(st.session_state.mermaid_code)
            
    st.markdown("#### 📄 最终产品需求文档 (PRD)")
    with st.container(border=True):
        st.markdown(st.session_state.final_prd)
        
    st.markdown('<div class="download-btn">', unsafe_allow_html=True)
    st.download_button(
        label="📥 下载 Markdown 格式文档", 
        data=st.session_state.final_prd, 
        file_name="Multi_Agent_PRD.md",
        mime="text/markdown"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📊 LLM-as-a-Judge: AI 质量评估报告", expanded=False):
        st.markdown(st.session_state.eval_report)
