#!/usr/bin/env python3
"""Build the reviewable 28-case evaluation pilot from approved P0 chunks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/processed/p0/chunks.jsonl"
OUTPUT = ROOT / "data/evaluation/pilot-cases.jsonl"
REVIEW = ROOT / "docs/evaluation-pilot-review.md"
AS_OF = "2026-10-18"


def ev(document_id: str, article: str | None, contains: str) -> dict:
    return {"document_id": document_id, "article": article, "contains": contains}


def case(
    number: int,
    question: str,
    question_type: str,
    risk_level: str,
    answerable: bool,
    gold_answer: str,
    required_claims: list[str],
    forbidden_claims: list[str],
    evidence_refs: list[dict],
    reasoning_outline: list[str],
    expected_behavior: str,
    tags: list[str],
    as_of_date: str = AS_OF,
) -> dict:
    return {
        "schema_version": "1.0",
        "case_id": f"CN-PRIV-{number:04d}",
        "question": question,
        "question_type": question_type,
        "risk_level": risk_level,
        "answerable": answerable,
        "gold_answer": gold_answer,
        "required_claims": required_claims,
        "forbidden_claims": forbidden_claims,
        "evidence_refs": evidence_refs,
        "reasoning_outline": reasoning_outline,
        "expected_behavior": expected_behavior,
        "as_of_date": as_of_date,
        "tags": tags,
        "split": "unassigned",
        "review_status": "draft",
        "review_note": None,
    }


SPECS = [
    case(1, "《个人信息保护法》所称个人信息和个人信息处理分别包括什么？", "single_document_fact", "low", True,
         "个人信息是以电子或者其他方式记录的、与已识别或者可识别自然人有关的各种信息，但不包括匿名化处理后的信息。个人信息处理包括收集、存储、使用、加工、传输、提供、公开、删除等。",
         ["说明个人信息与已识别或者可识别自然人有关", "排除匿名化处理后的信息", "列明处理至少包括收集、存储、使用、加工、传输、提供、公开、删除"],
         ["把匿名化后的信息仍一概认定为个人信息"],
         [ev("cn-pipl-2021", "第四条", "不包括匿名化处理后的信息")],
         ["定位个人信息保护法中的定义条款", "分别提取个人信息和处理的定义"], "answer", ["definition", "personal_information"]),
    case(2, "哪些信息属于敏感个人信息？处理这类信息需要满足什么基本条件？", "single_document_fact", "medium", True,
         "敏感个人信息是泄露或非法使用后容易侵害人格尊严，或者危害人身、财产安全的个人信息，包括生物识别、宗教信仰、特定身份、医疗健康、金融账户、行踪轨迹等，以及不满十四周岁未成年人的个人信息。只有具有特定目的、充分必要性并采取严格保护措施时方可处理。",
         ["给出敏感个人信息的风险定义", "列出法条中的代表性类别", "指出不满十四周岁未成年人个人信息属于敏感个人信息", "说明特定目的、充分必要性和严格保护措施"],
         ["声称列举类别是封闭清单", "声称取得一般同意即可无条件处理"],
         [ev("cn-pipl-2021", "第二十八条", "不满十四周岁未成年人的个人信息")],
         ["定位敏感个人信息定义", "合并类型范围与处理前提"], "answer", ["sensitive_personal_information", "minors"]),
    case(3, "《数据安全法》如何定义数据、数据处理和数据安全？", "single_document_fact", "low", True,
         "数据是任何以电子或者其他方式对信息的记录；数据处理包括数据的收集、存储、使用、加工、传输、提供、公开等；数据安全是通过必要措施确保数据处于有效保护和合法利用状态，并具备保障持续安全状态的能力。",
         ["定义数据", "列出数据处理的主要活动", "定义数据安全同时包含有效保护、合法利用和持续安全能力"],
         ["把数据限定为电子记录", "把数据安全仅解释为保密性"],
         [ev("cn-data-security-law-2021", "第三条", "任何以电子或者其他方式")],
         ["定位数据安全法定义条款", "区分三个相邻概念"], "answer", ["definition", "data_security"]),
    case(4, "女性健康类 App 的基本功能服务是否必须收集个人信息？", "single_document_fact", "medium", True,
         "不必须。《常见类型移动互联网应用程序必要个人信息范围规定》第五条规定，女性健康类 App 的基本功能服务无需个人信息即可使用。",
         ["明确回答无需个人信息即可使用基本功能", "引用第五条女性健康类条目"],
         ["声称手机号、经期或孕育信息属于该类 App 基本功能的法定必要信息"],
         [ev("cn-app-necessary-pi-scope-provisions-2021", "第五条", "女性经期管理、备孕育儿")],
         ["定位第五条中的具体 App 类别", "区分业务可能想收集的信息与法定必要信息"], "answer", ["app", "necessary_information", "women_health"]),

    case(5, "根据《个人信息保护法》第十七条，处理个人信息前应告知哪些事项？", "exact_article", "medium", True,
         "应以显著方式、清晰易懂的语言，真实、准确、完整地告知：处理者名称或姓名和联系方式；处理目的、方式、信息种类和保存期限；个人行使法定权利的方式和程序；法律、行政法规规定的其他事项。事项变更时应告知变更部分；以处理规则告知的，规则应公开且便于查阅和保存。",
         ["列全四类告知事项", "说明变更部分需告知", "说明处理规则应公开且便于查阅和保存"],
         ["遗漏处理者联系方式或保存期限", "声称只需在隐私政策中笼统告知"],
         [ev("cn-pipl-2021", "第十七条", "保存期限")],
         ["按指定条款定位", "完整还原告知清单和补充要求"], "answer", ["notice", "personal_information"]),
    case(6, "《个人信息保护法》第五十五条规定哪些情形应当事前开展个人信息保护影响评估？", "exact_article", "high", True,
         "包括：处理敏感个人信息；利用个人信息进行自动化决策；委托处理、向其他处理者提供或公开个人信息；向境外提供个人信息；以及其他对个人权益有重大影响的个人信息处理活动。还应对处理情况进行记录。",
         ["列全五类触发情形", "指出评估应事前开展", "指出还需记录处理情况"],
         ["把影响评估说成事故发生后才进行", "遗漏个人信息出境"],
         [ev("cn-pipl-2021", "第五十五条", "事前进行个人信息保护影响评估")],
         ["按指定条款定位", "提取所有触发情形与记录义务"], "answer", ["impact_assessment", "high_risk_processing"]),
    case(7, "处理超过1000万人个人信息的处理者，至少多久开展一次个人信息保护合规审计？依据哪一条？", "exact_article", "medium", True,
         "至少每两年开展一次，依据《个人信息保护合规审计管理办法》第四条。",
         ["阈值是超过1000万人", "频率是每两年至少一次", "引用第四条"],
         ["混淆为处理100万人以上", "声称每年必须一次"],
         [ev("cn-pi-compliance-audit-measures-2025", "第四条", "每两年至少")],
         ["核对适用人数阈值", "提取最低审计频率和条款号"], "answer", ["compliance_audit", "threshold"]),
    case(8, "现行《网络安全法》哪一条要求网络日志留存不少于六个月？该条规定的义务主体是谁？", "exact_article", "medium", True,
         "第二十三条。义务主体是网络运营者，其应按照网络安全等级保护制度履行安全保护义务，其中包括监测、记录网络运行状态和网络安全事件，并按规定留存相关网络日志不少于六个月。",
         ["条款号为第二十三条", "主体为网络运营者", "留存期限不少于六个月", "说明其属于网络安全等级保护义务"],
         ["引用旧版条款号而不说明版本", "把主体限定为关键信息基础设施运营者"],
         [ev("cn-cybersecurity-law-2025", "第二十三条", "网络日志不少于六个月")],
         ["使用2025年修正后的现行整合文本", "定位日志义务的条款号、主体和期限"], "answer", ["cybersecurity", "log_retention", "current_version"]),

    case(9, "紧急情况下为保护自然人的生命健康，来不及事前告知就处理个人信息，是否永久免除告知义务？", "condition_exception", "medium", True,
         "不是。紧急情况下无法及时告知的，可以暂时不在处理前告知，但应在紧急情况消除后及时告知。另有法律、行政法规规定应保密或不需要告知的情形，才可依该规定不告知。",
         ["区分暂时无法及时告知与永久免除", "说明紧急情况消除后应及时告知", "说明法定保密或无需告知属于另一类例外"],
         ["声称紧急处理后无需再告知"],
         [ev("cn-pipl-2021", "第十八条", "紧急情况消除后及时告知")],
         ["识别问题中的紧急情形", "适用延后告知规则而非永久豁免"], "answer", ["notice", "emergency", "exception"]),
    case(10, "公司为实施人力资源管理而处理员工个人信息，是否一律必须取得员工同意？", "condition_exception", "high", True,
         "不一律必须。按照依法制定的劳动规章制度和依法签订的集体合同实施人力资源管理所必需的，可以不以个人同意为处理依据；超出该必要范围或不满足这些前提时，不能仅凭“人力资源管理”主张该依据，还需判断是否存在其他合法处理依据。",
         ["说明不是一律需要同意", "限定为依法制定的劳动规章制度和依法签订的集体合同", "限定为人力资源管理所必需", "超范围时需另找合法依据"],
         ["声称任何员工数据都可无同意处理", "忽略必要性和制度/集体合同前提"],
         [ev("cn-pipl-2021", "第十三条", "实施人力资源管理所必需")],
         ["识别处理依据问题", "逐项检查劳动规则、集体合同和必要性条件", "给出有条件结论"], "answer", ["lawful_basis", "employment", "exception"]),
    case(11, "自动化采集不可避免地收集到非必要或未获同意的个人信息时，是否必须立即物理删除？", "condition_exception", "medium", True,
         "原则上应删除或匿名化处理。但法定保存期限尚未届满，或者从技术上难以删除、匿名化的，可以不立即物理删除；此时应停止除存储和采取必要安全保护措施之外的处理。",
         ["原则是删除或匿名化", "指出法定保存期限未届满或技术上难以实现两类例外", "例外下只允许存储和必要安全保护措施"],
         ["声称可以继续正常使用这些信息", "声称在所有情况下都必须立即物理删除"],
         [ev("cn-network-data-regulation-2024", "第二十四条", "停止除存储和采取必要的安全保护措施之外的处理")],
         ["先识别一般处置规则", "再判断是否落入保存期限或技术困难例外", "限定例外期间允许的处理"], "answer", ["deletion", "automated_collection", "exception"]),
    case(12, "非关键信息基础设施运营者当年向境外提供8万人的非敏感个人信息，不含重要数据，且不属于其他特殊情形，是否必须走安全评估、标准合同或认证？", "condition_exception", "high", True,
         "在题设条件下，不必须走这三种机制。非关键信息基础设施运营者自当年1月1日起累计向境外提供不满10万人非敏感个人信息，且不包含重要数据的，免予申报安全评估、订立标准合同和通过认证。但其他个人信息保护义务仍需履行。",
         ["确认主体不是关键信息基础设施运营者", "确认数量是不满10万人且不含敏感个人信息", "确认不得包含重要数据", "结论是三种机制均免予而非所有义务豁免"],
         ["声称个人信息出境的全部义务均免除", "把8万人误判为必须订立标准合同"],
         [ev("cn-cross-border-data-flow-provisions-2024", "第五条", "不满10万人个人信息")],
         ["核对主体、累计期间、数量、敏感性和重要数据条件", "适用小规模出境豁免", "保留其他法定义务"], "answer", ["cross_border_data", "threshold", "exemption"]),

    case(13, "非关基运营者当年拟向境外提供60万人的非敏感个人信息，不含重要数据，也不适用合同履行等豁免，应选择什么出境机制？", "cross_document", "high", True,
         "应依法与境外接收方订立个人信息出境标准合同，或者通过个人信息保护认证；该数量区间本身不触发数据出境安全评估。无论选择哪种机制，仍应采取必要措施，使境外接收方的处理达到个人信息保护法规定的标准。",
         ["适用10万人以上、不满100万人的非敏感个人信息区间", "结论为标准合同或认证二选一", "说明题设下不因数量触发安全评估", "说明仍需保障境外接收方达到法定保护标准"],
         ["声称必须安全评估", "声称只需取得个人同意即可"],
         [ev("cn-cross-border-data-flow-provisions-2024", "第八条", "10万人以上、不满100万人"), ev("cn-pipl-2021", "第三十八条", "达到本法规定的个人信息保护标准")],
         ["先按2024年规定判断数量区间和机制", "再叠加个人信息保护法对境外接收方保护水平的要求"], "answer", ["cross_border_data", "standard_contract", "certification"]),
    case(14, "关键信息基础设施运营者确需向境外提供其在境内收集的个人信息，应走什么程序？", "cross_document", "high", True,
         "原则上应在境内存储；确需向境外提供的，应通过国家网信部门组织的数据出境安全评估。法律、行政法规或国家网信部门另有规定可以不评估的，从其规定。",
         ["说明原则上境内存储", "确需出境时应进行国家网信部门组织的安全评估", "保留法定例外"],
         ["声称订立标准合同即可替代安全评估", "遗漏另有规定的例外"],
         [ev("cn-pipl-2021", "第四十条", "关键信息基础设施运营者"), ev("cn-cross-border-data-flow-provisions-2024", "第七条", "关键信息基础设施运营者向境外提供个人信息")],
         ["确认主体为关键信息基础设施运营者", "组合境内存储原则与2024年申报规则", "给出带例外的结论"], "answer", ["cross_border_data", "ciio", "security_assessment"]),
    case(15, "处理13周岁用户的个人信息，应同时关注哪些特别要求？", "cross_document", "high", True,
         "13周岁用户属于不满十四周岁未成年人，其个人信息属于敏感个人信息。处理者应取得其父母或其他监护人的同意，并制定专门的个人信息处理规则；还应满足处理敏感个人信息的特定目的、充分必要性和严格保护措施等要求。",
         ["判断13周岁属于不满十四周岁", "其个人信息属于敏感个人信息", "取得父母或其他监护人同意", "制定专门处理规则", "满足敏感信息处理的强化条件"],
         ["声称13周岁本人同意即可", "只要求一般同意而忽略专门规则和严格保护"],
         [ev("cn-pipl-2021", "第二十八条", "不满十四周岁未成年人的个人信息"), ev("cn-pipl-2021", "第三十一条", "父母或者其他监护人的同意"), ev("cn-network-data-regulation-2024", "第二十二条", "不满十四周岁未成年人个人信息")],
         ["根据年龄确定未成年人特别规则", "组合敏感个人信息与监护人同意要求", "列出专门规则和保护条件"], "answer", ["minors", "sensitive_personal_information", "consent"]),
    case(16, "发生个人信息泄露后，处理者是否都可以只采取补救措施而不通知个人和监管部门？", "cross_document", "high", True,
         "不可以。处理者应立即采取补救措施，并通知履行个人信息保护职责的部门和个人；民法典也要求及时补救并按规定告知自然人、向主管部门报告。只有处理者采取措施能够有效避免危害时，才可以不通知个人，但监管部门认为可能造成危害的仍可要求通知；这不等于免除向主管部门通知或报告。",
         ["立即或及时采取补救措施", "原则上通知主管部门和个人", "有效避免危害时可不通知个人", "监管部门仍可要求通知个人", "个人通知例外不等于主管部门通知豁免"],
         ["声称采取补救措施后当然无需任何通知", "把不通知个人的例外扩大到不通知主管部门"],
         [ev("cn-pipl-2021", "第五十七条", "可以不通知个人"), ev("cn-civil-code-2020-privacy-sections", "第一千零三十八条", "向有关主管部门报告")],
         ["组合个人信息保护法和民法典的事件处置义务", "区分个人通知例外与主管部门通知/报告"], "answer", ["incident_response", "notification", "data_breach"]),

    case(17, "截至2026年10月，网络安全法问答应引用2016年原始文本还是2025年修正后的文本？", "version_conflict", "high", True,
         "应以2025年修正后的现行整合文本为准，并明确版本。当前 P0 文本标明该法于2016年通过，并根据2025年10月28日的修改决定修正；对指定的更早历史时点则需另行使用当时有效版本。",
         ["当前问题使用2025年修正文本", "说明2016年是通过时间而不是当前唯一版本", "历史时点需使用当时有效版本"],
         ["把2016年原始文本当作2026年的唯一现行依据", "虚构2025年后又有新的修订"],
         [ev("cn-cybersecurity-law-2025", None, "2025年10月28日")],
         ["识别问题的基准日期", "读取现行整合文本的修正说明", "区分当前问答和历史时点问答"], "answer", ["versioning", "cybersecurity", "current_version"]),
    case(18, "2026年通过数据出境安全评估后，评估结果有效期应按2年还是3年计算？", "version_conflict", "high", True,
         "按3年计算。《数据出境安全评估办法》第十四条原规定2年，但后来的《促进和规范数据跨境流动规定》第九条改为3年；两者不一致时，依该规定第十三条适用后者。",
         ["现行结论为3年", "指出旧办法曾规定2年", "说明后来的规定优先适用", "引用第九条和第十三条"],
         ["仍以2年作为2026年的有效期", "不说明规则变更依据"],
         [ev("cn-data-export-security-assessment-measures-2022", "第十四条", "有效期为2年"), ev("cn-cross-border-data-flow-provisions-2024", "第九条", "有效期为3年"), ev("cn-cross-border-data-flow-provisions-2024", "第十三条", "适用本规定")],
         ["识别同一事项的先后规则", "比较2年与3年规定", "依据冲突条款选择2024年规则"], "answer", ["versioning", "cross_border_data", "validity_period"]),
    case(19, "截至2026年，非关基运营者虽然总计处理超过100万人的个人信息，但当年仅向境外提供5万人的非敏感个人信息、不含重要数据且无其他特殊情形，仅因总处理量大是否必须申报安全评估？", "version_conflict", "high", True,
         "不必须。2024年规定下，非关基运营者当年累计出境不满10万人非敏感个人信息且不含重要数据的，可免予安全评估、标准合同和认证；安全评估的现行数量门槛主要看当年出境达到100万人非敏感个人信息或1万人敏感个人信息。旧办法中“处理100万人以上”的触发规则与新规定不一致时，适用新规定。",
         ["不因总处理量超过100万人单独触发", "核对当年出境少于10万人、非敏感且不含重要数据", "说明现行安全评估出境阈值", "说明新旧不一致适用2024年规定"],
         ["沿用旧规则直接判定必须评估", "声称免除所有个人信息保护义务"],
         [ev("cn-cross-border-data-flow-provisions-2024", "第五条", "不满10万人个人信息"), ev("cn-cross-border-data-flow-provisions-2024", "第七条", "100万人以上个人信息"), ev("cn-cross-border-data-flow-provisions-2024", "第十三条", "适用本规定")],
         ["先使用2026年有效规则", "核对主体、出境数量、敏感性和重要数据", "通过冲突条款排除旧触发条件"], "answer", ["versioning", "cross_border_data", "threshold"]),
    case(20, "如果基准日是2023年12月31日，某非关基数据处理者已处理超过100万人的个人信息，拟向境外提供5万人的非敏感个人信息，按当时规则是否需要申报数据出境安全评估？", "version_conflict", "high", True,
         "需要。按2023年12月31日当时有效的《数据出境安全评估办法》第四条，处理100万人以上个人信息的数据处理者向境外提供个人信息即属于应申报情形。不能把2024年发布的后续规定倒用于该历史时点。",
         ["以2023年12月31日为判断时点", "适用当时的处理100万人以上触发条件", "结论为需要申报", "不倒用2024年规则"],
         ["使用2024年规定得出历史时点无需申报", "只看5万人出境数量而忽略当时的总处理量触发项"],
         [ev("cn-data-export-security-assessment-measures-2022", "第四条", "处理100万人以上个人信息")],
         ["固定历史基准日", "选择该时点有效规则", "核对总处理人数触发项"], "answer", ["versioning", "historical_time", "security_assessment"], as_of_date="2023-12-31"),

    case(21, "按照欧盟 GDPR，个人数据泄露必须在多少小时内通知监管机构？", "knowledge_missing", "high", False,
         "当前知识库仅覆盖中国大陆 P0 法规，未收录欧盟 GDPR 正文，无法据此确认通知时限。应补充并核验 GDPR 的现行官方文本后回答。",
         ["明确当前知识库不含欧盟 GDPR", "不猜测具体小时数", "说明需要补充现行官方文本"],
         ["直接给出具体小时数", "把中国大陆规则冒充为欧盟规则"], [],
         ["判断适用地区为欧盟而非中国大陆", "检查其不在当前 P0 语料范围", "拒绝给出无证据结论"], "refuse", ["out_of_scope", "gdpr"]),
    case(22, "我们公司员工离职后，门禁记录的内部保留期限具体是多少个月？", "knowledge_missing", "medium", False,
         "当前知识库不包含贵公司的内部数据保留制度，无法确定具体月数。需要提供适用的公司制度、劳动管理规则或该系统的数据保留配置，并结合相关法律要求判断。",
         ["明确缺少公司内部制度", "不编造具体期限", "指出需要补充的内部资料"],
         ["编造固定月数", "声称 P0 法规已规定公司门禁记录的统一保留期"], [],
         ["识别问题依赖企业内部规则", "确认公司制度不在首轮语料", "拒答并列明所需资料"], "refuse", ["out_of_scope", "company_policy", "retention"]),
    case(23, "项目 Alpha 与境外供应商签订的合同是否允许其把用户数据转给分包商？", "knowledge_missing", "high", False,
         "当前知识库没有项目 Alpha 的合同及分包条款，无法判断是否允许转交。需要提供合同正文、数据处理附件、分包商清单和适用的出境安排后再审查。",
         ["明确缺少项目合同", "不推定允许或禁止", "列出判断所需的关键材料"],
         ["在未见合同的情况下断言允许", "在未见合同的情况下断言绝对禁止"], [],
         ["识别问题取决于项目事实和合同约定", "确认项目材料不在 P0", "拒答并请求必要材料"], "refuse", ["out_of_scope", "project_contract", "subprocessor"]),
    case(24, "加利福尼亚州消费者隐私法对出售个人信息的选择退出权有哪些具体要求？", "knowledge_missing", "medium", False,
         "当前知识库只覆盖中国大陆 P0 法规，未收录加利福尼亚州相关法律的现行文本，无法给出可靠的具体要求。应补充对应法域的官方现行法规后回答。",
         ["明确超出中国大陆范围", "不根据常识补答具体要求", "要求补充官方现行文本"],
         ["直接列举美国州法义务", "将中国大陆个人信息保护法当作其依据"], [],
         ["识别适用法域不在范围内", "检查当前语料无对应文本", "正确拒答"], "refuse", ["out_of_scope", "ccpa"]),

    case(25, "处理个人信息是不是任何情况下都必须先取得个人同意？", "ambiguity_false_premise", "high", True,
         "不是。个人同意只是合法处理依据之一。为订立或履行个人作为一方的合同所必需、依法实施必要的人力资源管理、履行法定职责或义务、应对紧急情况、在合理范围内为公共利益开展新闻报道或处理已合法公开信息，以及法律行政法规规定的其他情形，可以不取得个人同意；仍须满足对应条件和其他法定义务。",
         ["纠正任何情况下都需同意的前提", "说明同意是多种合法依据之一", "概括法定非同意依据", "强调仍需满足具体条件和其他义务"],
         ["声称只要企业认为必要即可不经同意", "声称个人信息处理完全不需要同意"],
         [ev("cn-pipl-2021", "第十三条", "不需取得个人同意")],
         ["识别绝对化错误前提", "引用处理依据的完整结构", "给出带条件的纠正"], "correct_premise", ["false_premise", "consent", "lawful_basis"]),
    case(26, "个人信息只要出境，就一律必须申报国家网信部门安全评估，对吗？", "ambiguity_false_premise", "high", True,
         "不对。个人信息出境可能通过安全评估、个人信息保护认证、标准合同或其他法定条件实现；2024年规定还针对特定合同履行、跨境人力资源、紧急情况和一定规模的小量非敏感个人信息等设置豁免。是否需要安全评估要结合是否为关基运营者、是否含重要数据、出境人数、是否含敏感个人信息及是否适用豁免判断。",
         ["明确纠正一律安全评估", "列出个人信息保护法规定的多种机制", "指出2024年规定存在豁免", "列出决定性判断因素"],
         ["声称取得单独同意即可满足所有出境要求", "声称任何出境都无需安全评估"],
         [ev("cn-pipl-2021", "第三十八条", "应当具备下列条件之一"), ev("cn-cross-border-data-flow-provisions-2024", "第五条", "免予申报数据出境安全评估")],
         ["识别一律二字形成的错误前提", "组合一般出境机制与后续豁免规则", "说明需要事实条件才能选路"], "correct_premise", ["false_premise", "cross_border_data", "security_assessment"]),
    case(27, "我们今年准备向境外提供20万人的个人信息，需要申报安全评估吗？", "ambiguity_false_premise", "high", False,
         "仅凭20万人这一信息无法判断。至少需要确认：是否为关键信息基础设施运营者；数据是否含重要数据；20万人中是否包含敏感个人信息及其人数；是否属于合同履行、跨境人力资源、紧急保护等豁免；统计是否为自当年1月1日起累计。若为非关基、无重要数据、20万均为非敏感且无豁免，通常落入标准合同或认证区间，而非安全评估。",
         ["明确当前信息不足", "询问主体、重要数据、敏感信息人数、豁免和累计期间", "仅在明确假设下说明可能落入标准合同或认证区间"],
         ["只看20万人就直接断言必须安全评估", "忽略敏感个人信息1万人阈值", "忽略关基和重要数据"],
         [ev("cn-cross-border-data-flow-provisions-2024", "第七条", "1万人以上敏感个人信息"), ev("cn-cross-border-data-flow-provisions-2024", "第八条", "不满1万人敏感个人信息")],
         ["识别决定性事实缺失", "列出需要澄清的条件", "在清晰假设下给出非最终判断"], "clarify", ["ambiguity", "cross_border_data", "threshold"]),
    case(28, "用户不同意提供与基本功能无关的个人信息，App 就有权拒绝其使用基本功能，对吗？", "ambiguity_false_premise", "medium", True,
         "不对。App 不得因为用户不同意提供非必要个人信息而拒绝其使用基本功能服务；因用户拒绝非必要个人信息或非必要权限而拒绝提供业务功能，也可被认定为违反必要原则。",
         ["纠正 App 有权拒绝的错误前提", "说明不得因拒绝非必要信息而阻断基本功能", "指出该行为可能被认定为违反必要原则"],
         ["声称隐私政策勾选后即可强制收集非必要信息", "把新增可选功能与基本功能混为一谈"],
         [ev("cn-app-necessary-pi-scope-provisions-2021", "第四条", "不得因为用户不同意提供非必要个人信息"), ev("cn-app-illegal-pi-identification-method-2019", None, "拒绝提供业务功能")],
         ["识别非必要信息与基本功能的关系", "组合必要信息范围规定和违法违规认定方法", "纠正错误前提"], "correct_premise", ["false_premise", "app", "necessary_information"]),
]


def normalize(text: str) -> str:
    return "".join(text.split())


def load_chunks() -> list[dict]:
    return [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line.strip()]


def resolve_evidence(ref: dict, chunks: list[dict]) -> dict:
    candidates = [
        item for item in chunks
        if item["document_id"] == ref["document_id"]
        and item.get("article") == ref["article"]
        and normalize(ref["contains"]) in normalize(item["text"])
    ]
    if len(candidates) != 1:
        raise ValueError(f"Evidence selector must match exactly once: {ref!r}; matched {len(candidates)}")
    item = candidates[0]
    return {
        "document_id": item["document_id"],
        "title": item["title"],
        "article": item.get("article"),
        "source_artifact": item["source_artifact"],
        "source_sha256": item["source_sha256"],
        "source_url": item["source_url"],
        "quote": item["text"],
    }


def build() -> list[dict]:
    chunks = load_chunks()
    result = []
    for spec in SPECS:
        item = dict(spec)
        refs = item.pop("evidence_refs")
        item["evidence"] = [resolve_evidence(ref, chunks) for ref in refs]
        # Restore schema field order around evidence for readable JSONL diffs.
        ordered = {}
        for key in (
            "schema_version", "case_id", "question", "question_type", "risk_level",
            "answerable", "gold_answer", "required_claims", "forbidden_claims"
        ):
            ordered[key] = item[key]
        ordered["evidence"] = item["evidence"]
        for key in ("reasoning_outline", "expected_behavior", "as_of_date", "tags", "split", "review_status", "review_note"):
            ordered[key] = item[key]
        result.append(ordered)
    return result


def write_review(cases: list[dict]) -> None:
    lines = [
        "# 首批评测题审核表",
        "",
        "> 状态：待项目负责人审核",
        ">",
        "> 数据源：`data/evaluation/pilot-cases.jsonl`（自动生成，请勿直接编辑）",
        "",
        "审核时重点检查问题口径、标准答案、必含要点、禁答项和证据。确认后再把结构化数据中的 `review_status` 批量冻结为 `approved`。",
        "",
    ]
    for item in cases:
        lines.extend([
            f"## {item['case_id']} · {item['question_type']} · {item['risk_level']}",
            "",
            f"**问题：** {item['question']}",
            "",
            f"**标准答案：** {item['gold_answer']}",
            "",
            "**必含要点：**",
            "",
            *[f"- {claim}" for claim in item["required_claims"]],
            "",
            "**禁答项：**",
            "",
            *([f"- {claim}" for claim in item["forbidden_claims"]] or ["- 无"]),
            "",
            "**证据：**",
            "",
        ])
        if item["evidence"]:
            for evidence in item["evidence"]:
                article = evidence["article"] or "文首/非条款结构"
                lines.append(f"- 《{evidence['title']}》{article}：{evidence['quote']}")
        else:
            lines.append("- 当前 P0 语料无支持证据，期望拒答。")
        lines.extend(["", "**审核结论：** 待审核", ""])
    REVIEW.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    cases = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in cases), encoding="utf-8")
    write_review(cases)
    print(f"wrote {len(cases)} cases to {OUTPUT.relative_to(ROOT)}")
    print(f"wrote review document to {REVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
