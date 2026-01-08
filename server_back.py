from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import pandas as pd

from llm_direct import call_llm_api

EXCEL_PATH = "/Users/yl_doc/Downloads/data-1767773780643.xlsx"

USER_PROFILE_DF = pd.read_excel(EXCEL_PATH)
USER_PROFILE_DF["user_id"] = USER_PROFILE_DF["user_id"].astype(str)
USER_PROFILE_DF.set_index("user_id", inplace=True)


def load_user_profile_from_excel(user_id: str) -> dict:
    user_id = str(user_id)
    if user_id not in USER_PROFILE_DF.index:
        return {}
    return USER_PROFILE_DF.loc[user_id].dropna().to_dict()


def format_user_profile_from_row(row: dict, scene: str = "chat") -> str:
    if not row:
        return "【用户画像】暂无可靠的历史画像数据。"

    lines = ["【用户画像（基于历史行为，可能存在偏差）】"]

    if row.get("gender"):
        lines.append(f"- 性别：{row['gender']}")
    if row.get("age"):
        lines.append(f"- 年龄段：{int(row['age'])} 岁左右")
    if row.get("height"):
        lines.append("- 身体条件：身高体型相对稳定")
    if row.get("bmi"):
        lines.append("- 体型特征：偏向健康区间")

    if row.get("interested_sports"):
        lines.append(f"- 感兴趣运动：{row['interested_sports']}")
    if row.get("sports"):
        lines.append(f"- 常参与运动：{row['sports']}")
    if row.get("all_training_times"):
        lines.append("- 有一定运动基础")
    if row.get("cycling_level"):
        lines.append(f"- 骑行经验：{row['cycling_level']}")

    if scene == "purchase":
        if row.get("activity_buy_count"):
            lines.append("- 有过装备购买经验")
        if row.get("activity_buy_pay"):
            lines.append("- 对装备品质有一定要求")

    return "\n".join(lines)


SYSTEM_PROMPT = """
### 人设信息 ###
-你长期研究并实际使用骑行、跑步、滑雪、健身、户外及康复相关的运动装备与器械，理解运动科学、生物力学、地理与气候差异，以及产品运营逻辑。你非常清楚“参数与营销概念”与“真实使用体验”之间的差距，擅长替用户做信息过滤，帮助新手与进阶用户在复杂的装备信息中做出理性、低风险的选择。
-你不仅是一个被动回答问题的顾问，更是一个主动收敛信息、构建决策路径的运动装备智能推荐顾问。核心目标是：在 1–2 次交互内，帮助用户做出可执行、低风险的运动装备购买决策

### 决策原则 ###
- 你的目标不是让用户一次买齐所有装备，而是让他们安心开始运动
- 始终以“是否真的能提升体验或降低受伤风险”为第一判断标准
- 明确区分「必备装备 / 可选但能改善体验的装备 / 阶阶段才有意义、当前不需要的装备」
- 对新手默认采用保守、低学习成本的推荐策略
- 在其他决策原则的基础上，同时考虑出片搭配，符合当下运动的主流配色和搭配
### 输出规则 ###
- 整体输出的逻辑可以归纳为 3 轮；
- 首轮推荐以【适度信息输出】+【清晰简单的推荐理由】+【符合用户信息不出错的装备推荐】为主要内容
- 次轮为明确的行动指令，帮助用户完成决策，输出内容可以有逻辑的丰富
- 最后一轮是一个兜底，如果用户有表达复杂的担忧或者是不安心，给出试错成本的解决方案
- 总体的结论优先
- 总字数 ≤ 300
- 任一列表 ≤ 4 条
- 可以输出结合用户的身高、体重等身体数据信息；所处地理位置的天气等地理信息给出的推荐，但是严格禁止输出用户肥胖、矮瘦等负面词汇，不得说用户消费习惯等敏感信息
- 文本中不使用 emoji
- 输出时文本不要带** xx **标题加粗 （一定），但是可以使用bullet point和数字有序标注
 
"""

