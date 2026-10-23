"""Interface text in English (British) and Simplified Chinese.

To add a language, add a dictionary with every key of ``EN`` and list its code in
``rscore.launcher.tools.LANGUAGES``. A test checks that every language has every key and the same
placeholders.
"""

from __future__ import annotations

EN = {
    "app_title": "Research Suite",
    "subtitle": "Firm, network and regime tools for tax research",
    "switch_language": "中文",
    "ashare_name": "A-share Company Intelligence",
    "ashare_desc": "Firm-level data on Chinese listed groups: shareholders, subsidiaries and control, with sources.",
    "lab_name": "International Tax Network Lab",
    "lab_desc": "Network analysis of international tax: tax routing, conduits and sinks, topological data analysis.",
    "rulebench_name": "JAF Rule Bench",
    "rulebench_desc": "Coding and testing of jurisdictional assignment rules across countries.",
    "open": "Open",
    "locate": "Locate…",
    "status_ready": "Ready: {path}",
    "status_missing": "Not found. Install the tool, or use Locate to choose its program file.",
    "locate_title": "Choose the program file for {name}",
    "programs": "Programs",
    "not_a_program": "That file is not a program the launcher can open. On Windows, choose the tool's .exe file.",
    "launch_failed": "Could not open {name}:\n{error}",
    "started": "Started {name}.",
    "saved": "Saved the location of {name}.",
    "settings": "Settings folder",
    "about": "About",
    "footer": "Core {version} · data model generation {generation}",
    "about_text": (
        "Research Suite launcher {version}\n\n"
        "Opens the suite's tools from one place. Each tool is a separate program with its own licence; "
        "the launcher only starts it.\n\n"
        "Copyright (c) 2026 Leong, Wen Yi. No licence is granted at present: see LICENSE.\n"
        "Third-party components: see THIRD_PARTY_NOTICES.txt."
    ),
    "error": "Error",
}

ZH_HANS = {
    "app_title": "研究工具套件",
    "subtitle": "面向税收研究的企业、网络与制度工具",
    "switch_language": "English",
    "ashare_name": "A股公司情报",
    "ashare_desc": "中国上市公司集团的企业层面数据：股东、子公司与控制关系，附来源。",
    "lab_name": "国际税收网络实验室",
    "lab_desc": "国际税收的网络分析：税收路由、通道与汇点、拓扑数据分析。",
    "rulebench_name": "JAF 规则工作台",
    "rulebench_desc": "各国管辖权分配规则的编码与检验。",
    "open": "打开",
    "locate": "定位…",
    "status_ready": "就绪：{path}",
    "status_missing": "未找到。请安装该工具，或点击“定位”选择其程序文件。",
    "locate_title": "选择 {name} 的程序文件",
    "programs": "程序",
    "not_a_program": "该文件不是启动器可以打开的程序。在 Windows 上，请选择该工具的 .exe 文件。",
    "launch_failed": "无法打开 {name}：\n{error}",
    "started": "已启动 {name}。",
    "saved": "已保存 {name} 的位置。",
    "settings": "设置文件夹",
    "about": "关于",
    "footer": "核心 {version} · 数据模型第 {generation} 代",
    "about_text": (
        "研究工具套件启动器 {version}\n\n"
        "在同一处打开套件中的各个工具。每个工具都是独立的程序，各有其许可；启动器只负责启动。\n\n"
        "版权所有 (c) 2026 Leong, Wen Yi。目前未授予任何许可：见 LICENSE。\n"
        "第三方组件：见 THIRD_PARTY_NOTICES.txt。"
    ),
    "error": "错误",
}

STRINGS = {"en": EN, "zh-Hans": ZH_HANS}


def text(language: str, key: str, **values: object) -> str:
    table = STRINGS.get(language, EN)
    return table.get(key, EN[key]).format(**values)
