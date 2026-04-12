import streamlit as st
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI PRD Pro Agent", page_icon="🎨", layout="wide")

# ── 预设服务商配置（自动联动 Base URL） ──────────────────────────────────────────
PROVIDERS = {
    "DeepSeek (推荐)": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "OpenAI (Global)": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    },
    "Kimi (Moonshot)": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k"]
    },
    "智谱 AI (GLM)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "models": ["glm-4", "glm-4-flash"]
    }
}

# ── 初始化 Session State ──────────────────────────────────────────────────────
if 'stage' not in st.session_state:
    st.session_state.stage = "IDEATION" # 阶段：IDEATION, REVIEW, FINAL
if 'blueprint' not in st.session_state:
    st.session_state.blueprint = ""
if 'final_prd' not in st.session_state:
    st.session_state.final_prd = ""
if 'user_idea' not in st.session_state:
    st.session_state.user_idea = ""

# ── 样式注入（极致暗黑/专业排版） ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Noto+Sans+SC:wght@300;500;700&display=swap');

.stApp { background: #0a0c10; color: #d1d5db; font-family: 'Noto Sans SC', sans-serif; }
[data-testid="stSidebar"] { background: #11141b !important; border-right: 1px solid #1f2937; }

/* 标题美化 */
.main-title { font-size: 2.2rem; font-weight: 800; background: linear-gradient(90deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }
.sub-tag { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #6b7280; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 2rem; }

/* 流程进度条 */
.step-bar { display: flex; gap: 10px; margin-bottom: 2rem; }
.step { flex: 1; height: 4px; border-radius: 2px; }
.step-active { background: #3b82f6; box-shadow: 0 0 10px rgba(59, 130, 246, 0.5); }
.step-inactive { background: #374151; }

/* 内容卡片 */
.glass-card { background: rgba(17, 24, 39, 0.7); border: 1px solid #1f2937; border-radius: 12px; padding: 2rem; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }

/* 按钮自定义 */
.stButton > button { border-radius: 8px !important; background: #3b82f6 !important; color: white !important; font-weight: 600 !important; border: none !important; transition: all 0.2s; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(59,130,246,0.3); }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏配置 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛠️ 工作流引擎配置")
    
    provider_name = st.selectbox("选择 AI 服务商", options=list(PROVIDERS.keys()))
    selected_provider = PROVIDERS[provider_name]
    
    api_key = st.text_input("API Access Key", type="password", placeholder="填入 sk-...")
    base_url = st.text_input("Base URL", value=selected_provider["base_url"])
    model = st.selectbox("核心模型节点", options=selected_provider["models"])
    
    st.markdown("---")
    if st.button("🔄 开启新任务"):
        st.session_state.stage = "IDEATION"
        st.session_state.blueprint = ""
        st.session_state.final_prd = ""
        st.rerun()

# ── 顶层导航 ──────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">AI-PM PRO AGENT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-tag">Architecture-First PRD Engine v3.0</div>', unsafe_allow_html=True)

# 绘制进度条
s1, s2, s3 = ("step-active", "step-inactive", "step-inactive")
if st.session_state.stage == "REVIEW": s1, s2 = "step-active", "step-active"
if st.session_state.stage == "FINAL": s1, s2, s3 = "step-active", "step-active", "step-active"
st.markdown(f'<div class="step-bar"><div class="step {s1}"></div><div class="step {s2}"></div><div class="step {s3}"></div></div>', unsafe_allow_html=True)

def get_client():
    if not api_key: st.warning("请先配置 API Key"); st.stop()
    return OpenAI(api_key=api_key, base_url=base_url)

# ── 阶段 1：灵感捕获与架构规划 ─────────────────────────────────────────────────
if st.session_state.stage == "IDEATION":
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### 💡 需求原点")
        idea = st.text_area("在此输入您的产品构想或核心痛点：", height=150, placeholder="例如：一个为独立开发者设计的、集成 AI 代码审查功能的透明桌面看板...")
        
        if st.button("开始架构规划 (Run Planner)"):
            if idea:
                st.session_state.user_idea = idea
                client = get_client()
                with st.spinner("AI Agent 正在进行多维度需求拆解..."):
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": "你是一个资深产品专家。请将用户模糊的需求转化为一份专业的 PRD 架构大纲，包含核心模块、业务流程逻辑和技术选型。"},
                                  {"role": "user", "content": idea}]
                    )
                    st.session_state.blueprint = resp.choices[0].message.content
                    st.session_state.stage = "REVIEW"
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ── 阶段 2：产品经理架构审阅 ─────────────────────────────────────────────────
elif st.session_state.stage == "REVIEW":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("#### 🏗️ 架构蓝图审阅")
    st.markdown("AI 已经为您规划了初步架构。请进行专业审阅并根据实际业务逻辑进行微调：")
    
    edited_blueprint = st.text_area("编辑架构蓝图：", value=st.session_state.blueprint, height=350)
    
    if st.button("确认架构并填充内容 (Generate PRD)"):
        st.session_state.blueprint = edited_blueprint
        st.session_state.stage = "FINAL"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── 阶段 3：最终 PRD 交付 ────────────────────────────────────────────────────
elif st.session_state.stage == "FINAL":
    if not st.session_state.final_prd:
        client = get_client()
        with st.spinner("正在根据确认的架构进行全文填充与逻辑闭环..."):
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "你是一个拥有腾讯/字节大厂经验的资深PM。请根据确认的架构蓝图，扩写成一份完整、专业、具备数据埋点和验收标准的 PRD。"},
                          {"role": "user", "content": f"原始需求：{st.session_state.user_idea}\n确认架构：{st.session_state.blueprint}"}]
            )
            st.session_state.final_prd = resp.choices[0].message.content
            st.rerun()
            
    st.markdown("#### ✅ 最终交付：产品需求文档 (PRD)")
    st.markdown(st.session_state.final_prd)
    st.download_button("📥 导出 Markdown 文档", data=st.session_state.final_prd, file_name="Product_PRD.md")
