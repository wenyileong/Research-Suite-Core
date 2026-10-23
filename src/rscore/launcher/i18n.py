"""Interface text in English (British) and Simplified Chinese.

To add a language, add a dictionary with every key of ``EN`` (and every reason in ``REASONS_EN``) and
list its code in ``rscore.launcher.tools.LANGUAGES``. Tests check that every language has every key with
the same placeholders, and that every key the window uses exists.
"""

from __future__ import annotations

_TABLES_EN = {
    "entities": "Entities", "ownership": "Ownership and control", "entity_financials": "Revenue",
    "sources": "Sources", "jurisdictions": "Jurisdictions", "jurisdiction_aliases": "Place-name aliases",
    "jurisdiction_attributes": "Jurisdiction data", "flows": "Flows", "instruments": "Treaties and laws",
    "instrument_parties": "Treaty parties", "provisions": "Provisions", "regime_values": "Coded rules",
    "authorities": "Cases and rulings", "propositions": "Legal propositions",
    "proposition_links": "Proposition links",
    "ownership_observations": "Shareholders", "subsidiary_observations": "Subsidiaries",
    "control_observations": "Controlling shareholders", "control_edges": "Control chains",
    "financial_facts": "Financial figures",
}
_TABLES_ZH = {
    "entities": "主体", "ownership": "持股与控制", "entity_financials": "营业收入", "sources": "来源",
    "jurisdictions": "法域", "jurisdiction_aliases": "地名别称", "jurisdiction_attributes": "法域数据",
    "flows": "资金流", "instruments": "条约与法律", "instrument_parties": "条约缔约方", "provisions": "条款",
    "regime_values": "规则编码", "authorities": "判例与裁定", "propositions": "法律命题",
    "proposition_links": "命题关联",
    "ownership_observations": "股东", "subsidiary_observations": "子公司", "control_observations": "控股股东",
    "control_edges": "控制链", "financial_facts": "财务数据",
}
_DESC_EN = {
    "entities": "Companies and other legal persons, each with its jurisdiction",
    "ownership": "Who holds or controls whom, with the stake and its source",
    "entity_financials": "Annual revenue by company and year",
    "sources": "Every document or dataset a value came from, with its terms",
    "jurisdictions": "ISO 3166 territories and special cases (Hong Kong, the Crown Dependencies, the EU)",
    "instruments": "Treaties, the MLI, statutes and guidance (for the treaty module)",
    "provisions": "Pinpointed articles and sections (for the treaty module)",
    "regime_values": "Coded tax rules by jurisdiction and date (for the Rule Bench link)",
    "authorities": "Cases, rulings and official guidance",
    "propositions": "Legal claims the software relies on, with their support",
}
_DESC_ZH = {
    "entities": "公司及其他法人，各附所属法域",
    "ownership": "谁持有或控制谁，附持股比例及来源",
    "entity_financials": "按公司和年度的营业收入",
    "sources": "每个数值所出自的文件或数据集，附使用条款",
    "jurisdictions": "ISO 3166 地区及特殊情形（香港、英国皇家属地、欧盟）",
    "instruments": "条约、多边公约、法律与指引（供条约模块使用）",
    "provisions": "精确到条款的规定（供条约模块使用）",
    "regime_values": "按法域和日期编码的税收规则（供规则工作台对接）",
    "authorities": "判例、裁定与官方指引",
    "propositions": "软件所依据的法律命题及其依据",
}

