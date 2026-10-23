"""The Research Suite window (tkinter, part of Python's standard library).

A sidebar leads to one page per task. Every page opens with a line saying what it is for, and the Tools
page carries a four-step guide (project, import, review, Lab) that ticks itself off as the work is done.
Every command of ``python -m rscore`` has an action here (``GUI_ACTIONS``; checked by a test), and both
call the same functions in ``rscore.services``.

Colours follow the International Tax Network Lab's interface; each tool keeps its colour from the icon.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from importlib import resources
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rscore import SCHEMA_GENERATION, __version__, demo, services
from rscore.launcher import tools as tl
from rscore.launcher.i18n import reason_text, text

BG, SURFACE, INK, MUTED, LINE = "#FAFAFB", "#FFFFFF", "#1C1F2A", "#6B7280", "#E7E8EC"
ACCENT, ACCENT_DARK, ACCENT_SOFT = "#4F46E5", "#4338CA", "#EEF0FF"
OK, WARN, ERROR, DISABLED = "#059669", "#B45309", "#DC2626", "#C7C9D1"
SIDEBAR = "#F1F2F6"

FONTS = {
    "en": ("Segoe UI", "Noto Sans", "DejaVu Sans", "Helvetica"),
    "zh-Hans": ("Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans CJK TC", "PingFang SC"),
}

#: Pages in sidebar order: (key, page class name).
PAGES = ("tools", "project", "import", "review", "data", "lab", "check")

#: Each command of ``python -m rscore`` and the page and method that offer it in the window.
GUI_ACTIONS = {
    "import-ashare": ("import", "start_import"),
    "export-lab": ("lab", "export_lab"),
    "snapshot": ("lab", "take_snapshot"),
    "validate": ("check", "run_check"),
}


def _asset(name: str) -> str:
    return str(resources.files("rscore.launcher").joinpath("assets", name))


def _shorten(path: str, limit: int = 60) -> str:
    if len(path) <= limit:
        return path
    keep = (limit - 1) // 2
    return path[:keep] + "…" + path[-keep:]


def _open_folder(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(folder)  # type: ignore[attr-defined]
    else:
        try:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])
        except OSError:
            pass


# ====================================================================== application
class App:
    def __init__(self, root: tk.Tk, config_path: Path, *, base: Path | None = None,
                 local_appdata: Path | None = None, start_page: str = "tools"):
        self.root = root
        self.config_path = config_path
        self.base, self.local_appdata = base, local_appdata
        self.settings = tl.Settings.load(config_path)
        self.project: services.Project | None = None
        if self.settings.project and Path(self.settings.project).exists():
            self.project = services.Project(Path(self.settings.project))
        self.last_report: Path | None = services.latest_report(self.project) if self.project else None
        self.found: dict[str, tl.Found | None] = {}
        self.jobs: "queue.Queue[tuple]" = queue.Queue()
        self._fonts: dict[tuple, tkfont.Font] = {}
        self._families: set[str] | None = None
        self.busy = False
        root.configure(bg=BG)
        root.minsize(980, 640)
        self._icon_big = tk.PhotoImage(file=_asset("icon_256.png"))
        self._icon_small = tk.PhotoImage(file=_asset("icon_48.png"))
        root.iconphoto(True, self._icon_big)
        self.current = start_page
        self.build()
        root.after(100, self._poll)

    # -------------------------------------------------------------- helpers
    def t(self, key: str, **values: object) -> str:
        return text(self.settings.language, key, **values)

    def font(self, size: float, weight: str = "normal") -> tkfont.Font:
        """A named font, kept for the life of the window (Tk drops a named font once Python lets it go,
        and ttk styles then fall back to the default)."""
        key = (self.settings.language, round(size), weight)
        if key not in self._fonts:
            if self._families is None:
                self._families = set(tkfont.families(self.root))
            family = next((f for f in FONTS[self.settings.language] if f in self._families), "TkDefaultFont")
            self._fonts[key] = tkfont.Font(root=self.root, family=family, size=round(size), weight=weight)
        return self._fonts[key]

    def button(self, parent: tk.Widget, label: str, command, kind: str = "secondary", width: int | None = None):
        primary = kind == "primary"
        b = tk.Button(parent, text=label, command=command, font=self.font(10, "bold" if primary else "normal"),
                      bg=ACCENT if primary else SURFACE, fg="#FFFFFF" if primary else ACCENT,
                      activebackground=ACCENT_DARK if primary else ACCENT_SOFT,
                      activeforeground="#FFFFFF" if primary else ACCENT,
                      disabledforeground="#FFFFFF" if primary else DISABLED, relief="flat", bd=0,
                      highlightthickness=0 if primary else 1, highlightbackground=LINE, padx=14, pady=5,
                      cursor="hand2")
        if width:
            b.configure(width=width)
        return b

    def link(self, parent: tk.Widget, label: str, command, bg: str = BG) -> tk.Label:
        lab = tk.Label(parent, text=label, font=self.font(9), fg=ACCENT, bg=bg, cursor="hand2")
        lab.bind("<Button-1>", lambda _e: command())
        return lab

    def label(self, parent, txt, size=10, weight="normal", fg=INK, bg=BG, wrap=0, **kw) -> tk.Label:
        return tk.Label(parent, text=txt, font=self.font(size, weight), fg=fg, bg=bg, anchor="w", justify="left",
                        wraplength=wrap, **kw)

    def card(self, parent, **pack) -> tk.Frame:
        f = tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, padx=16, pady=12)
        f.pack(**({"fill": "x", "pady": 6} | pack))
        return f

    def tree(self, parent, columns: list[tuple[str, str, int, str]], height: int = 12) -> ttk.Treeview:
        """columns: (id, heading key, width, anchor)."""
        frame = tk.Frame(parent, bg=SURFACE)
        frame.pack(fill="both", expand=True)
        tv = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", height=height,
                          selectmode="browse")
        for cid, key, width, anchor in columns:
            tv.heading(cid, text=self.t(key), anchor="e" if anchor == "e" else "w")
            tv.column(cid, width=width, minwidth=40, anchor=anchor, stretch=width >= 150)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tv.tag_configure("odd", background="#F7F7FA")
        tv.tag_configure("warn", foreground=WARN)
        tv.tag_configure("error", foreground=ERROR)
        tv.tag_configure("done", foreground=OK)
        return tv

    def say(self, message: str, colour: str = MUTED) -> None:
        self.status.configure(text=message, fg=colour)

    def error(self, message: str) -> None:
        messagebox.showerror(self.t("error"), message, parent=self.root)

    def need_project(self) -> bool:
        if self.project is None:
            if messagebox.askyesno(self.t("no_project_title"), self.t("no_project_body"), parent=self.root):
                self.show("project")
            return False
        return True

    # -------------------------------------------------------------- styles and layout
    def _styles(self) -> None:
        st = ttk.Style(self.root)
        if "clam" in st.theme_names():
            st.theme_use("clam")
        f = self.font(10)
        rowheight = 30 if self.settings.language == "zh-Hans" else 26
        st.configure("Treeview", font=f, rowheight=rowheight, background=SURFACE, fieldbackground=SURFACE,
                     foreground=INK, bordercolor=LINE, borderwidth=0)
        st.configure("Treeview.Heading", font=self.font(9, "bold"), background="#F3F4F6", foreground=MUTED,
                     relief="flat", borderwidth=0, padding=(6, 4))
        st.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", INK)])
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", font=self.font(10), padding=(14, 6), background="#ECEDF2", foreground=MUTED)
        st.map("TNotebook.Tab", background=[("selected", SURFACE)], foreground=[("selected", INK)])
        st.configure("TCombobox", padding=4)
        st.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#E5E7EB", bordercolor="#E5E7EB")
        st.configure("TCheckbutton", background=SURFACE, font=f, foreground=INK)
        st.configure("TEntry", font=f)
        st.configure("TEntry", padding=4)
        self.root.option_add("*TCombobox*Listbox.font", f)

    def build(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self.t("app_title"))
        self._styles()
        side = tk.Frame(self.root, bg=SIDEBAR, width=212)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        head = tk.Frame(side, bg=SIDEBAR, padx=16, pady=16)
        head.pack(fill="x")
        tk.Label(head, image=self._icon_small, bg=SIDEBAR).pack(side="left")
        self.label(head, self.t("app_title"), 12, "bold", bg=SIDEBAR, wrap=120).pack(side="left", padx=(10, 0))
        self.nav: dict[str, tk.Label] = {}
        for key in PAGES:
            item = tk.Label(side, text=self.t(f"nav_{key}"), font=self.font(10), bg=SIDEBAR, fg=INK, anchor="w",
                            padx=20, pady=8, cursor="hand2")
            item.pack(fill="x")
            item.bind("<Button-1>", lambda _e, k=key: self.show(k))
            self.nav[key] = item
        bottom = tk.Frame(side, bg=SIDEBAR, padx=16, pady=14)
        bottom.pack(side="bottom", fill="x")
        self.project_label = self.label(bottom, "", 9, fg=MUTED, bg=SIDEBAR, wrap=180)
        self.project_label.pack(fill="x", pady=(0, 8))
        row = tk.Frame(bottom, bg=SIDEBAR)
        row.pack(fill="x")
        self.link(row, self.t("switch_language"), self.switch_language, SIDEBAR).pack(side="left")
        self.link(row, self.t("about"), self.about, SIDEBAR).pack(side="right")

        main = tk.Frame(self.root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.status = self.label(main, self.t("footer", version=__version__, generation=SCHEMA_GENERATION), 9,
                                 fg=MUTED)
        self.status.pack(side="bottom", fill="x", padx=24, pady=(0, 10))
        self.body = tk.Frame(main, bg=BG)
        self.body.pack(fill="both", expand=True, padx=24, pady=(18, 6))
        self.pages: dict[str, Page] = {}
        for key in PAGES:
            page = PAGE_CLASSES[key](self.body, self, key)
            self.pages[key] = page
        self.show(self.current)

    def show(self, key: str) -> None:
        self.current = key
        for k, item in self.nav.items():
            active = k == key
            item.configure(bg=ACCENT_SOFT if active else SIDEBAR, fg=ACCENT if active else INK,
                           font=self.font(10, "bold" if active else "normal"))
        for page in self.pages.values():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self.update_project_label()
        self.pages[key].on_show()

    def update_project_label(self) -> None:
        if self.project:
            self.project_label.configure(text=self.t("project_open", name=self.project.name))
        else:
            self.project_label.configure(text=self.t("project_none"))

    # -------------------------------------------------------------- shared actions
    def set_project(self, project: services.Project) -> None:
        self.project = project
        self.last_report = services.latest_report(project)
        self.settings.remember_project(str(project.path))
        self.settings.save(self.config_path)
        self.update_project_label()

    def switch_language(self) -> None:
        langs = tl.LANGUAGES
        self.settings.language = langs[(langs.index(self.settings.language) + 1) % len(langs)]
        self.settings.save(self.config_path)
        self.build()

    def about(self) -> None:
        messagebox.showinfo(self.t("about"), self.t("about_text", version=__version__), parent=self.root)

    # -------------------------------------------------------------- background work
    def run_in_background(self, work, done, progress_key: str) -> None:
        """Run ``work(progress)`` off the window's thread; ``done(result_or_exception)`` runs on it."""
        if self.busy:
            return
        self.busy = True

        def target():
            try:
                result = work(lambda m: self.jobs.put(("progress", m)))
            except Exception as exc:  # reported in the window, never lost
                result = exc
            self.jobs.put(("done", done, result))

        self.say(self.t(progress_key), ACCENT)
        threading.Thread(target=target, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                item = self.jobs.get_nowait()
                if item[0] == "progress":
                    self.say(self.t("progress_" + item[1].replace(" ", "_")), ACCENT)
                else:
                    self.busy = False
                    item[1](item[2])
        except queue.Empty:
            pass
        try:
            self.root.after(150, self._poll)
        except tk.TclError:
            pass


# ====================================================================== pages
class Page(tk.Frame):
    def __init__(self, parent: tk.Widget, app: App, key: str):
        super().__init__(parent, bg=BG)
        self.app, self.key = app, key
        app.label(self, app.t(f"title_{key}"), 17, "bold").pack(fill="x")
        app.label(self, app.t(f"intro_{key}"), 10, fg=MUTED, wrap=720).pack(fill="x", pady=(2, 12))
        self.build()

    def t(self, key: str, **v) -> str:
        return self.app.t(key, **v)

    def build(self) -> None:  # pragma: no cover - overridden
        pass

    def on_show(self) -> None:
        pass


class ToolsPage(Page):
    def build(self) -> None:
        a = self.app
        guide = a.card(self)
        a.label(guide, self.t("guide_title"), 11, "bold", bg=SURFACE).pack(fill="x")
        self.steps = tk.Frame(guide, bg=SURFACE)
        self.steps.pack(fill="x", pady=(6, 0))
        self.cards: dict[str, tuple[tk.Label, tk.Button]] = {}
        for tool in tl.TOOLS:
            card = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
            card.pack(fill="x", pady=4)
            tk.Frame(card, bg=tool.colour, width=6).pack(side="left", fill="y")
            body = tk.Frame(card, bg=SURFACE, padx=14, pady=9)
            body.pack(side="left", fill="both", expand=True)
            a.label(body, self.t(f"{tool.key}_name"), 11, "bold", bg=SURFACE).pack(fill="x")
            a.label(body, self.t(f"{tool.key}_desc"), 9, fg=MUTED, bg=SURFACE, wrap=520).pack(fill="x", pady=(2, 3))
            status = a.label(body, "", 9, bg=SURFACE, wrap=520)
            status.pack(fill="x")
            actions = tk.Frame(card, bg=SURFACE, padx=14)
            actions.pack(side="right")
            open_b = a.button(actions, self.t("open"), lambda k=tool.key: self.open_tool(k), "primary", 9)
            open_b.pack(pady=(0, 6))
            a.button(actions, self.t("locate"), lambda k=tool.key: self.locate(k), width=9).pack()
            self.cards[tool.key] = (status, open_b)

    def on_show(self) -> None:
        a = self.app
        for w in self.steps.winfo_children():
            w.destroy()
        review_left = len(services.load_review(a.last_report, a.project)) if a.last_report and a.project else 0
        reviewed = a.last_report is not None and review_left == 0
        exports = a.project.files / "lab_exports" if a.project else None
        exported = bool(exports and exports.exists() and any(exports.iterdir()))
        steps = [("step_project", "project", a.project is not None),
                 ("step_import", "import", a.last_report is not None),
                 ("step_review", "review", reviewed),
                 ("step_lab", "lab", exported)]
        for n, (key, page, done) in enumerate(steps, start=1):
            row = tk.Frame(self.steps, bg=SURFACE)
            row.pack(fill="x", pady=2)
            mark = "✓" if done else str(n)
            tk.Label(row, text=mark, width=2, font=a.font(10, "bold"), bg=OK if done else ACCENT_SOFT,
                     fg="#FFFFFF" if done else ACCENT).pack(side="left")
            extra = self.t("step_review_left", n=review_left) if key == "step_review" and review_left else ""
            a.label(row, self.t(key) + extra, 10, bg=SURFACE, fg=MUTED if done else INK).pack(side="left", padx=10)
            a.link(row, self.t("go"), lambda p=page: a.show(p), SURFACE).pack(side="right")
        for tool in tl.TOOLS:
            found = tl.find(tool, a.settings, base=a.base, local_appdata=a.local_appdata)
            a.found[tool.key] = found
            status, button = self.cards[tool.key]
            if found:
                status.configure(text=self.t("status_ready", path=_shorten(str(found.path), 70)), fg=OK)
                button.configure(state="normal", bg=ACCENT, cursor="hand2")
            else:
                status.configure(text=self.t("status_missing"), fg=WARN)
                button.configure(state="disabled", bg=DISABLED, cursor="arrow")

    def open_tool(self, key: str) -> None:
        found = self.app.found.get(key)
        if not found:
            return
        try:
            tl.launch(found.path)
        except tl.LaunchError as exc:
            self.app.error(self.t("launch_failed", name=self.t(f"{key}_name"), error=exc))
            return
        self.app.say(self.t("started", name=self.t(f"{key}_name")), OK)

    def locate(self, key: str) -> None:
        a = self.app
        name = self.t(f"{key}_name")
        types = [(self.t("programs"), "*.exe")] if sys.platform == "win32" else [(self.t("programs"), "*")]
        chosen = filedialog.askopenfilename(parent=a.root, title=self.t("locate_title", name=name), filetypes=types)
        if not chosen:
            return
        if not tl.is_program(Path(chosen)):
            a.error(self.t("not_a_program"))
            return
        a.settings.tool_paths[key] = chosen
        a.settings.save(a.config_path)
        self.on_show()
        a.say(self.t("saved", name=name), OK)


class ProjectPage(Page):
    def build(self) -> None:
        a = self.app
        top = a.card(self)
        self.path_label = a.label(top, "", 10, bg=SURFACE, wrap=640)
        self.path_label.pack(fill="x")
        row = tk.Frame(top, bg=SURFACE)
        row.pack(fill="x", pady=(10, 0))
        a.button(row, self.t("new_project"), self.new_project, "primary").pack(side="left")
        a.button(row, self.t("open_project"), self.open_project).pack(side="left", padx=8)
        self.folder_btn = a.button(row, self.t("open_folder"), self.open_files)
        self.folder_btn.pack(side="left")
        self.recent = tk.Frame(self, bg=BG)
        self.recent.pack(fill="x")
        a.label(self, self.t("project_contents"), 11, "bold").pack(fill="x", pady=(10, 4))
        box = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="both", expand=True)
        self.table = a.tree(box, [("table", "col_table", 170, "w"), ("rows", "col_rows", 80, "e"),
                                  ("about", "col_about", 460, "w")], height=10)

    def on_show(self) -> None:
        a = self.app
        if a.project:
            self.path_label.configure(text=self.t("project_path", path=str(a.project.path)), fg=INK)
            self.folder_btn.configure(state="normal")
        else:
            self.path_label.configure(text=self.t("project_none_long"), fg=MUTED)
            self.folder_btn.configure(state="disabled")
        for w in self.recent.winfo_children():
            w.destroy()
        others = [p for p in a.settings.recent_projects if not a.project or p != str(a.project.path)]
        others = [p for p in others if Path(p).exists()][:4]
        if others:
            a.label(self.recent, self.t("recent"), 9, fg=MUTED).pack(fill="x", pady=(4, 0))
            for p in others:
                a.link(self.recent, _shorten(p, 90), lambda p=p: self.open_path(Path(p))).pack(anchor="w")
        self.table.delete(*self.table.get_children())
        if a.project:
            for i, (t, n) in enumerate(services.summary(a.project).items()):
                self.table.insert("", "end", values=(self.t(f"table_{t}"), f"{n:,}", self.t(f"tabledesc_{t}")),
                                  tags=("odd",) if i % 2 else ())

    def new_project(self) -> None:
        a = self.app
        path = filedialog.asksaveasfilename(parent=a.root, title=self.t("new_project"), defaultextension=".sqlite",
                                            filetypes=[(self.t("project_files"), "*.sqlite")],
                                            initialfile="my_study.sqlite")
        if path:
            a.set_project(services.create_project(path))
            a.say(self.t("project_created", name=a.project.name), OK)
            self.on_show()

    def open_project(self) -> None:
        path = filedialog.askopenfilename(parent=self.app.root, title=self.t("open_project"),
                                          filetypes=[(self.t("project_files"), "*.sqlite *.db")])
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        a = self.app
        try:
            a.set_project(services.create_project(path))
        except Exception as exc:
            a.error(self.t("project_open_failed", error=exc))
            return
        a.say(self.t("project_opened", name=a.project.name), OK)
        self.on_show()

    def open_files(self) -> None:
        if self.app.project:
            _open_folder(self.app.project.files)


