"""The launcher window (tkinter, part of Python's standard library).

Colours follow the International Tax Network Lab's interface (its ``web/styles.css``); each tool card
carries the tool's colour from the suite icon.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from importlib import resources
from pathlib import Path
from tkinter import filedialog, messagebox

from rscore import SCHEMA_GENERATION, __version__
from rscore.launcher import tools as tl
from rscore.launcher.i18n import text

BG, SURFACE, INK, MUTED, LINE = "#FAFAFB", "#FFFFFF", "#1C1F2A", "#6B7280", "#E7E8EC"
ACCENT, ACCENT_SOFT, OK, WARN, DISABLED = "#4F46E5", "#EEF0FF", "#059669", "#B45309", "#C7C9D1"

FONTS = {
    "en": ("Segoe UI", "Noto Sans", "DejaVu Sans", "Helvetica"),
    "zh-Hans": ("Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans CJK TC", "PingFang SC"),
}


def _asset(name: str) -> str:
    return str(resources.files("rscore.launcher").joinpath("assets", name))


def _shorten(path: str, limit: int = 46) -> str:
    if len(path) <= limit:
        return path
    keep = (limit - 1) // 2
    return path[:keep] + "…" + path[-keep:]


class App:
    def __init__(self, root: tk.Tk, config_path: Path, *, base: Path | None = None,
                 local_appdata: Path | None = None):
        self.root = root
        self.config_path = config_path
        self.base, self.local_appdata = base, local_appdata
        self.settings = tl.Settings.load(config_path)
        self.found: dict[str, tl.Found | None] = {}
        root.title(text(self.settings.language, "app_title"))
        root.configure(bg=BG)
        root.resizable(False, False)
        root.minsize(640, 1)
        self._icon_big = tk.PhotoImage(file=_asset("icon_256.png"))
        self._icon_header = tk.PhotoImage(file=_asset("icon_48.png"))
        root.iconphoto(True, self._icon_big)
        self.build()

    # -------------------------------------------------------------- helpers
    def t(self, key: str, **values: object) -> str:
        return text(self.settings.language, key, **values)

    def font(self, size: float, weight: str = "normal") -> tkfont.Font:
        families = set(tkfont.families(self.root))
        family = next((f for f in FONTS[self.settings.language] if f in families), "TkDefaultFont")
        return tkfont.Font(root=self.root, family=family, size=round(size), weight=weight)

    def _button(self, parent: tk.Widget, label: str, command, primary: bool) -> tk.Button:
        return tk.Button(
            parent, text=label, command=command, font=self.font(10, "bold" if primary else "normal"),
            bg=ACCENT if primary else SURFACE, fg="#FFFFFF" if primary else ACCENT,
            activebackground="#4338CA" if primary else ACCENT_SOFT,
            activeforeground="#FFFFFF" if primary else ACCENT,
            disabledforeground="#FFFFFF" if primary else DISABLED,
            relief="flat", bd=0, highlightthickness=0 if primary else 1, highlightbackground=LINE,
            padx=14, pady=5, cursor="hand2", width=9)

    def _link(self, parent: tk.Widget, label: str, command) -> tk.Label:
        link = tk.Label(parent, text=label, font=self.font(9), fg=ACCENT, bg=BG, cursor="hand2")
        link.bind("<Button-1>", lambda _e: command())
        return link

    # -------------------------------------------------------------- layout
    def build(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self.t("app_title"))
        outer = tk.Frame(self.root, bg=BG, padx=22, pady=18)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 14))
        tk.Label(header, image=self._icon_header, bg=BG).pack(side="left", padx=(0, 12))
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", fill="x", expand=True)
        tk.Label(titles, text=self.t("app_title"), font=self.font(16, "bold"), fg=INK, bg=BG,
                 anchor="w").pack(fill="x")
        tk.Label(titles, text=self.t("subtitle"), font=self.font(10), fg=MUTED, bg=BG, anchor="w").pack(fill="x")
        self._link(header, self.t("switch_language"), self.switch_language).pack(side="right", anchor="n")

        self.status_labels: dict[str, tk.Label] = {}
        self.open_buttons: dict[str, tk.Button] = {}
        for tool in tl.TOOLS:
            self._card(outer, tool)

        footer = tk.Frame(outer, bg=BG)
        footer.pack(fill="x", pady=(10, 0))
        self.message = tk.Label(footer, text=self.t("footer", version=__version__, generation=SCHEMA_GENERATION),
                                font=self.font(9), fg=MUTED, bg=BG, anchor="w")
        self.message.pack(side="left", fill="x", expand=True)
        self._link(footer, self.t("about"), self.about).pack(side="right")
        tk.Label(footer, text="  ", bg=BG).pack(side="right")
        self._link(footer, self.t("settings"), self.open_settings_folder).pack(side="right")
        self.refresh()

    def _card(self, parent: tk.Widget, tool: tl.Tool) -> None:
        card = tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", pady=5)
        tk.Frame(card, bg=tool.colour, width=6).pack(side="left", fill="y")
        body = tk.Frame(card, bg=SURFACE, padx=14, pady=11)
        body.pack(side="left", fill="both", expand=True)
        tk.Label(body, text=self.t(f"{tool.key}_name"), font=self.font(11, "bold"), fg=INK, bg=SURFACE,
                 anchor="w").pack(fill="x")
        tk.Label(body, text=self.t(f"{tool.key}_desc"), font=self.font(9), fg=MUTED, bg=SURFACE, anchor="w",
                 justify="left", wraplength=400).pack(fill="x", pady=(2, 4))
        status = tk.Label(body, font=self.font(9), bg=SURFACE, anchor="w", justify="left", wraplength=400)
        status.pack(fill="x")
        self.status_labels[tool.key] = status
        actions = tk.Frame(card, bg=SURFACE, padx=14)
        actions.pack(side="right")
        button = self._button(actions, self.t("open"), lambda k=tool.key: self.open_tool(k), True)
        button.pack(pady=(0, 6))
        self.open_buttons[tool.key] = button
        self._button(actions, self.t("locate"), lambda k=tool.key: self.locate(k), False).pack()

    def refresh(self) -> None:
        for tool in tl.TOOLS:
            found = tl.find(tool, self.settings, base=self.base, local_appdata=self.local_appdata)
            self.found[tool.key] = found
            label, button = self.status_labels[tool.key], self.open_buttons[tool.key]
            if found:
                label.configure(text=self.t("status_ready", path=_shorten(str(found.path))), fg=OK)
                button.configure(state="normal", bg=ACCENT, cursor="hand2")
            else:
                label.configure(text=self.t("status_missing"), fg=WARN)
                button.configure(state="disabled", bg=DISABLED, cursor="arrow")

    # -------------------------------------------------------------- actions
    def say(self, message: str) -> None:
        self.message.configure(text=message)

    def switch_language(self) -> None:
        langs = tl.LANGUAGES
        self.settings.language = langs[(langs.index(self.settings.language) + 1) % len(langs)]
        self.settings.save(self.config_path)
        self.build()

    def open_tool(self, key: str) -> None:
        found = self.found.get(key)
        name = self.t(f"{key}_name")
        if not found:
            return
        try:
            tl.launch(found.path)
        except tl.LaunchError as exc:
            messagebox.showerror(self.t("error"), self.t("launch_failed", name=name, error=exc), parent=self.root)
            return
        self.say(self.t("started", name=name))

    def locate(self, key: str) -> None:
        name = self.t(f"{key}_name")
        start = self.local_appdata or (Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else None)
        types = [(self.t("programs"), "*.exe")] if sys.platform == "win32" else [(self.t("programs"), "*")]
        chosen = filedialog.askopenfilename(
            parent=self.root, title=self.t("locate_title", name=name), filetypes=types,
            initialdir=str(start / "Programs") if start and (start / "Programs").is_dir() else str(Path.home()))
        if not chosen:
            return
        path = Path(chosen)
        if not tl.is_program(path):
            messagebox.showerror(self.t("error"), self.t("not_a_program"), parent=self.root)
            return
        self.settings.tool_paths[key] = str(path)
        self.settings.save(self.config_path)
        self.refresh()
        self.say(self.t("saved", name=name))

    def open_settings_folder(self) -> None:
        folder = self.config_path.parent
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            try:
                subprocess.Popen([opener, str(folder)])
            except OSError:
                self.say(str(folder))

    def about(self) -> None:
        messagebox.showinfo(self.t("about"), self.t("about_text", version=__version__), parent=self.root)


def run(config_path: Path | None = None) -> None:
    root = tk.Tk()
    App(root, config_path or tl.default_config_path())
    root.mainloop()


def self_test(config_path: Path) -> None:
    """Build the window in both languages without showing it for long or launching anything."""
    root = tk.Tk()
    app = App(root, config_path)
    root.update()
    app.switch_language()
    root.update()
    root.destroy()