EN = {
    "app_title": "Research Suite",
    "switch_language": "中文",
    "about": "About",
    "error": "Error",
    "footer": "Core {version} · data model generation {generation}",
    "about_text": (
        "Research Suite {version}\n\n"
        "A workspace for the suite's tools and its shared data: import A-share releases, review what needs "
        "a decision, browse the data with its sources, send it to the Lab and freeze snapshots for papers.\n\n"
        "Copyright (c) 2026 Leong, Wen Yi. No licence is granted at present: see LICENSE.\n"
        "Third-party components: see THIRD_PARTY_NOTICES.txt."
    ),
    # navigation, titles and introductions
    "nav_tools": "Tools", "nav_project": "Project", "nav_import": "Import", "nav_review": "Review",
    "nav_data": "Data", "nav_lab": "Lab and snapshots", "nav_check": "Check",
    "title_tools": "Tools", "intro_tools": "Open the suite's tools, or follow the four steps to bring A-share data into the Lab.",
    "title_project": "Project", "intro_project": "A project is one file holding all the data for a study. Its reports, choices and exports are kept in a folder beside it.",
    "title_import": "Import an A-share release", "intro_import": "Bring a release made by A-share Company Intelligence into the project. Rows that look misparsed are set aside with a reason, and natural persons are never imported.",
    "title_review": "Review", "intro_review": "Decide what the import could not: which jurisdiction a holder or place belongs to. Revenue figures that disagree are listed for correction in A-share Company Intelligence.",
    "title_data": "Data", "intro_data": "Browse what the project holds. Every row rests on a source: double-click it to open the document.",
    "title_lab": "Lab and snapshots", "intro_lab": "Send the project's data to the International Tax Network Lab, and freeze verifiable snapshots to cite in papers.",
    "title_check": "Check", "intro_check": "Re-check the whole project: broken links, stakes summing above 100%, ownership cycles and rows that no longer validate.",
    # project in the sidebar
    "project_open": "Project: {name}", "project_none": "No project open",
    "no_project_title": "No project open", "no_project_body": "This needs a project. Create or open one now?",
    # tools page
    "guide_title": "Getting started",
    "step_project": "Create or open a project", "step_import": "Import an A-share release",
    "step_review": "Review what needs a decision", "step_review_left": " ({n} waiting)",
    "step_lab": "Export the data for the Lab", "go": "Go",
    "ashare_name": "A-share Company Intelligence",
    "ashare_desc": "Firm-level data on Chinese listed groups: shareholders, subsidiaries and control, with sources.",
    "lab_name": "International Tax Network Lab",
    "lab_desc": "Network analysis of international tax: tax routing, conduits and sinks, topological data analysis.",
    "rulebench_name": "JAF Rule Bench",
    "rulebench_desc": "Coding and testing of jurisdictional assignment rules across countries.",
    "open": "Open", "locate": "Locate…",
    "status_ready": "Ready: {path}",
    "status_missing": "Not found. Install the tool, or use Locate to choose its program file.",
    "locate_title": "Choose the program file for {name}", "programs": "Programs",
    "not_a_program": "That file is not a program the launcher can open. On Windows, choose the tool's .exe file.",
    "launch_failed": "Could not open {name}:\n{error}", "started": "Started {name}.",
    "saved": "Saved the location of {name}.",
    # project page
    "new_project": "New project…", "open_project": "Open project…", "open_folder": "Open folder",
    "project_path": "Open project: {path}",
    "project_none_long": "No project is open. Create a new project, or open an existing one.",
    "recent": "Recent projects", "project_contents": "What the project holds",
    "project_files": "Research Suite projects", "project_created": "Created project {name}.",
    "project_opened": "Opened project {name}.", "project_open_failed": "Could not open the project:\n{error}",
    # import page
    "release_folder": "Release folder", "browse": "Browse…",
    "use_example": "No release to hand? Try the invented example data",
    "example_ready": "Example release ready. Its companies and figures are invented.",
    "options": "Options",
    "opt_assume": "Treat revenue with no stated scope as consolidated",
    "opt_assume_help": "Figures read from PDFs do not say whether they are consolidated. Tick this only if you accept that assumption; the report records it.",
    "opt_accept": "Accept jurisdictions suggested from holders' names without review",
    "opt_accept_help": "Faster, but a name is weak evidence of where a company is incorporated. Usually better left unticked.",
    "opt_companies": "Only these companies", "opt_companies_help": "security codes, separated by commas; empty for all",
    "start_import": "Import", "not_a_release": "{folder} is not an A-share release folder: it has no manifest.json.",
    "progress_reading": "Reading the release…", "progress_importing": "Importing…",
    "progress_writing_report": "Writing the report…",
    "import_done": "Import finished: {n} rows added to the project.",
    "import_failed": "The import failed:\n{error}", "import_failed_short": "The import failed.",
    "result_title": "Last import: {release}", "open_report_folder": "Open report folder",
    "stat_entities": "entities", "stat_relations": "ownership and control relations",
    "stat_revenue": "revenue figures", "stat_rejected": "rows set aside",
    "go_review": "Review {n} item(s)",
    "col_from": "From", "col_reason": "Why it was set aside", "col_rows": "Rows",
    # review page
    "tab_jurisdictions": "Jurisdictions", "tab_revenue": "Revenue conflicts",
    "review_nothing": "Nothing to review yet: import a release first.",
    "review_clear": "Nothing waiting: the last import needed no decisions.",
    "review_from": "From the import {report}.",
    "review_j_help": "Choose a jurisdiction for each line, then save and import again. Double-click a line to accept its suggestion. Your choices are kept in the project and used by every later import.",
    "review_r_help": "These revenue figures disagree with each other, usually because of a scale or digit error in the scraper. None of them was imported. Correct them in A-share Company Intelligence's review, then make a new release.",
    "col_name": "Name or place", "col_problem": "Problem", "col_suggested": "Suggested", "col_choice": "Your choice",
    "col_code": "Security code", "col_year": "Year", "col_candidates": "Figures found (yuan)",
    "problem_holder": "Jurisdiction not stated", "problem_place_unmatched": "Place not recognised",
    "problem_place_ambiguous": "Place is ambiguous", "problem_place_missing": "No place given",
    "problem_place_empty": "No place given",
    "not_chosen": "not chosen", "choose_for": "Jurisdiction:",
    "apply": "Apply", "use_suggestion": "Use suggestion", "clear": "Clear",
    "use_all_suggestions": "Use all suggestions", "save_and_reimport": "Save choices and import again",
    "bad_code": "{code} is not a jurisdiction code.", "choices_saved": "Choices saved to the project.",
    "reimported": "Saved {n} choice(s) and imported again.",
    # data page
    "search": "Search", "search_go": "Search", "open_source": "Open source document",
    "tab_ownership": "Ownership and control", "tab_revenue_data": "Revenue",
    "col_holder": "Holder", "col_j": "Jur.", "col_type": "Type", "col_stake": "Stake", "col_held": "Held",
    "col_date": "From", "col_entity": "Company", "col_revenue": "Revenue", "col_basis": "Basis",
    "rel_equity": "equity", "rel_control": "control", "rel_voting": "voting", "rel_economic_interest": "economic",
    "basis_consolidated": "consolidated", "basis_unconsolidated": "unconsolidated",
    "basis_deconsolidated": "deconsolidated",
    "rows_shown": "{n} row(s)", "source_hint": "double-click a row to open its source",
    "select_row_first": "Select a row first.", "no_source_url": "This row's source has no web address.",
    # lab page
    "lab_section": "International Tax Network Lab",
    "lab_help": "Writes the project's sources, jurisdictions, entities, ownership and revenue in the Lab's own format, then opens the folder. In the Lab, import that folder as a dataset.",
    "export_lab": "Export for the Lab", "open_lab": "Open the Lab",
    "lab_written": "Written to {path}", "lab_done": "Exported for the Lab.",
    "lab_not_found": "The Lab was not found on this computer: install it, or use Locate on the Tools page.",
    "snap_section": "Snapshots",
    "snap_help": "A snapshot freezes the project's data with a fingerprint for every table, so a figure in a paper can be regenerated from exactly the same data. Verify checks that a snapshot's files have not changed since.",
    "snap_note": "Note", "take_snapshot": "Take snapshot", "verify_snapshot": "Verify selected",
    "col_when": "Taken (UTC)", "col_id": "Fingerprint", "col_note": "Note",
    "snapshot_done": "Snapshot {id}… taken.", "snapshot_intact": "The snapshot is intact: no file has changed.",
    "snapshot_changed": "The snapshot has changed since it was taken:",
    # check page
    "run_check": "Run check", "check_clean": "No problems found.",
    "check_warnings": "No errors; {n} warning(s) to look at.", "check_errors": "{n} error(s) found.",
    "col_level": "Level", "col_table": "Table", "col_where": "Row", "col_message": "Problem", "col_about": "What it holds",
    "level_error": "Error", "level_warning": "Warning",
}
EN.update({f"table_{k}": v for k, v in _TABLES_EN.items()})
EN.update({f"tabledesc_{k}": v for k, v in _DESC_EN.items()})

