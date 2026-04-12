import streamlit as st
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI PRD 生成器 Pro", page_icon="🚀", layout="wide")

# ── 预设服务商配置（自动联动 Base URL） ──────────────────────────────────────────
PROVIDERS = {
    "DeepSeek (推荐)": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "Kimi (Moonshot)": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k"]
    },
    "OpenAI (Global)": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    },
    "智谱 AI (GLM)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "models": ["glm-4", "glm-4-flash"]
    }
}

# ── 初始化 Session State ──────────────────────────────────────────────────────
if 'stage' not in st.session_state:
    st.session_state.stage = "IDEATION" 
if 'blueprint' not in st.session_state:
    st.session_state.blueprint = ""
if 'final_prd' not in st.session_state:
    st.session_state.final_prd = ""
if 'user_idea' not in st.session_state:
    st.session_state.user_idea = ""

# ── 全局样式注入 (完美兼容 Light/Dark 模式) ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&family=JetBrains+Mono:wght@400;600&display=swap');

/* 主标题保留第一版的渐变色，极其亮眼 */
.hero-title {
    font-family: 'Noto Serif SC', serif;
    font-size: 2.2rem;
    font-weight: 900;
    line-height: 1.3;
    background: linear-gradient(135deg, #f5c842 0%, #ff8c42 50%, #e84393 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #888; /* 中性灰，明暗模式下都好看 */
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

/* 第一版的金灿灿按钮 */
.stButton > button {
    background: linear-gradient(135deg, #f5c842, #ff8c42) !important;
    color: #0d0f14 !important;
    font-family: 'Noto Serif SC', serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.65rem 2rem !important;
    letter-spacing: 0.05em;
    transition: opacity 0.2s, transform 0.1s;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-2px);
}

/* 状态徽章 */
.badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    padding: 2px 10px;
    border-radius: 20px;
    background: rgba(245,200,66,0.12);
    color: #d4a017;
    border: 1px solid rgba(245,200,66,0.3);
    margin-bottom: 1.5rem;
}

/* 卡片容器：使用半透明适配系统主题 */
.glass-card {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 2rem;
    margin-top: 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    background: rgba(128, 128, 128, 0.03);
}
</style>
""", unsafe_allow_html=True)

# ── 侧边栏配置 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 引擎配置")
    
    provider_name = st.selectbox("🤖 选择大模型服务商", options=list(PROVIDERS.keys()))
    selected_provider = PROVIDERS[provider_name]
    
    api_key = st.text_input("🔑 API Key", type="password", placeholder="填入 sk-...")
    base_url = st.text_input("🌐 Base URL", value=selected_provider["base_url"])
    model = st.selectbox("⚡ 核心模型", options=selected_provider["models"])
    
    st.markdown("---")
    if st.button("🔄 重置工作流"):
        st.session_state.stage = "IDEATION"
        st.session_state.blueprint = ""
        st.session_state.final_prd = ""
        st.rerun()

# ── 主区域顶部 ────────────────────────────────────────────────────────────────
col_main, col_pad = st.columns([3, 1])
with col_main:
    st.markdown('<div class="hero-title">🚀 AI 产品经理的超级大脑</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Human-in-the-loop PRD Agent Engine</div>', unsafe_allow_html=True)
    
    # 动态显示当前阶段
    stage_text = "Step 1: 需求原点" if st.session_state.stage == "IDEATION" else ("Step 2: 架构蓝图审阅" if st.session_state.stage == "REVIEW" else "Step 3: 最终交付")
    st.markdown(f'<span class="badge">✦ 当前进度：{stage_text}</span>', unsafe_allow_html=True)

def get_client():
    if not api_key: 
        st.warning("⚠️ 请先在左侧输入 API Key 才能唤醒 Agent 哦！")
        st.stop()
    return OpenAI(api_key=api_key, base_url=base_url)

# ── 阶段 1：灵感捕获 ──────────────────────────────────────────────────────────
if st.session_state.stage == "IDEATION":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    idea = st.text_area("💡 你的产品构想是什么？", height=130, placeholder="例如：我想做一个帮大学生自动润色简历的小程序...")
    
    if st.button("✦ 第一步：生成 PRD 架构大纲 (Planner)"):
        if idea:
            st.session_state.user_idea = idea
            client = get_client()
            with st.spinner("🧠 资深 PM Agent 正在拆解需求骨架..."):
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": "你是一个资深产品总监。请将用户的想法转化为一份清晰的 PRD 骨架大纲（包含模块、流程、技术方向），不要写详细肉身，只需骨架。"},
                              {"role": "user", "content": idea}]
                )
                st.session_state.blueprint = resp.choices[0].message.content
                st.session_state.stage = "REVIEW"
                st.rerun()
        else:
            st.warning("哪怕只是一句话，也要填点想法哦！")
    st.markdown('</div>', unsafe_allow_html=True)

# ── 阶段 2：架构蓝图审阅 ──────────────────────────────────────────────────────
elif st.session_state.stage == "REVIEW":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("🎯 **AI 已生成初步架构。请作为 PM 进行专业审阅并微调大纲方向：**")
    
    edited_blueprint = st.text_area("✍️ 架构蓝图编辑区：", value=st.session_state.blueprint, height=350)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✦ 第二步：确认架构并生成全文 (Executor)"):
            st.session_state.blueprint = edited_blueprint
            st.session_state.stage = "FINAL"
            st.rerun()
    with col2:
        if st.button("返回上一步"):
            st.session_state.stage = "IDEATION"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── 阶段 3：最终 PRD 交付 ─────────────────────────────────────────────────────
elif st.session_state.stage == "FINAL":
    if not st.session_state.final_prd:
        client = get_client()
        with st.spinner("🚀 Agent 正在根据你确认的架构进行全文撰写与逻辑闭环，请稍候..."):
            system_prompt = """你是一个在腾讯/字节拥有 5 年经验的高级产品经理。
            请根据用户提供的【原始需求】和确认后的【架构蓝图】，严格按照大纲结构，输出一份丰满、严谨的 PRD。
            必须包含：产品背景、核心功能拆解 (User Story)、交互说明、验收标准和数据埋点指标。"""
            
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": f"【原始需求】：{st.session_state.user_idea}\n\n【架构蓝图】：\n{st.session_state.blueprint}"}]
            )
            st.session_state.final_prd = resp.choices[0].message.content
            st.rerun()
            
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📄 最终产品需求文档 (PRD)")
    st.markdown(st.session_state.final_prd)
    
    st.download_button(
        label="📥 下载 Markdown 格式文档", 
        data=st.session_state.final_prd, 
        file_name="Agent_PRD_Output.md",
        mime="text/markdown"
    )
    st.markdown('</div>', unsafe_allow_html=True)