class ScrollArea(tk.Frame):
    """A vertically scrolling area for pages whose content can outgrow the window."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width - 4))
        for widget in (self.canvas, self.inner):
            widget.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel))
            widget.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")

    def top(self) -> None:
        self.canvas.yview_moveto(0)


class ImportPage(Page):
    def build(self) -> None:
        a = self.app
        scroll = ScrollArea(self)
        scroll.pack(fill="both", expand=True)
        self.scroll = scroll
        body = scroll.inner
        src = a.card(body)
        a.label(src, self.t("release_folder"), 10, "bold", bg=SURFACE).pack(fill="x")
        row = tk.Frame(src, bg=SURFACE)
        row.pack(fill="x", pady=(6, 2))
        self.folder = tk.StringVar(value=a.settings.last_release_dir)
        ttk.Entry(row, textvariable=self.folder, font=a.font(10)).pack(side="left", fill="x", expand=True)
        a.button(row, self.t("browse"), self.browse).pack(side="left", padx=(8, 0))
        a.link(src, self.t("use_example"), self.use_example, SURFACE).pack(anchor="w", pady=(4, 0))

        opts = a.card(body)
        a.label(opts, self.t("options"), 10, "bold", bg=SURFACE).pack(fill="x")
        self.assume = tk.BooleanVar(value=False)
        self.accept = tk.BooleanVar(value=False)
        for var, key in ((self.assume, "opt_assume"), (self.accept, "opt_accept")):
            ttk.Checkbutton(opts, text=self.t(key), variable=var).pack(anchor="w", pady=(6, 0))
            a.label(opts, self.t(key + "_help"), 9, fg=MUTED, bg=SURFACE, wrap=680).pack(fill="x", padx=(24, 0))
        row = tk.Frame(opts, bg=SURFACE)
        row.pack(fill="x", pady=(8, 0))
        a.label(row, self.t("opt_companies"), 10, bg=SURFACE).pack(side="left")
        self.companies = tk.StringVar()
        ttk.Entry(row, textvariable=self.companies, width=28, font=a.font(10)).pack(side="left", padx=8)
        a.label(row, self.t("opt_companies_help"), 9, fg=MUTED, bg=SURFACE).pack(side="left")

        act = tk.Frame(body, bg=BG)
        act.pack(fill="x", pady=(8, 4))
        self.go = a.button(act, self.t("start_import"), self.start_import, "primary")
        self.go.pack(side="left")
        self.bar = ttk.Progressbar(act, mode="indeterminate", length=220, style="Horizontal.TProgressbar")
        self.result = tk.Frame(body, bg=BG)
        self.result.pack(fill="both", expand=True)

    def on_show(self) -> None:
        if self.app.last_report and not self.result.winfo_children():
            self.show_result(self.app.last_report)

    def browse(self) -> None:
        folder = filedialog.askdirectory(parent=self.app.root, title=self.t("release_folder"),
                                         initialdir=self.folder.get() or str(Path.home()))
        if folder:
            self.folder.set(folder)

    def use_example(self) -> None:
        a = self.app
        if not a.need_project():
            return
        folder = demo.build(a.project.files / "example_release_invented_data")
        self.folder.set(str(folder))
        a.say(self.t("example_ready"), OK)

    def start_import(self) -> None:
        a = self.app
        if not a.need_project():
            return
        folder = Path(self.folder.get().strip().strip('"'))
        if not (folder / "manifest.json").exists():
            a.error(self.t("not_a_release", folder=folder))
            return
        a.settings.last_release_dir = str(folder)
        a.settings.save(a.config_path)
        codes = tuple(c.strip() for c in self.companies.get().replace("，", ",").split(",") if c.strip())
        project, assume, accept = a.project, self.assume.get(), self.accept.get()
        self.go.configure(state="disabled", bg=DISABLED)
        self.bar.pack(side="left", padx=12)
        self.bar.start(12)
        a.run_in_background(lambda say: services.run_import(project, folder, companies=codes,
                                                            assume_consolidated=assume, accept_suggestions=accept,
                                                            progress=say), self.finished, "progress_reading")

    def finished(self, result) -> None:
        a = self.app
        self.bar.stop()
        self.bar.pack_forget()
        self.go.configure(state="normal", bg=ACCENT)
        if isinstance(result, Exception):
            a.say(self.t("import_failed_short"), ERROR)
            a.error(self.t("import_failed", error=result))
            return
        a.last_report = result.report_dir
        a.say(self.t("import_done", n=sum(v for k, v in result.report.imported.items() if k != "sources")), OK)
        self.show_result(result.report_dir)

    def show_result(self, report_dir: Path) -> None:
        a = self.app
        for w in self.result.winfo_children():
            w.destroy()
        data = json.loads((report_dir / "import_report.json").read_text(encoding="utf-8"))
        head = tk.Frame(self.result, bg=BG)
        head.pack(fill="x", pady=(6, 4))
        a.label(head, self.t("result_title", release=data["release"]), 11, "bold").pack(side="left")
        a.link(head, self.t("open_report_folder"), lambda: _open_folder(report_dir)).pack(side="right")
        stats = tk.Frame(self.result, bg=BG)
        stats.pack(fill="x")
        imp = data["imported"]
        for key, n in (("stat_entities", imp.get("entities", 0)), ("stat_relations", imp.get("ownership", 0)),
                       ("stat_revenue", imp.get("entity_financials", 0)),
                       ("stat_rejected", sum(r["rows"] for r in data["rejected"]))):
            box = tk.Frame(stats, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, padx=14, pady=8)
            box.pack(side="left", padx=(0, 8))
            colour = WARN if key == "stat_rejected" and n else INK
            a.label(box, f"{n:,}", 15, "bold", fg=colour, bg=SURFACE).pack(anchor="w")
            a.label(box, self.t(key), 9, fg=MUTED, bg=SURFACE).pack(anchor="w")
        waiting = data.get("review_jurisdictions", 0) + data.get("review_revenue", 0)
        if waiting:
            nxt = tk.Frame(self.result, bg=BG)
            nxt.pack(fill="x", pady=(8, 0))
            a.button(nxt, self.t("go_review", n=waiting), lambda: a.show("review"), "primary").pack(side="left")
        for note in data.get("notes", []):
            a.label(self.result, "• " + note, 9, fg=WARN, wrap=760).pack(fill="x", pady=(4, 0))
        if data["rejected"]:
            box = tk.Frame(self.result, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
            box.pack(fill="x", pady=(10, 12))
            tv = a.tree(box, [("table", "col_from", 190, "w"), ("reason", "col_reason", 440, "w"),
                              ("rows", "col_rows", 70, "e")], height=min(len(data["rejected"]), 8))
            for i, r in enumerate(data["rejected"]):
                tv.insert("", "end", values=(self.t(f"table_{r['table']}"), reason_text(a.settings.language,
                                                                                      r["reason"]), r["rows"]),
                          tags=("odd",) if i % 2 else ())


class ReviewPage(Page):
    def build(self) -> None:
        a = self.app
        self.empty = a.label(self, "", 10, fg=MUTED, wrap=700)
        self.empty.pack(fill="x")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        # Jurisdictions tab
        jt = tk.Frame(self.tabs, bg=SURFACE, padx=12, pady=10)
        self.tabs.add(jt, text=self.t("tab_jurisdictions"))
        a.label(jt, self.t("review_j_help"), 9, fg=MUTED, bg=SURFACE, wrap=700).pack(fill="x", pady=(0, 6))
        self.items_tv = a.tree(jt, [("name", "col_name", 290, "w"), ("problem", "col_problem", 190, "w"),
                                    ("suggested", "col_suggested", 100, "w"), ("rows", "col_rows", 60, "e"),
                                    ("choice", "col_choice", 120, "w")], height=9)
        self.items_tv.bind("<<TreeviewSelect>>", lambda _e: self.selected())
        self.items_tv.bind("<Double-1>", lambda _e: self.use_suggestion())
        edit = tk.Frame(jt, bg=SURFACE)
        edit.pack(fill="x", pady=(8, 0))
        a.label(edit, self.t("choose_for"), 10, bg=SURFACE).pack(side="left")
        codes = services.jurisdiction_codes()
        self.options = [f"{c}  {n}" for c, n in sorted(codes.items())]
        self.choice = tk.StringVar()
        self.combo = ttk.Combobox(edit, textvariable=self.choice, values=self.options, width=34, font=a.font(10))
        self.combo.pack(side="left", padx=8)
        self.combo.bind("<KeyRelease>", self.filter_options)
        self.combo.bind("<Return>", lambda _e: self.apply())
        a.button(edit, self.t("apply"), self.apply).pack(side="left")
        a.button(edit, self.t("use_suggestion"), self.use_suggestion).pack(side="left", padx=6)
        a.button(edit, self.t("clear"), self.clear).pack(side="left")
        foot = tk.Frame(jt, bg=SURFACE)
        foot.pack(fill="x", pady=(10, 0))
        a.button(foot, self.t("use_all_suggestions"), self.use_all).pack(side="left")
        self.rerun = a.button(foot, self.t("save_and_reimport"), self.save_and_reimport, "primary")
        self.rerun.pack(side="right")
        # Revenue tab
        rt = tk.Frame(self.tabs, bg=SURFACE, padx=12, pady=10)
        self.tabs.add(rt, text=self.t("tab_revenue"))
        a.label(rt, self.t("review_r_help"), 9, fg=MUTED, bg=SURFACE, wrap=700).pack(fill="x", pady=(0, 6))
        self.rev_tv = a.tree(rt, [("code", "col_code", 120, "w"), ("year", "col_year", 80, "w"),
                                  ("candidates", "col_candidates", 460, "w")], height=10)
        self.items: list[services.ReviewItem] = []
        self.pending: dict[str, str] = {}

    def on_show(self) -> None:
        a = self.app
        self.items, self.pending = [], {}
        self.items_tv.delete(*self.items_tv.get_children())
        self.rev_tv.delete(*self.rev_tv.get_children())
        if not a.project or not a.last_report:
            self.empty.configure(text=self.t("review_nothing"))
            return
        self.items = services.load_review(a.last_report, a.project)
        conflicts = services.load_revenue_conflicts(a.last_report)
        self.empty.configure(text=self.t("review_from", report=a.last_report.name) if self.items or conflicts
                             else self.t("review_clear"))
        self.tabs.tab(0, text=self.t("tab_jurisdictions") + f" ({len(self.items)})")
        self.tabs.tab(1, text=self.t("tab_revenue") + f" ({len(conflicts)})")
        for i, item in enumerate(self.items):
            self.items_tv.insert("", "end", iid=str(i), values=self.values(item), tags=("odd",) if i % 2 else ())
        for i, c in enumerate(conflicts):
            self.rev_tv.insert("", "end", values=(c["security_code"], c["year"], c["candidates_cny"]),
                               tags=("odd",) if i % 2 else ())
        if self.items:
            self.items_tv.selection_set("0")

    def values(self, item: services.ReviewItem) -> tuple:
        choice = self.pending.get(item.name, item.chosen)
        problem = self.t("problem_holder") if item.status.startswith("holder") else self.t(
            "problem_place_" + item.status.split()[-1])
        return (item.name, problem, item.suggestion or "", item.rows, choice or self.t("not_chosen"))

    def current(self) -> services.ReviewItem | None:
        sel = self.items_tv.selection()
        return self.items[int(sel[0])] if sel else None

    def selected(self) -> None:
        item = self.current()
        if item:
            code = self.pending.get(item.name, item.chosen) or item.suggestion.split("/")[0]
            match = next((o for o in self.options if o.startswith(code + " ")), "") if code else ""
            self.choice.set(match)

    def filter_options(self, _e=None) -> None:
        typed = self.choice.get().strip().lower()
        self.combo.configure(values=[o for o in self.options if typed in o.lower()] or self.options)

    def set_choice(self, item: services.ReviewItem, code: str) -> None:
        self.pending[item.name] = code
        idx = self.items.index(item)
        self.items_tv.item(str(idx), values=self.values(item), tags=("done",) if code else ())

    def apply(self) -> None:
        item = self.current()
        code = self.choice.get().split()[0].upper() if self.choice.get().strip() else ""
        if item and code:
            if code not in services.jurisdiction_codes():
                self.app.error(self.t("bad_code", code=code))
                return
            self.set_choice(item, code)
            self.next_item()

    def use_suggestion(self) -> None:
        item = self.current()
        if item and item.suggestion and "/" not in item.suggestion:
            self.set_choice(item, item.suggestion)
            self.next_item()

    def clear(self) -> None:
        item = self.current()
        if item:
            self.set_choice(item, "")

    def use_all(self) -> None:
        for item in self.items:
            if item.suggestion and "/" not in item.suggestion and not self.pending.get(item.name, item.chosen):
                self.set_choice(item, item.suggestion)

    def next_item(self) -> None:
        sel = self.items_tv.selection()
        if sel and int(sel[0]) + 1 < len(self.items):
            nxt = str(int(sel[0]) + 1)
            self.items_tv.selection_set(nxt)
            self.items_tv.see(nxt)

    def save_and_reimport(self) -> None:
        a = self.app
        if not a.project or not a.last_report:
            return
        try:
            services.save_overrides(a.project, self.pending)
        except ValueError as exc:
            a.error(str(exc))
            return
        settings = services.report_settings(a.last_report)
        folder = settings.get("release_folder")
        if not folder or not Path(folder).exists():
            a.say(self.t("choices_saved"), OK)
            return
        project = a.project
        self.rerun.configure(state="disabled", bg=DISABLED)

        def done(result):
            self.rerun.configure(state="normal", bg=ACCENT)
            if isinstance(result, Exception):
                a.error(self.t("import_failed", error=result))
                return
            a.last_report = result.report_dir
            a.say(self.t("reimported", n=len(self.pending)), OK)
            a.pages["import"].show_result(result.report_dir)
            self.on_show()

        a.run_in_background(lambda say: services.run_import(
            project, folder, companies=tuple(settings.get("companies", ())),
            assume_consolidated=settings.get("assume_consolidated", False),
            accept_suggestions=settings.get("accept_suggestions", False), progress=say), done, "progress_reading")


class DataPage(Page):
    def build(self) -> None:
        a = self.app
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", pady=(0, 6))
        a.label(bar, self.t("search"), 10).pack(side="left")
        self.query = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.query, width=32, font=a.font(10))
        entry.pack(side="left", padx=8)
        entry.bind("<Return>", lambda _e: self.on_show())
        a.button(bar, self.t("search_go"), self.on_show).pack(side="left")
        self.source_btn = a.button(bar, self.t("open_source"), self.open_source)
        self.source_btn.pack(side="right")
        self.count = a.label(self, "", 9, fg=MUTED)
        self.count.pack(fill="x")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        ot = tk.Frame(self.tabs, bg=SURFACE)
        self.tabs.add(ot, text=self.t("tab_ownership"))
        self.own_tv = a.tree(ot, [("holder", "col_holder", 220, "w"), ("hj", "col_j", 56, "w"),
                                  ("type", "col_type", 82, "w"), ("stake", "col_stake", 86, "e"),
                                  ("held", "col_held", 220, "w"), ("dj", "col_j", 56, "w"),
                                  ("date", "col_date", 104, "w")], height=14)
        rt = tk.Frame(self.tabs, bg=SURFACE)
        self.tabs.add(rt, text=self.t("tab_revenue_data"))
        self.rev_tv = a.tree(rt, [("entity", "col_entity", 260, "w"), ("year", "col_year", 70, "w"),
                                  ("revenue", "col_revenue", 170, "e"), ("basis", "col_basis", 120, "w")], height=14)
        for tv in (self.own_tv, self.rev_tv):
            tv.bind("<Double-1>", lambda _e: self.open_source())
        self.tabs.bind("<<NotebookTabChanged>>", lambda _e: self.update_count())
        self.urls: dict[str, str] = {}
        self.own_rows: list[dict] = []
        self.rev: list[dict] = []

    def on_show(self) -> None:
        a = self.app
        self.own_tv.delete(*self.own_tv.get_children())
        self.rev_tv.delete(*self.rev_tv.get_children())
        self.urls = {}
        if not a.project:
            self.count.configure(text=self.t("project_none_long"))
            return
        q = self.query.get()
        self.own_rows = services.ownership_rows(a.project, q)
        for i, r in enumerate(self.own_rows):
            stake = f"{r['fraction'] * 100:.2f}%" if r["fraction"] is not None else ""
            iid = f"o{i}"
            self.own_tv.insert("", "end", iid=iid, values=(r["holder"], r["holder_j"], self.t("rel_" + r["relation_type"]),
                                                           stake, r["held"], r["held_j"], r["valid_from"]),
                               tags=("odd",) if i % 2 else ())
            self.urls[iid] = r["source_url"]
        self.rev = services.revenue_rows(a.project, q)
        for i, r in enumerate(self.rev):
            iid = f"r{i}"
            self.rev_tv.insert("", "end", iid=iid, values=(r["entity"], r["period"],
                                                           f"{r['operating_revenue']:,.0f} {r['currency']}",
                                                           self.t("basis_" + r["consolidation"])),
                               tags=("odd",) if i % 2 else ())
            self.urls[iid] = r["source_url"]
        self.update_count()

    def update_count(self) -> None:
        if not self.app.project:
            return
        on_own = self.tabs.index("current") == 0
        n = len(self.own_rows) if on_own else len(self.rev)
        self.count.configure(text=self.t("rows_shown", n=n) + "  ·  " + self.t("source_hint"))

    def open_source(self) -> None:
        tv = self.own_tv if self.tabs.index("current") == 0 else self.rev_tv
        sel = tv.selection()
        if not sel:
            self.app.say(self.t("select_row_first"), WARN)
            return
        if not services.open_url(self.urls.get(sel[0])):
            self.app.say(self.t("no_source_url"), WARN)


class LabPage(Page):
    def build(self) -> None:
        a = self.app
        lab = a.card(self)
        a.label(lab, self.t("lab_section"), 11, "bold", bg=SURFACE).pack(fill="x")
        a.label(lab, self.t("lab_help"), 9, fg=MUTED, bg=SURFACE, wrap=700).pack(fill="x", pady=(2, 8))
        row = tk.Frame(lab, bg=SURFACE)
        row.pack(fill="x")
        a.button(row, self.t("export_lab"), self.export_lab, "primary").pack(side="left")
        self.open_lab_btn = a.button(row, self.t("open_lab"), self.open_lab)
        self.open_lab_btn.pack(side="left", padx=8)
        self.lab_out = a.label(lab, "", 9, fg=MUTED, bg=SURFACE, wrap=700)
        self.lab_out.pack(fill="x", pady=(6, 0))
        snap = a.card(self, fill="both", expand=True)
        a.label(snap, self.t("snap_section"), 11, "bold", bg=SURFACE).pack(fill="x")
        a.label(snap, self.t("snap_help"), 9, fg=MUTED, bg=SURFACE, wrap=700).pack(fill="x", pady=(2, 8))
        row = tk.Frame(snap, bg=SURFACE)
        row.pack(fill="x", pady=(0, 8))
        a.label(row, self.t("snap_note"), 10, bg=SURFACE).pack(side="left")
        self.note = tk.StringVar()
        ttk.Entry(row, textvariable=self.note, width=36, font=a.font(10)).pack(side="left", padx=8)
        a.button(row, self.t("take_snapshot"), self.take_snapshot, "primary").pack(side="left")
        self.snaps = a.tree(snap, [("when", "col_when", 170, "w"), ("id", "col_id", 140, "w"),
                                   ("rows", "col_rows", 90, "e"), ("note", "col_note", 300, "w")], height=6)
        row = tk.Frame(snap, bg=SURFACE)
        row.pack(fill="x", pady=(8, 0))
        a.button(row, self.t("verify_snapshot"), self.verify).pack(side="left")
        a.button(row, self.t("open_folder"), self.open_snapshot).pack(side="left", padx=8)

    def on_show(self) -> None:
        a = self.app
        lab = tl.find(tl.TOOLS_BY_KEY["lab"], a.settings, base=a.base, local_appdata=a.local_appdata)
        self.open_lab_btn.configure(state="normal" if lab else "disabled")
        if not lab and not self.lab_out.cget("text"):
            self.lab_out.configure(text=self.t("lab_not_found"), fg=MUTED)
        self.snaps.delete(*self.snaps.get_children())
        if not a.project:
            return
        for i, s in enumerate(services.list_snapshots(a.project)):
            self.snaps.insert("", "end", iid=s["snapshot_id"] + str(i),
                              values=(s["created_utc"].replace("T", " ")[:19], s["snapshot_id"][:12] + "…",
                                      f"{sum(s['counts'].values()):,}", s["note"] or ""),
                              tags=("odd",) if i % 2 else ())

    def export_lab(self) -> None:
        a = self.app
        if not a.need_project():
            return
        out = services.export_lab(a.project)
        self.lab_out.configure(text=self.t("lab_written", path=str(out)), fg=OK)
        a.say(self.t("lab_done"), OK)
        _open_folder(out)

    def open_lab(self) -> None:
        a = self.app
        found = tl.find(tl.TOOLS_BY_KEY["lab"], a.settings, base=a.base, local_appdata=a.local_appdata)
        if found:
            try:
                tl.launch(found.path)
                a.say(self.t("started", name=self.t("lab_name")), OK)
            except tl.LaunchError as exc:
                a.error(self.t("launch_failed", name=self.t("lab_name"), error=exc))

    def take_snapshot(self) -> None:
        a = self.app
        if not a.need_project():
            return
        folder = services.take_snapshot(a.project, self.note.get().strip())
        self.note.set("")
        a.say(self.t("snapshot_done", id=folder.name[:12]), OK)
        self.on_show()

    def chosen_folder(self) -> Path | None:
        sel = self.snaps.selection()
        if not sel or not self.app.project:
            self.app.say(self.t("select_row_first"), WARN)
            return None
        sid = self.snaps.item(sel[0])["values"][1]
        snaps = services.list_snapshots(self.app.project)
        full = next((s["snapshot_id"] for s in snaps if s["snapshot_id"].startswith(str(sid).rstrip("…"))), None)
        return services.snapshot_folder(self.app.project, full) if full else None

    def verify(self) -> None:
        folder = self.chosen_folder()
        if folder is None:
            return
        problems = services.verify_snapshot(folder)
        if problems:
            self.app.error(self.t("snapshot_changed") + "\n" + "\n".join(problems))
        else:
            messagebox.showinfo(self.t("verify_snapshot"), self.t("snapshot_intact"), parent=self.app.root)

    def open_snapshot(self) -> None:
        folder = self.chosen_folder()
        if folder:
            _open_folder(folder)


class CheckPage(Page):
    def build(self) -> None:
        a = self.app
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        a.button(row, self.t("run_check"), self.run_check, "primary").pack(side="left")
        self.verdict = a.label(row, "", 11, "bold")
        self.verdict.pack(side="left", padx=14)
        box = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="both", expand=True)
        self.tv = a.tree(box, [("level", "col_level", 90, "w"), ("table", "col_table", 150, "w"),
                               ("where", "col_where", 160, "w"), ("message", "col_message", 420, "w")], height=14)

    def run_check(self) -> None:
        a = self.app
        if not a.need_project():
            return
        report = services.check(a.project)
        self.tv.delete(*self.tv.get_children())
        for i, issue in enumerate(report.issues):
            self.tv.insert("", "end", values=(self.t("level_" + issue.level), self.t(f"table_{issue.table}"),
                                              issue.where, issue.message),
                           tags=("error" if issue.level == "error" else "warn",))
        if report.ok and not report.warnings:
            self.verdict.configure(text=self.t("check_clean"), fg=OK)
        elif report.ok:
            self.verdict.configure(text=self.t("check_warnings", n=len(report.warnings)), fg=WARN)
        else:
            self.verdict.configure(text=self.t("check_errors", n=len(report.errors)), fg=ERROR)


PAGE_CLASSES = {"tools": ToolsPage, "project": ProjectPage, "import": ImportPage, "review": ReviewPage,
                "data": DataPage, "lab": LabPage, "check": CheckPage}


# ====================================================================== entry points
def run(config_path: Path | None = None) -> None:
    root = tk.Tk()
    root.geometry("1100x720")
    App(root, config_path or tl.default_config_path())
    root.mainloop()


def self_test(config_path: Path) -> None:
    """Build every page in both languages and run the example import end to end, without launching tools.

    Run by the Windows build after packaging, so a page that fails to build or a broken service stops the
    build."""
    import tempfile

    root = tk.Tk()
    with tempfile.TemporaryDirectory() as tmp:
        project = services.create_project(Path(tmp) / "self_test")
        settings = tl.Settings(project=str(project.path))
        settings.save(config_path)
        app = App(root, config_path)
        for language in tl.LANGUAGES:
            for key in PAGES:
                app.show(key)
                root.update()
            if language != tl.LANGUAGES[-1]:
                app.switch_language()
        release = demo.build(project.files / "example")
        result = services.run_import(project, release)
        app.last_report = result.report_dir
        app.pages["import"].show_result(result.report_dir)
        for key in ("review", "data", "lab"):
            app.show(key)
            root.update()
        app.pages["review"].use_all()
        app.pages["lab"].take_snapshot()
        app.pages["check"].run_check()
        root.update()
        assert services.summary(project)["ownership"] > 0, "example import wrote no relations"
        root.destroy()
