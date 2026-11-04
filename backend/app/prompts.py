"""Prompt Engineering：集中管理所有提示词模板。

设计原则：
- SYSTEM_PROMPT 定义智能体的角色边界与行为约束（防幻觉、引用要求）
- 每个工具的 docstring 即其 Function Calling 描述，与这里的说明保持一致
- 上下文拼装统一走 build_context_block，控制注入格式与长度
"""

SYSTEM_PROMPT = """你是公司智能知识库助手「小知」，帮助员工快速找到公司制度、流程、产品等内部知识。

## 行为规则
1. 涉及公司内部知识的问题，必须先调用工具检索知识库，再基于检索结果回答，禁止凭空编造内部信息。
2. 回答基于提供的【参考知识】内容；若参考知识不足以回答，明确说明"知识库中暂无相关内容"，并可建议用户联系相关部门，不要猜测。
3. 引用参考知识中的内容时，必须在对应句子末尾标注编号，格式为 [1]、[2]（编号见参考知识中的 [n] 标记）；未使用的内容不要标注。
4. 涉及具体文章时可以使用 get_article_detail 工具获取全文以给出更完整的回答。
5. 闲聊、寒暄或与知识库无关的问题，直接友好回应，不必调用工具。
6. 用简体中文回答，条理清晰，适当使用列表分段。

## 当前日期
{today}"""


def build_context_block(hits: list[dict], start_index: int = 1) -> str:
    """Context Engineering：将检索到的片段拼装为受控格式的上下文块。

    每个片段带全局编号 [n]（跨多次检索连续），便于模型引用；
    生成结束后从回答文本解析被引用的编号，即可得到 LLM 实际使用的来源。
    """
    if not hits:
        return "【参考知识】\n（知识库中未检索到相关内容）"

    parts = ["【参考知识】（引用下述内容回答时，必须在对应句子末尾标注其编号，如 [1]、[2]；只能使用下列片段自带的编号，禁止编造编号）"]
    for i, hit in enumerate(hits, start_index):
        meta = []
        if hit.get("category"):
            meta.append(f"分类：{hit['category']}")
        if hit.get("section"):
            meta.append(f"章节：{hit['section']}")
        if hit.get("tags"):
            meta.append(f"标签：{hit['tags']}")
        meta_str = f"（{'，'.join(meta)}）" if meta else ""
        parts.append(f"[{i}] 《{hit['title']}》{meta_str}\n{hit['text']}")
    return "\n\n".join(parts)
