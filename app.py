import streamlit as st
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI PRD 极速生成器",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局样式注入 ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&family=JetBrains+Mono:wght@400;600&display=swap');

/* 整体背景 */
.stApp {
    background: #0d0f14;
    color: #e8e4dc;
}

/* 侧边栏 */
[data-testid="stSidebar"] {
    background: #13161e !important;
    border-right: 1px solid #2a2d38;
}
[data-testid="stSidebar"] * {
    color: #c9c5bc !important;
}

/* 主标题 */
.hero-title {
    font-family: 'Noto Serif SC', serif;
    font-size: 2.1rem;
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
    color: #5a5f72;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* 分割线 */
.divider {
    border: none;
    border-top: 1px solid #232633;
    margin: 1.5rem 0;
}

/* PRD 输出卡片 */
.prd-card {
    background: #13161e;
    border: 1px solid #2a2d38;
    border-radius: 12px;
    padding: 2rem 2.4rem;
    margin-top: 1.5rem;
    box-shadow: 0 4px 32px rgba(0,0,0,0.4);
}

/* 按钮覆盖 */
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
    transition: opacity 0.2s;
}
.stButton > button:hover {
    opacity: 0.85 !important;
}

/* 文本域 */
.stTextArea textarea {
    background: #13161e !important;
    color: #e8e4dc !important;
    border: 1px solid #2a2d38 !important;
    border-radius: 8px !important;
    font-size: 0.95rem !important;
}
.stTextArea textarea:focus {
    border-color: #f5c842 !important;
    box-shadow: 0 0 0 2px rgba(245,200,66,0.15) !important;
}

/* 输入框 */
.stTextInput input, .stSelectbox select {
    background: #1a1d27 !important;
    color: #e8e4dc !important;
    border: 1px solid #2a2d38 !important;
    border-radius: 6px !important;
}

/* 侧边栏标签 */
.sidebar-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #5a5f72;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
}

/* 状态徽章 */
.badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    padding: 2px 10px;
    border-radius: 20px;
    background: rgba(245,200,66,0.12);
    color: #f5c842;
    border: 1px solid rgba(245,200,66,0.25);
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是一个在腾讯/字节跳动拥有 5 年经验的资深技术产品经理，曾主导过多个亿级日活产品的从 0 到 1。
请根据用户的想法，输出一份结构严谨、专业可落地的产品需求文档（PRD）。

文档必须包含以下 5 个模块，每个模块用 Markdown 二级标题标注，内容丰富详实：

## 一、产品背景与目标
- **核心痛点**：当前用户面临什么问题？
- **目标用户**：精准描述用户画像（年龄、职业、使用场景）
- **商业价值**：该产品能带来什么商业收益或社会价值？

## 二、核心功能拆解（User Story）
以「作为…我希望…以便于…」格式撰写至少 5 条用户故事，并附上优先级（P0/P1/P2）。

## 三、AI 技术与软硬架构设计
- 需要用到的 AI 技术（如 LLM、RAG、向量数据库、多模态模型等）
- 系统架构简述（前端/后端/AI 服务/数据层的交互方式）
- 关键技术选型建议与理由

## 四、验收标准（Acceptance Criteria）
用表格形式给出至少 6 条具体可测试的验收条件，包含：功能项、测试场景、通过标准（如响应延迟 < 2s、错误率 < 0.1% 等）。

## 五、数据监控指标
列出上线后需要埋点监控的核心指标，分为：
- **用户行为指标**（如 DAU、留存率、任务完成率）
- **AI 效果指标**（如生成质量评分、用户反馈率）
- **系统稳定性指标**（如 P99 延迟、错误率、可用性 SLA）

