# Phase 5：Chat 骨架（预留扩展）

**目标**：搭 Chat 链路骨架（数据库 + DAO + 路由 + 占位回复），便于后续挂载查询工具。本次不实现实际查询能力。

> 上一阶段：[05_Phase4_数据质量评估.md](./05_Phase4_数据质量评估.md)
> 下一阶段：[07_全局验收与风险.md](./07_全局验收与风险.md)

---

## Phase 5 后端任务

### 5.1 数据库迁移

- `app/alembic/versions/0005_v2_init_chat.py`：
  - 建 `chat_sessions` 表（id VARCHAR(64) PK uuid4 / title / created_at / updated_at）
  - 建 `chat_messages` 表（id BIGSERIAL / session_id VARCHAR(64) / role VARCHAR(16) / content TEXT / metadata JSONB / created_at）
  - 索引：B-tree(session_id)

### 5.2 ORM + DAO + Schemas

- `app/model/chat.py`：ChatSession + ChatMessage 类
- `app/dao/chat.py`：
  - `create_session(title)` / `list_sessions()` / `delete_session(id)` / `get_messages(session_id)`
  - `add_message(session_id, role, content, metadata)`
- `app/schemas/chat.py`：CreateSessionRequest/SessionList/MessageList/SendMessage

### 5.3 Service

- `app/service/chat.py`：
  - `create_session()` / `list_sessions()` / `delete_session(id)` / `get_history(session_id)`
  - `async def send_message(session_id, content) -> dict`：
    1. 落 user 消息
    2. 调用 chat agent（agent 只绑定 `echo_tool`，本次直接返回占位文本）
    3. 落 assistant 消息
    4. 更新 session.title（首条消息取前 20 字）
    5. 返回 `{ok: True, user_message, assistant_message}`

### 5.4 Agent 骨架

- `app/agents/chat/builder.py`：

  ```python
  def build() -> Agent:
      """本次仅绑定 1 个 echo_tool，后续可挂载 query_dataset_tool 等"""
      llm = _build_llm_unthinking()
      return create_agent(model=llm, tools=[echo_tool], system_prompt=CHAT_PROMPT)
  ```

- `app/agents/chat/prompt.py`：
  - "你是开放数据小D。当前为骨架模式，所有消息将直接 echo 返回。后续将挂载数据集查询、元数据评估查询、数据质量查询等工具。"

- `app/agents/tools/chat_tool.py`（**新增**）：

  ```python
  @tool
  async def echo_tool(text: str) -> str:
      """Echo 输入文本。本次为占位实现"""
      return f"echo: {text}"

  # === 后续可挂载的查询工具（接口已定义，实现待补） ===
  # @tool
  # async def query_dataset_tool(dataset_id: str) -> str:
  #     """查询数据集元数据"""
  # @tool
  # async def query_evaluation_tool(dataset_id: str) -> str:
  #     """查询元数据评估报告"""
  # @tool
  # async def query_quality_tool(dataset_id: str) -> str:
  #     """查询数据质量评估报告"""
  ```

- `app/nodes/chat_graph.py`：极简单步（不引入 langgraph 复杂度）

  ```python
  async def chat_node(state: dict) -> dict:
      """单步：调 agent → 返回消息"""
      agent = build_chat_agent()
      result = await agent.ainvoke({"messages": state["messages"]})
      return {"messages": result["messages"]}
  ```

### 5.5 API（**本次非 SSE，普通 JSON**）

- `app/api/routes/chat.py`：

  ```python
  @router.get("/chat/sessions")                       # 列表
  @router.post("/chat/sessions")                      # 新建
  @router.delete("/chat/sessions/{id}")               # 删除
  @router.get("/chat/sessions/{id}/messages")         # 历史
  @router.post("/chat/sessions/{id}/messages")        # 发送（JSON 返回）
  ```

---

## Phase 5 前端任务

### 5.6 API 改造

- `web/src/api/chat.ts`：在已有 SSE 基础上，**新增非流式方法**：
  - `listSessions()` / `createSession()` / `deleteSession()` / `getMessages()` / `sendMessageSync(content)` - 普通 JSON

### 5.7 View 改造

- `web/src/views/ChatView.vue`：占位改造为引用 ChatLayout（Phase 0 已搬过来）
- `web/src/components/chat/ChatInput.vue`：**改造**为非流式提交（直接调 sendMessageSync）

---

## Phase 5 验收标准

- [ ] 迁移成功，2 张表存在
- [ ] `POST /chat/sessions` 创建会话成功
- [ ] `POST /chat/sessions/{id}/messages` 发送消息，返回占位响应，user + assistant 都落库
- [ ] `GET /chat/sessions/{id}/messages` 能查到历史
- [ ] 前端 ChatView 能创建会话、发消息、看到 echo 回复

---

✅ **本 Phase 验收清单全勾完成后，进入全局验收。**
