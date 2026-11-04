"""种子数据：默认分类与示例知识文章（发布状态，首次启动即自动向量化）。"""
import logging

from app.database import SessionLocal
from app.models.article import Article
from app.models.category import Category
from app.models.user import User
from app.utils.security import get_password_hash

logger = logging.getLogger("app.seed")

SEED_CATEGORIES = [
    ("公司制度", "考勤、假期、报销等公司规章制度"),
    ("IT 服务", "账号、网络、办公设备等 IT 相关指南"),
    ("产品知识", "公司产品介绍与常见问题"),
]

SEED_ARTICLES = [
    ("公司制度", "考勤制度说明",
     "公司实行弹性工作制：工作日 9:00-18:00 为核心工作时间，可在 8:00-10:00 之间弹性到岗。\n\n"
     "迟到定义：核心时间（9:00）后到岗记为迟到。每月前 3 次迟到不扣款，第 4 次起每次扣 50 元。\n\n"
     "加班：需要提前在 OA 系统提交加班申请，经部门负责人审批后有效。工作日加班按 1.5 倍调休，"
     "周末加班按 2 倍调休，法定节假日按 3 倍薪资或调休。"),
    ("公司制度", "年假与请假流程",
     "年假天数：入职满 1 年享 5 天，满 3 年享 10 天，满 5 年享 15 天。年假当年有效，可跨年使用至次年 3 月 31 日。\n\n"
     "请假流程：在 OA 系统「考勤假期」模块提交申请，1 天以内部门负责人审批，3 天以上需总监审批，"
     "7 天以上需 HRBP 与总监共同审批。病假需在返岗后 3 日内补交医院证明。\n\n"
     "婚假 10 天，产假 158 天，陪产假 15 天，丧假 3 天（直系亲属）。"),
    ("公司制度", "差旅报销制度",
     "交通：高铁二等座/飞机经济舱为标准，超出标准需提前说明。市内交通凭发票实报实销，每日上限 100 元。\n\n"
     "住宿：一线城市每晚 500 元，其他城市每晚 400 元。同城市连续住宿超过 5 晚可申请提高标准。\n\n"
     "报销流程：出差结束后 15 个工作日内在报销系统提交，上传发票照片并关联出差申请单，"
     "部门负责人与财务审核后 5 个工作日内打款。发票抬头为公司全称，纳税人识别号见 OA 首页。"),
    ("IT 服务", "VPN 使用指南",
     "申请：在内网门户「IT 服务台」提交 VPN 申请，主管审批后 IT 部门在 1 个工作日内开通。\n\n"
     "使用：下载 EasyConnect 客户端，服务器地址 vpn.example.com，使用企业统一账号登录。"
     "首次登录需修改初始密码并绑定手机验证码。\n\n"
     "常见问题：连接后无法访问内网请尝试断开重连；提示账号锁定请联系 IT 服务台（内线 8000）解锁。"),
    ("IT 服务", "办公设备申请与故障报修",
     "新设备申请：入职设备由部门行政统一配发；额外设备（显示器、扩展坞等）在 IT 服务台提交申请，主管审批后 3 个工作日内发放。\n\n"
     "故障报修：IT 服务台提交工单，紧急故障（无法开机、网络中断）可直接拨打内线 8001。"
     "维修期间可申请备用笔记本。\n\n"
     "设备归还：离职或转岗时需将全部设备归还 IT 部门并签字确认，遗失按折旧价赔偿。"),
    ("产品知识", "智能预约系统产品介绍",
     "智能预约系统是基于 AI Agent 的预约平台：用户通过自然语言与智能体对话即可完成场景选择、"
     "资源查询、预约与取消；商家可自助配置预约场景与规则，AI 自动生成匹配的资源。\n\n"
     "核心能力：自然语言意图识别（预约/查询/取消/闲聊）、可配置场景规则（开放时间、时长步长、"
     "每日上限等）、AI 生成资源、统一业务校验。\n\n"
     "技术栈：FastAPI + SQLAlchemy + LangGraph + DeepSeek + Vue 3。"),
]


def init_seed_data(db: SessionLocal):
    editor = db.query(User).filter(User.role == "editor").first()

    for name, desc in SEED_CATEGORIES:
        if not db.query(Category).filter(Category.name == name).first():
            db.add(Category(name=name, description=desc))
    db.commit()

    categories = {c.name: c for c in db.query(Category).all()}
    created = 0
    for cat_name, title, content in SEED_ARTICLES:
        if db.query(Article).filter(Article.title == title).first():
            continue
        db.add(Article(
            title=title,
            content=content,
            category_id=categories[cat_name].id if cat_name in categories else None,
            editor_id=editor.id if editor else 1,
            status="published",
        ))
        created += 1
    db.commit()

    if created:
        # 新增的种子文章同步向量库（导入放函数内避免循环依赖启动顺序问题）
        from app.services import rag
        from app.routers.articles import _sync_vector
        for _, title, _c in SEED_ARTICLES:
            article = db.query(Article).filter(Article.title == title).first()
            if article:
                try:
                    _sync_vector(article)
                except Exception as e:
                    logger.warning("种子文章 %s 向量化失败（无 Embedding key 时可忽略）: %s", title, e)
        logger.info("种子文章已创建 %s 篇", created)
