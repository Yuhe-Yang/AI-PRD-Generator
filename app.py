import streamlit as st
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI-PM Agent", page_icon="⚡", layout="wide")

# ── 预设服务商配置 ────────────────────────────────────────────────────────────
PROVIDERS = {
    "DeepSeek (推荐)": {"base_url": "https://api.deepseek.com/v1", "models": ["deepseek-chat"]},
    "Kimi (Moonshot)": {"base_url": "https://api.moonshot.cn/v1", "models": ["moonshot-v1-8k", "moonshot-v1-32k"]},
    "OpenAI (Global)": {"base_url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini"]},
    "智谱 AI (GLM)": {"base_url": "https://open.bigmodel.cn/api/paas/v4/", "models": ["glm-4"]}
}

# ── 初始化 Session State ──────────────────────────────────────────────────────
if 'stage' not in st.session_state:
    st.session_state.stage = "IDEATION" # 阶段分为: IDEATION, REVIEW, FINAL
if 'blueprint' not in st.session_state:
    st.session_state.blueprint = ""
if 'final_prd' not in st.session_state:
    st.session_state.final_prd = ""
if 'user_idea' not in st.session_state:
    st.session_state.user_idea = ""

# ── 极简美学 CSS (Vercel/Linear 风格，完美适配亮/暗模式) ──────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

/* 全局字体：硅谷标配 Inter + 思源黑体 */
html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans SC', sans-serif !important;
}

/* 主标题极致清爽 */
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
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* 按钮极简化：纯色、微圆角、无渐变 */
.stButton > button {
    background-color: #0f172a !important; /* 深夜蓝/黑 */
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

/* 下载按钮特殊处理 */
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

# ── 侧边栏：引擎配置 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    
    with st.container(border=True):
        provider_name = st.selectbox("LLM Provider", options=list(PROVIDERS.keys()))
        selected_provider = PROVIDERS[provider_name]
        
        api_key = st.text_input("API Key", type="password", placeholder="sk-...")
        base_url = st.text_input("Base URL", value=selected_provider["base_url"])
        model = st.selectbox("Model", options=selected_provider["models"])
    
    if st.button("🔄 Reset Workflow", use_container_width=True):
        st.session_state.stage = "IDEATION"
        st.session_state.blueprint = ""
        st.session_state.final_prd = ""
        st.rerun()

# ── 顶部 Header 与进度流 ──────────────────────────────────────────────────────
st.markdown('<div class="hero-title">AI-PM Workflow</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Human-in-the-loop PRD Generator</div>', unsafe_allow_html=True)

# 动态进度条 (已修复 Bug 的版本)
stages = {"IDEATION": 1, "REVIEW": 2, "FINAL": 3}
current_step = stages[st.session_state.stage]

col1, col2, col3 = st.columns(3)
with col1:
    if current_step == 1:
        st.info("🟢 **Step 1: 需求原点 (Ideation)**")
    else:
        st.markdown("✅ Step 1: 需求原点")
        
with col2:
    if current_step == 2: 
        st.info("🟢 **Step 2: 架构审阅 (Review)**")
    elif current_step > 2: 
        st.markdown("✅ Step 2: 架构审阅")
    else: 
        st.markdown("⚪ Step 2: 架构审阅")
        
with col3:
    if current_step == 3:
        st.info("🟢 **Step 3: 最终交付 (Final PRD)**")
    else:
        st.markdown("⚪ Step 3: 最终交付")

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
        idea = st.text_area(
            "一句话描述你的产品痛点或核心功能：", 
            height=120, 
            placeholder="例如：打工人经常忘记跨部门会议的 To-Do，我想做一个在微信里能自动识别会议纪要并提醒的机器人...",
            label_visibility="collapsed"
        )
        
        if st.button("⚡ 拆解需求架构 (Run Planner)"):
            if idea:
                st.session_state.user_idea = idea
                client = get_client()
                with st.spinner("Agent 正在为你规划 PRD 骨架..."):
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": "你是一个严谨的资深产品总监。请将用户的想法转化为一份清晰的 PRD 骨架大纲（包含目标、模块拆解、核心流程），不要写详细肉身，只需骨架大纲。"},
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
        st.markdown("#### 🏗️ 架构蓝图审阅 (Human-in-the-loop)")
        st.caption("AI 已生成初步架构。请作为产品经理进行专业审阅，修改或补充核心逻辑后，再生成全文：")
        
        edited_blueprint = st.text_area("架构蓝图编辑区", value=st.session_state.blueprint, height=400, label_visibility="collapsed")
        
        c1, c2, _ = st.columns([2, 2, 5])
        with c1:
            if st.button("🚀 确认架构并生成 PRD"):
                st.session_state.blueprint = edited_blueprint
                st.session_state.stage = "FINAL"
                st.rerun()
        with c2:
            if st.button("← 重新输入需求"):
                st.session_state.stage = "IDEATION"
                st.rerun()

# 【阶段 3：最终交付】
elif st.session_state.stage == "FINAL":
    if not st.session_state.final_prd:
        client = get_client()
        with st.spinner("Agent 执行器正在根据你确认的架构进行全文撰写，预计需要 15-30 秒..."):
            system_prompt = """你是一个在腾讯/字节拥有 5 年经验的高级产品经理。
            请根据用户提供的【原始需求】和确认后的【架构蓝图】，严格按照大纲结构，输出一份丰满、严谨的 PRD。
            文风要求专业极简，必须包含：业务背景、User Story、交互说明、验收标准 (Acceptance Criteria) 和 数据埋点指标。"""
            
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": f"【原始需求】：{st.session_state.user_idea}\n\n【架构蓝图】：\n{st.session_state.blueprint}"}]
            )
            st.session_state.final_prd = resp.choices[0].message.content
            st.rerun()
            
    with st.container(border=True):
        st.markdown("#### 📄 最终产品需求文档 (PRD)")
        st.markdown(st.session_state.final_prd)
        
    st.markdown('<div class="download-btn">', unsafe_allow_html=True)
    st.download_button(
        label="📥 下载 Markdown 格式文档", 
        data=st.session_state.final_prd, 
        file_name="Agent_PRD_Output.md",
        mime="text/markdown"
    )
    st.markdown('</div>', unsafe_allow_html=True)