PURCHASE_MODE_PROMPT = """
【当前模式：购买辅助（允许链接）】
【购买辅助输出规则（强制）】
- 不输出任何商品 URL
- 每个商品必须输出以下字段（非必要条件下，文本中禁用英文）：
  - id（中文，下划线）
  - 产品名称
  - 品牌
  - 官网首页链接，一定要保证链接可以打开可以使用，不能404（必须遵守）
  - 站内搜索关键词
  - 推荐理由（一句话，同时解释用户可以用产品关键词去网址内搜索）
  - 产品类别（核心运动器械，着装系统，保护 / 安全系统，背负系统，补给系统，训练 / 恢复系统）
"""

COMPARE_JSON_INSTRUCTION = """
你当前处于【产品对比输出模式】。
只输出 JSON，不得输出任何解释性文本。

{
  "type": "product_compare",
  "data": {
    "focus": "本次对比关注点",
    "items": [
      {
        "name": "产品名称",
        "pros": ["优点1"],
        "cons": ["限制1"]
      }
    ],
    "suggestion": "一句话倾向性建议"
  }
}
最终的回复要生产为自然语言，不要暴露json字符串。
"""

FINAL_JSON_INSTRUCTION = """
你现在需要给用户一个【最终购买结论】。

【要求】
- 第一行必须给出明确结论（选哪个 / 先买哪个）
- 使用判断型语言：要 / 不要 / 先 / 暂不需要
- 总字数 ≤ 120
- 不使用 JSON
- 不复述对比过程
- 不解释原理
- 最多 1 个下一步引导问题

示例格式（仅示意）：
结论：先买 A。
原因：……（1–2 句）
下一步：是否需要我帮你补齐 B？
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_STORE = {}


def is_purchase_intent(message: str) -> bool:
    return any(k in message for k in ["买", "购买", "下单", "链接", "在哪里买", "能买吗"])


def is_compare_intent(message: str) -> bool:
    return any(k in message for k in ["对比", "区别", "哪个好", "怎么选"])


def ensure_clickable_link(text: str) -> str:
    if "http" not in text:
        text += "\n\n（可在品牌官网搜索对应型号购买）"
    return text

def is_compare_payload(message: str) -> dict | None:
    try:
        obj = json.loads(message)
        if isinstance(obj, dict) and obj.get("intent") == "compare_products":
            return obj
    except Exception:
        pass
    return None

def build_system_prompt(is_purchase: bool) -> str:
    prompt = SYSTEM_PROMPT
    if is_purchase:
        prompt += "\n" + PURCHASE_MODE_PROMPT
    return prompt


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()

    user_id = body.get("user_id")
    message = body.get("message", "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    if not user_id or not message:
        return JSONResponse({"error": "user_id and message are required"}, status_code=400)

    history = SESSION_STORE.get(session_id, [])

    raw_profile = load_user_profile_from_excel(user_id)
    profile_block = format_user_profile_from_row(raw_profile, scene="purchase")

    # ===== 新增：结构化对比请求识别 =====
    compare_payload = is_compare_payload(message)

    def stream():
        nonlocal history
        # 【1. 结构化产品对比模式】
        if compare_payload:
            items = compare_payload.get("items", [])

            if len(items) < 2:
                yield f"data: {json.dumps({
                    'type': 'text',
                    'data': {'text': '至少需要两个商品才能对比'},
                    'session_id': session_id
                }, ensure_ascii=False)}\n\n"
                return

            compare_context = [
                profile_block,
                "",
                "【用户选择的待对比商品】"
            ]

            for i, item in enumerate(items, 1):
                compare_context.append(
                    f"{i}. {item.get('name')}（品牌：{item.get('brand')}）\n"
                    f"   分类：{item.get('category')}\n"
                    f"   推荐理由：{item.get('reason')}"
                )

            compare_prompt = "\n".join(compare_context)

            # ===== 调用对比 LLM =====
            compare_raw = call_llm_api(
                prompt=compare_prompt,
                system_prompt=SYSTEM_PROMPT + COMPARE_JSON_INSTRUCTION
            )

            try:
                compare_obj = json.loads(compare_raw)
            except Exception:
                compare_obj = {
                    "type": "text",
                    "data": {"text": compare_raw}
                }

            # 关键修复 ①：统一包成 type=text，前端才能显示
            compare_obj["session_id"] = session_id

            yield f"data: {json.dumps(compare_obj, ensure_ascii=False)}\n\n"

            # ===== 自动触发最终推荐 =====
            final_raw = call_llm_api(
                prompt=json.dumps(compare_obj, ensure_ascii=False),
                system_prompt=SYSTEM_PROMPT + FINAL_JSON_INSTRUCTION
            )

            try:
                final_obj = json.loads(final_raw)
            except Exception:
                final_obj = {
                    "type": "text",
                    "data": {"text": final_raw}
                }

            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": json.dumps(final_obj, ensure_ascii=False)}
            ])
            SESSION_STORE[session_id] = history

            # 关键修复 ②：final 也统一包 text + session_id
            final_obj["session_id"] = session_id

            yield f"data: {json.dumps(final_obj, ensure_ascii=False)}\n\n"
            return

        # 【2. 关键词触发的普通对比 】
        is_compare = is_compare_intent(message)
        is_purchase = is_purchase_intent(message)

        context_lines = [
            profile_block,
            "",
            "【历史对话】"
        ]
        for h in history:
            context_lines.append(f"{h['role'].upper()}: {h['content']}")
        context_lines.append(f"USER: {message}")
        context = "\n".join(context_lines)

        if is_compare:
            compare_raw = call_llm_api(
                prompt=context,
                system_prompt=SYSTEM_PROMPT + COMPARE_JSON_INSTRUCTION
            )

            try:
                compare_obj = json.loads(compare_raw)
            except Exception:
                compare_obj = {"type": "text", "data": {"text": compare_raw}}

            yield f"data: {json.dumps(compare_obj, ensure_ascii=False)}\n\n"

            if compare_obj.get("type") == "product_compare":
                final_raw = call_llm_api(
                    prompt=json.dumps(compare_obj, ensure_ascii=False),
                    system_prompt=SYSTEM_PROMPT + FINAL_JSON_INSTRUCTION
                )

                try:
                    final_obj = json.loads(final_raw)
                except Exception:
                    final_obj = {"type": "text", "data": {"text": final_raw}}

                history.extend([
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": json.dumps(final_obj, ensure_ascii=False)}
                ])
                SESSION_STORE[session_id] = history

                yield f"data: {json.dumps(final_obj | {'session_id': session_id}, ensure_ascii=False)}\n\n"
                return

        # 3. 购买模式
        if is_purchase:
            """
            强制 LLM 输出 JSON，包含：
            {
              "summary": "一句话判断",
              "items": [ {...商品结构...} ]
            }
            """
            purchase_json_instruction = """ 
            你当前处于【购买推荐输出模式】。
            只输出 JSON，不得输出任何解释性文本。
            
            {
              "summary": "一句话结论，必须是判断型语言",
              "items": [
                {
                  "id": "英文_id",
                  "name": "商品名称",
                  "brand": "品牌",
                  "official_site": "官网首页",
                  "search_hint": "站内搜索关键词",
                  "reason": "一句话理由",
                  "category": "base_layer / gloves / outerwear"
                }
              ]
            }
"""
            raw = call_llm_api(
                prompt=context,
                system_prompt=SYSTEM_PROMPT + PURCHASE_MODE_PROMPT + purchase_json_instruction
            )

            try:
                obj = json.loads(raw)
            except Exception:
                yield f"data: {json.dumps({'type':'text','data':{'text':raw}}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type':'text','data':{'text':obj.get('summary','')}}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type':'product_list','data':{'items':obj.get('items',[])}}, ensure_ascii=False)}\n\n"

            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": json.dumps(obj, ensure_ascii=False)}
            ])
            SESSION_STORE[session_id] = history
            return

        # 【4. 普通聊天】
        raw = call_llm_api(prompt=context, system_prompt=SYSTEM_PROMPT)

        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": raw}
        ])
        SESSION_STORE[session_id] = history

        yield f"data: {json.dumps({'type':'text','data':{'text':raw},'session_id':session_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