ZH_HANS = {
    "app_title": "研究工具套件",
    "switch_language": "English",
    "about": "关于",
    "error": "错误",
    "footer": "核心 {version} · 数据模型第 {generation} 代",
    "about_text": (
        "研究工具套件 {version}\n\n"
        "套件各工具及其共享数据的工作台：导入A股数据发布、处理待决事项、连同来源浏览数据、发送至实验室，"
        "并为论文固定快照。\n\n"
        "版权所有 (c) 2026 Leong, Wen Yi。目前未授予任何许可：见 LICENSE。\n"
        "第三方组件：见 THIRD_PARTY_NOTICES.txt。"
    ),
    "nav_tools": "工具", "nav_project": "项目", "nav_import": "导入", "nav_review": "审核",
    "nav_data": "数据", "nav_lab": "实验室与快照", "nav_check": "检查",
    "title_tools": "工具", "intro_tools": "打开套件中的工具，或按四个步骤把A股数据导入实验室。",
    "title_project": "项目", "intro_project": "一个项目就是保存一项研究全部数据的一个文件。其报告、选择和导出文件保存在旁边的文件夹中。",
    "title_import": "导入A股数据发布", "intro_import": "把A股公司情报生成的数据发布导入项目。疑似解析错误的行会连同原因被搁置，自然人一律不导入。",
    "title_review": "审核", "intro_review": "处理导入无法自行决定的事项：股东或地点属于哪个法域。相互矛盾的营业收入数值会列出，供在A股公司情报中更正。",
    "title_data": "数据", "intro_data": "浏览项目中的数据。每一行都有来源：双击即可打开原始文件。",
    "title_lab": "实验室与快照", "intro_lab": "把项目数据发送到国际税收网络实验室，并固定可验证的快照以便在论文中引用。",
    "title_check": "检查", "intro_check": "重新检查整个项目：失效的关联、合计超过100%的持股、循环持股，以及不再通过校验的行。",
    "project_open": "项目：{name}", "project_none": "未打开项目",
    "no_project_title": "未打开项目", "no_project_body": "此操作需要项目。现在新建或打开一个吗？",
    "guide_title": "入门",
    "step_project": "新建或打开项目", "step_import": "导入A股数据发布", "step_review": "处理待决事项",
    "step_review_left": "（{n} 项待处理）", "step_lab": "导出数据供实验室使用", "go": "前往",
    "ashare_name": "A股公司情报",
    "ashare_desc": "中国上市公司集团的企业层面数据：股东、子公司与控制关系，附来源。",
    "lab_name": "国际税收网络实验室",
    "lab_desc": "国际税收的网络分析：税收路由、通道与汇点、拓扑数据分析。",
    "rulebench_name": "JAF 规则工作台",
    "rulebench_desc": "各国管辖权分配规则的编码与检验。",
    "open": "打开", "locate": "定位…",
    "status_ready": "就绪：{path}",
    "status_missing": "未找到。请安装该工具，或点击“定位”选择其程序文件。",
    "locate_title": "选择 {name} 的程序文件", "programs": "程序",
    "not_a_program": "该文件不是启动器可以打开的程序。在 Windows 上，请选择该工具的 .exe 文件。",
    "launch_failed": "无法打开 {name}：\n{error}", "started": "已启动 {name}。",
    "saved": "已保存 {name} 的位置。",
    "new_project": "新建项目…", "open_project": "打开项目…", "open_folder": "打开文件夹",
    "project_path": "当前项目：{path}",
    "project_none_long": "尚未打开项目。请新建项目或打开已有项目。",
    "recent": "最近的项目", "project_contents": "项目中的数据",
    "project_files": "研究工具套件项目", "project_created": "已新建项目 {name}。",
    "project_opened": "已打开项目 {name}。", "project_open_failed": "无法打开项目：\n{error}",
    "release_folder": "数据发布文件夹", "browse": "浏览…",
    "use_example": "手头没有数据发布？试用虚构的示例数据",
    "example_ready": "示例数据发布已就绪。其中的公司和数字均为虚构。",
    "options": "选项",
    "opt_assume": "将未注明范围的营业收入视为合并口径",
    "opt_assume_help": "从PDF读取的数字未注明是否为合并报表口径。只有在接受这一假设时才勾选；报告会记录该假设。",
    "opt_accept": "直接采用根据股东名称推断的法域，不经审核",
    "opt_accept_help": "较快，但名称并不能可靠说明公司的注册地。通常不建议勾选。",
    "opt_companies": "仅导入这些公司", "opt_companies_help": "证券代码，以逗号分隔；留空则导入全部",
    "start_import": "导入", "not_a_release": "{folder} 不是A股数据发布文件夹：其中没有 manifest.json。",
    "progress_reading": "正在读取数据发布…", "progress_importing": "正在导入…",
    "progress_writing_report": "正在生成报告…",
    "import_done": "导入完成：项目新增 {n} 行。",
    "import_failed": "导入失败：\n{error}", "import_failed_short": "导入失败。",
    "result_title": "上次导入：{release}", "open_report_folder": "打开报告文件夹",
    "stat_entities": "个主体", "stat_relations": "条持股与控制关系",
    "stat_revenue": "个营业收入数值", "stat_rejected": "行被搁置",
    "go_review": "处理 {n} 项",
    "col_from": "来自", "col_reason": "搁置原因", "col_rows": "行数",
    "tab_jurisdictions": "法域", "tab_revenue": "营业收入冲突",
    "review_nothing": "暂无待处理事项：请先导入数据发布。",
    "review_clear": "没有待处理事项：上次导入无需任何决定。",
    "review_from": "来自导入 {report}。",
    "review_j_help": "为每一行选择法域，然后保存并重新导入。双击某行即可采用建议。您的选择保存在项目中，之后每次导入都会使用。",
    "review_r_help": "这些营业收入数值彼此矛盾，通常是爬虫的单位或数字错误所致。其中任何一个都未被导入。请在A股公司情报的审核中更正，然后重新生成数据发布。",
    "col_name": "名称或地点", "col_problem": "问题", "col_suggested": "建议", "col_choice": "您的选择",
    "col_code": "证券代码", "col_year": "年度", "col_candidates": "发现的数值（元）",
    "problem_holder": "未注明法域", "problem_place_unmatched": "无法识别地点",
    "problem_place_ambiguous": "地点有歧义", "problem_place_missing": "未提供地点",
    "problem_place_empty": "未提供地点",
    "not_chosen": "未选择", "choose_for": "法域：",
    "apply": "应用", "use_suggestion": "采用建议", "clear": "清除",
    "use_all_suggestions": "全部采用建议", "save_and_reimport": "保存选择并重新导入",
    "bad_code": "{code} 不是法域代码。", "choices_saved": "选择已保存到项目。",
    "reimported": "已保存 {n} 项选择并重新导入。",
    "search": "搜索", "search_go": "搜索", "open_source": "打开来源文件",
    "tab_ownership": "持股与控制", "tab_revenue_data": "营业收入",
    "col_holder": "持有方", "col_j": "法域", "col_type": "类型", "col_stake": "比例", "col_held": "被持有方",
    "col_date": "起始", "col_entity": "公司", "col_revenue": "营业收入", "col_basis": "口径",
    "rel_equity": "股权", "rel_control": "控制", "rel_voting": "表决权", "rel_economic_interest": "经济利益",
    "basis_consolidated": "合并", "basis_unconsolidated": "非合并", "basis_deconsolidated": "剔除合并",
    "rows_shown": "{n} 行", "source_hint": "双击某行可打开其来源",
    "select_row_first": "请先选择一行。", "no_source_url": "该行的来源没有网址。",
    "lab_section": "国际税收网络实验室",
    "lab_help": "按实验室的格式写出项目的来源、法域、主体、持股与营业收入，并打开该文件夹。在实验室中将该文件夹作为数据集导入。",
    "export_lab": "导出供实验室使用", "open_lab": "打开实验室",
    "lab_written": "已写入 {path}", "lab_done": "已导出供实验室使用。",
    "lab_not_found": "本机未找到实验室：请安装，或在“工具”页点击“定位”。",
    "snap_section": "快照",
    "snap_help": "快照为每张表记录指纹并固定项目数据，使论文中的图表能够用完全相同的数据重新生成。“验证”可检查快照文件此后是否被改动。",
    "snap_note": "备注", "take_snapshot": "生成快照", "verify_snapshot": "验证所选快照",
    "col_when": "生成时间（UTC）", "col_id": "指纹", "col_note": "备注",
    "snapshot_done": "已生成快照 {id}…。", "snapshot_intact": "快照完好：没有文件被改动。",
    "snapshot_changed": "快照生成后已被改动：",
    "run_check": "运行检查", "check_clean": "未发现问题。",
    "check_warnings": "没有错误；有 {n} 条警告值得查看。", "check_errors": "发现 {n} 个错误。",
    "col_level": "级别", "col_table": "表", "col_where": "行", "col_message": "问题", "col_about": "内容",
    "level_error": "错误", "level_warning": "警告",
}
ZH_HANS.update({f"table_{k}": v for k, v in _TABLES_ZH.items()})
ZH_HANS.update({f"tabledesc_{k}": v for k, v in _DESC_ZH.items()})

