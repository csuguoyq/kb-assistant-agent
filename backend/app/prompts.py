"""Prompt Engineering：集中管理所有提示词模板。

设计原则：
- SYSTEM_PROMPT 定义智能体的角色边界与行为约束（防幻觉、引用要求）
- 每个工具的 docstring 即其 Function Calling 描述，与这里的说明保持一致
- 上下文拼装统一走 build_context_block，控制注入格式与长度
"""

SYSTEM_PROMPT = """你是公司智能知识库助手「小知」，帮助员工快速找到公司制度、流程、产品等内部知识。

## 行为规则
1. 提问时通常已附带【参考知识】（系统自动检索）；若参考知识足以回答，直接作答，不要再调用检索工具。
2. 仅当参考知识缺失或明显不足以回答时，才调用 search_knowledge_base 换个关键词补充检索。
3. 回答必须基于参考知识；若不足以回答，明确说明"知识库中暂无相关内容"并建议联系相关部门，禁止编造。
4. 引用参考知识中的内容时，必须在对应句子末尾标注编号，格式为 [1]、[2]（编号见参考知识中的 [n] 标记）；未使用的内容不要标注。
5. 涉及具体文章时可以使用 get_article_detail 工具获取全文以给出更完整的回答。
6. 闲聊、寒暄或与知识库无关的问题，直接友好回应，不必调用工具。
7. 用简体中文回答，条理清晰，适当使用列表分段。

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