请直接输出 PRD 正文，不要有任何前言或客套话。文风专业、精炼，数据有据可依。"""

# ── 侧边栏 ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 配置")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown('<p class="sidebar-label">🔑 API Key</p>', unsafe_allow_html=True)
    api_key = st.text_input(
        label="API Key",
        type="password",
        placeholder="sk-... 或其他兼容格式",
        label_visibility="collapsed",
    )

    st.markdown('<p class="sidebar-label" style="margin-top:1.2rem">🌐 Base URL（可选）</p>', unsafe_allow_html=True)
    base_url = st.text_input(
        label="Base URL",
        value="https://api.deepseek.com/v1",
        placeholder="https://api.openai.com/v1",
        label_visibility="collapsed",
        help="如使用国产大模型（如 DeepSeek、Moonshot、智谱等），请填入其兼容 OpenAI 格式的 Base URL",
    )

    st.markdown('<p class="sidebar-label" style="margin-top:1.2rem">🤖 模型选择</p>', unsafe_allow_html=True)
    model_options = [
        "deepseek-chat",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "moonshot-v1-8k",
        "glm-4",
        "qwen-plus",
    ]
    selected_model = st.selectbox(
        label="模型",
        options=model_options,
        label_visibility="collapsed",
    )

    st.markdown('<p class="sidebar-label" style="margin-top:1.2rem">🌡️ Temperature</p>', unsafe_allow_html=True)
    temperature = st.slider(
        label="Temperature",
        min_value=0.0,
        max_value=1.5,
        value=0.55,
        step=0.05,
        label_visibility="collapsed",
        help="值越高，输出越有创意；值越低，输出越严谨",
    )

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.72rem;color:#3a3f52;font-family:JetBrains Mono,monospace;">Agent for PM · v1.0</p>',
        unsafe_allow_html=True,
    )

# ── 主区域 ────────────────────────────────────────────────────────────────────
col_main, col_pad = st.columns([3, 1])

with col_main:
    st.markdown('<div class="hero-title">🚀 产品经理的超级AI大脑<br>一键生成标准 PRD</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Agent for PM · Powered by OpenAI-Compatible API</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge">✦ 5 模块专业文档 · 腾讯/字节跳动资深 PM 视角</span>', unsafe_allow_html=True)

    user_idea = st.text_area(
        label="产品想法",
        placeholder="请输入您的一句话产品想法（例如：我想做一个帮大学生改简历的 AI 小程序）...",
        height=130,
        label_visibility="collapsed",
    )

    generate_btn = st.button("✦ 一键生成架构与 PRD", use_container_width=False)

    # ── 核心逻辑 ──────────────────────────────────────────────────────────────
    # 初始化 Session State（如果还不存在的话）
    if "prd_result" not in st.session_state:
        st.session_state.prd_result = ""

    if generate_btn:
        # 校验输入
        if not api_key.strip():
            st.warning("⚠️  请先在左侧侧边栏填入您的 API Key，才能开始生成。")
            st.stop()

        if not user_idea.strip():
            st.warning("⚠️  请输入您的产品想法，哪怕只是一句话也行！")
            st.stop()

        # 调用 API（流式输出）
        try:
            client = OpenAI(
                api_key=api_key.strip(),
                base_url=base_url.strip() if base_url.strip() else "https://api.openai.com/v1",
            )

            st.markdown('<div class="prd-card">', unsafe_allow_html=True)
            status_placeholder = st.empty()
            status_placeholder.markdown(
                '<p style="color:#5a5f72;font-family:JetBrains Mono,monospace;font-size:0.8rem">⏳ 正在召唤资深 PM 神经元，请稍候...</p>',
                unsafe_allow_html=True,
            )

            stream = client.chat.completions.create(
                model=selected_model,
                temperature=temperature,
                max_tokens=4096,
                stream=True,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"产品想法：{user_idea.strip()}"},
                ],
            )

            status_placeholder.empty()
            prd_placeholder = st.empty()
            full_response = ""

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_response += delta.content
                    prd_placeholder.markdown(full_response)

            # 生成完毕，将完整结果保存到内存中！
            st.session_state.prd_result = full_response
            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            err_msg = str(e)
            if "auth" in err_msg.lower() or "api_key" in err_msg.lower() or "401" in err_msg:
                st.error("🔐  API Key 验证失败，请检查您填入的 Key 是否正确，以及 Base URL 是否匹配。")
            elif "model" in err_msg.lower() or "404" in err_msg:
                st.error(f"🤖  模型 `{selected_model}` 不存在或当前 Base URL 不支持该模型，请换一个试试。")
            elif "connect" in err_msg.lower() or "timeout" in err_msg.lower():
                st.error("🌐  网络连接失败，请检查 Base URL 是否可访问，或网络是否正常。")
            else:
                st.error(f"❌  生成过程中出现错误：\n\n```\n{err_msg}\n```")

    # ── 持久化显示区域 ────────────────────────────────────────────────────────
    # 只要内存里有内容，就把它显示出来（如果正在生成，就不重复画了）
    if st.session_state.prd_result:
        if not generate_btn:
            st.markdown('<div class="prd-card">', unsafe_allow_html=True)
            st.markdown(st.session_state.prd_result)
            st.markdown('</div>', unsafe_allow_html=True)

        st.download_button(
            label="📥 下载 PRD（Markdown格式）",
            data=st.session_state.prd_result,
            file_name="产品需求文档_AI生成.md",
            mime="text/markdown",
        )