#: The importer's rejection reasons, in plain language.
REASONS_EN = {
    "natural_person_excluded": "A natural person: never imported",
    "table_columns_shifted": "The shareholder table's columns were shifted when it was read",
    "stake_missing": "No stake reported", "stake_outside_0_100": "Stake outside 0 to 100%",
    "stakes_sum_over_100": "The table's stakes add up to more than 100%",
    "holder_jurisdiction_needs_review": "Holder's jurisdiction needs your decision",
    "place_unmatched": "Place not recognised: needs your decision",
    "place_ambiguous": "Place is ambiguous: needs your decision", "place_missing": "No place given",
    "no_direct_stake": "No direct stake reported", "indirect_only": "Indirect stake only (not stored)",
    "below_min_confidence": "Below the confidence you set",
    "unknown_jurisdiction_code": "Unknown jurisdiction code",
    "consolidation_scope_not_stated": "Revenue scope (consolidated or not) not stated",
    "revenue_missing_or_negative": "Revenue missing or negative",
    "revenue_implausibly_small": "Revenue implausibly small (under 1 million yuan)",
    "revenue_candidates_disagree": "Revenue figures for the same year disagree",
    "observation_date_missing": "No date given",
}
REASONS_ZH = {
    "natural_person_excluded": "自然人：一律不导入",
    "table_columns_shifted": "读取股东表时列发生错位",
    "stake_missing": "未报告持股比例", "stake_outside_0_100": "持股比例不在0至100%之间",
    "stakes_sum_over_100": "该表持股比例合计超过100%",
    "holder_jurisdiction_needs_review": "股东所属法域需要您决定",
    "place_unmatched": "无法识别地点：需要您决定",
    "place_ambiguous": "地点有歧义：需要您决定", "place_missing": "未提供地点",
    "no_direct_stake": "未报告直接持股", "indirect_only": "仅有间接持股（不保存）",
    "below_min_confidence": "低于您设定的置信度",
    "unknown_jurisdiction_code": "未知的法域代码",
    "consolidation_scope_not_stated": "未注明营业收入口径（是否合并）",
    "revenue_missing_or_negative": "营业收入缺失或为负",
    "revenue_implausibly_small": "营业收入小得不合常理（低于100万元）",
    "revenue_candidates_disagree": "同一年度的营业收入数值相互矛盾",
    "observation_date_missing": "未提供日期",
}

STRINGS = {"en": EN, "zh-Hans": ZH_HANS}
REASONS = {"en": REASONS_EN, "zh-Hans": REASONS_ZH}


def text(language: str, key: str, **values: object) -> str:
    table = STRINGS.get(language, EN)
    return table.get(key, EN.get(key, key)).format(**values)


def reason_text(language: str, reason: str) -> str:
    return REASONS.get(language, REASONS_EN).get(reason, REASONS_EN.get(reason, reason.replace("_", " ")))
