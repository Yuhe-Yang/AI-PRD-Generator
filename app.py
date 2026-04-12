import streamlit as st
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI PRD 生成器 (Agent版)", page_icon="🚀", layout="wide")

# ── 初始化 Session State (实现记忆管理和多步交互的核心) ─────────────────────
# 这就是你向面试官吹牛的资本：“我用状态机管理了 Agent 的生命周期”
if 'stage' not in st.session_state:
    st.session_state.stage = 1  # 阶段1：输入想法，阶段2：修改大纲，阶段3：展示最终PRD
if 'outline_data' not in st.session_state:
    st.session_state.outline_data = ""
if 'final_prd' not in st.session_state:
    st.session_state.final_prd = ""
if 'user_idea' not in st.session_state:
    st.session_state.user_idea = ""

# ── 侧边栏配置 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Agent 配置")
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("Base URL", value="https://api.openai.com/v1")
    selected_model = st.selectbox("模型", ["deepseek-chat", "gpt-4o", "moonshot-v1-8k"])
    
    # 增加一个重置按钮
    if st.button("🔄 重置当前任务"):
        st.session_state.stage = 1
        st.session_state.outline_data = ""
        st.session_state.final_prd = ""
        st.session_state.user_idea = ""
        st.rerun()

# ── 主界面逻辑 ────────────────────────────────────────────────────────────────
st.title("🚀 AI-PM Agent: 人机协同 PRD 引擎")
st.markdown("`架构：规划器 (Planner) -> 人类确认 (Human-in-the-loop) -> 执行器 (Executor)`")

# 实例化客户端的辅助函数
def get_client():
    if not api_key:
        st.warning("⚠️ 请先在侧边栏输入 API Key")
        st.stop()
    return OpenAI(api_key=api_key.strip(), base_url=base_url.strip() if base_url else None)

# ==================== 阶段 1：用户输入与大纲规划 ====================
if st.session_state.stage == 1:
    st.info("📍 **Step 1: 需求输入**")
    idea = st.text_area("请输入你的一句话产品想法：", placeholder="例如：我想做一个帮大学生改简历的 AI 工具")
    
    if st.button("⚡ 第一步：让 Agent 生成 PRD 结构大纲 (Planner)"):
        if idea:
            st.session_state.user_idea = idea
            client = get_client()
            with st.spinner("Agent 规划器正在拆解需求..."):
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "你是一个资深产品总监。请根据用户的想法，仅仅输出一个 PRD 的目录大纲和核心功能列表。不要写详细内容，只需骨架。"},
                        {"role": "user", "content": idea}
                    ]
                )
                st.session_state.outline_data = response.choices[0].message.content
                st.session_state.stage = 2
                st.rerun()

# ==================== 阶段 2：人类干预与确认 ====================
elif st.session_state.stage == 2:
    st.warning("📍 **Step 2: 人类干预 (Human-in-the-loop)** - 请确认或修改 Agent 生成的大纲")
    st.markdown("为了防止生成结果失控，请你在生成完整文档前，先审阅并修改下方的大纲：")
    
    # 让用户可以修改大纲
    edited_outline = st.text_area("✍️ 审阅并编辑大纲：", value=st.session_state.outline_data, height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 第二步：确认大纲，生成完整 PRD (Executor)"):
            # 保存用户修改后的大纲，并进入下一步
            st.session_state.outline_data = edited_outline
            st.session_state.stage = 3
            st.rerun()
    with col2:
         if st.button("退回上一步"):
             st.session_state.stage = 1
             st.rerun()

# ==================== 阶段 3：执行生成与结果展示 ====================
elif st.session_state.stage == 3:
    st.success("📍 **Step 3: 完整 PRD 生成结果**")
    
    if not st.session_state.final_prd:
        client = get_client()
        
        # 核心：将原始想法和修改后的大纲一起发给模型（这就是短期记忆管理！）
        system_prompt = """你是一个在腾讯/字节拥有5年经验的高级PM。
        请根据用户提供的【原始想法】和【确认后的大纲】，严格按照大纲结构，扩写出一份丰满、专业的 PRD。
        必须包含：用户故事(User Story)、验收标准(Acceptance Criteria) 和 数据埋点指标。"""
        
        user_prompt = f"【原始想法】：{st.session_state.user_idea}\n\n【确认后的大纲】：\n{st.session_state.outline_data}"
        
        with st.spinner("Agent 执行器正在根据你的大纲全力撰写细节..."):
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            st.session_state.final_prd = response.choices[0].message.content
            st.rerun()
            
    # 展示最终结果
    st.markdown("### 📄 最终产品需求文档")
    st.markdown(st.session_state.final_prd)
    
    st.download_button("📥 下载 Markdown 格式文档", data=st.session_state.final_prd, file_name="Agent_PRD.md")
