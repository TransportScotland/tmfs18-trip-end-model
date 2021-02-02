# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 11:38:28 2019

@author: japeach
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable, Tuple


class TextLog:
    def __init__(self,
                 frame: ttk.Frame,
                 width: int = 50,
                 height: int = 8
                 ) -> None:

        self.log_frame = ttk.Frame(frame, borderwidth=2, relief=tk.GROOVE)
        self.log_frame.pack(side="top", padx=5, pady=2, ipadx=5, ipady=5)
        self.text = tk.Text(self.log_frame, width=width,
                            height=height, wrap=tk.WORD)
        self.text.configure(font=("Helvetica", 7))
        self.text.config(state=tk.DISABLED)
        self.scrollbar = tk.Scrollbar(self.log_frame)
        self.text.pack(side="left", fill="both", expand="yes")
        self.scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.text.yview)
        self.text.tag_config('RED', foreground='red')
        self.text.tag_config('GREEN', foreground='green')
        self.text.tag_config('BLUE', foreground='blue')

    def add_message(self,
                    message: str,
                    color: str = '',
                    clear: bool = False
                    ) -> None:

        self.text.config(state=tk.NORMAL)
        if clear:
            self.clear()
        if not message.endswith('\n'):
            message += '\n'
        if color == '':
            self.text.insert(tk.END, message)
        else:
            self.text.insert(tk.END, message, color)
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)

    def clear(self) -> None:
        self.add_message("Clearing...")
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)


class CreateToolTip:
    def __init__(self,
                 widget: ttk.Widget,
                 text: str = "Widget Info"
                 ) -> None:
        self.wait_time = 500
        self.wrap_length = 180
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.wait_id = None
        self.top_window = None

    def enter(self, event: tk.Event = None) -> None:
        self.begin_wait()

    def leave(self, event: tk.Event = None) -> None:
        self.stop_wait()
        self.destroy_tooltip()

    def begin_wait(self) -> None:
        self.stop_wait()
        self.wait_id = self.widget.after(self.wait_time, self.create_tooltip)

    def stop_wait(self) -> None:
        id = self.wait_id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def create_tooltip(self, event: tk.Event = None) -> None:
        x = 0
        y = 0
        x, y, w, h = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.top_window = tk.Toplevel(self.widget)
        self.top_window.attributes("-topmost", "true")

        self.top_window.wm_overrideredirect(True)
        self.top_window.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.top_window,
                         text=self.text,
                         justify="left",
                         background="#ffffff",
                         relief="solid",
                         borderwidth=1,
                         wraplength=self.wrap_length)
        label.pack(ipadx=1)

    def destroy_tooltip(self) -> None:
        top_window = self.top_window
        self.top_window = None
        if top_window:
            top_window.destroy()


class LabelledEntry:
    def __init__(self,
                 master: ttk.Widget,
                 text: str,
                 var: tk.StringVar,
                 w: int = 5,
                 lw: int = 20,
                 pack_side: str = "top",
                 tool_tip_text: str = "",
                 anchor: str = "w",
                 char_limit: int = None,
                 px: int = 5,
                 py: int = 1,
                 lx: int = 5,
                 ly: int = 5,
                 inter_pack_side: str = "left",
                 button_pack_side: str = "left",
                 text_style: str = "TLabel",
                 dir_callback: Callable = None
                 ) -> None:
        self.px = px
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(side=pack_side, anchor=anchor, pady=py, padx=px)
        self.frame = ttk.Frame(self.main_frame)
        self.frame.pack(side=button_pack_side)
        self.button_side = button_pack_side
        self.dir = None
        self.variable = var
        self.limit = char_limit

        okay_func = self.frame.register(self.validate)
        if dir_callback is not None:
            self.dir_callback_func = dir_callback
        label = ttk.Label(
            self.frame,
            text=text,
            width=lw,
            style=text_style
        )
        label.pack(side=inter_pack_side, anchor=anchor, padx=lx, pady=ly)
        self.entry = ttk.Entry(
            self.frame,
            textvariable=var,
            width=w,
            validate="all",
            validatecommand=(okay_func, "%P")
        )
        self.entry.pack(side=inter_pack_side, anchor="e")
        if tool_tip_text != "":
            CreateToolTip(label, tool_tip_text)

    def validate(self,
                 text: str) -> bool:
        if self.limit is None:
            return True
        if len(text) < self.limit:
            return True
        return False

    def add_button(self,
                   callback_command: Callable,
                   text: str = ""
                   ) -> None:
        button = ttk.Button(self.frame, text=text, command=callback_command)
        button.pack(side="left", anchor="e", padx=self.px)

    def add_directory(self,
                      working_dir: str = None,
                      change_callback: Callable = None
                      ) -> None:
        self.dir = working_dir
        self.callback = change_callback
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(side=self.button_side, fill="y")
        button = ttk.Button(button_frame, text="Browse",
                            command=self.get_working_dir)
        button.pack(side="bottom", anchor="s", padx=self.px)

    def add_browse(self,
                   working_dir: str,
                   save: bool = False,
                   types: Tuple[Tuple[str, str]] = (("CSV", "*.csv")),
                   extension: str = ".csv"
                   ) -> None:

        self.dir = tk.StringVar()
        self.dir.set(working_dir)
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(side=self.button_side, fill="y")
        if not save:
            button = ttk.Button(
                button_frame,
                text="Browse",
                command=self.get_file_name
            )
        else:
            self.types = types
            button = ttk.Button(
                button_frame,
                text="Browse",
                command=lambda: self.get_save_file_name(extension)
            )
        button.pack(side="bottom", anchor="s", padx=self.px)

    def get_working_dir(self) -> None:
        win_title = (
            "Working Directory - Containing: Data, Input, Output Folders"
        )
        try:
            working_dir = filedialog.askdirectory(title=win_title)
        except ValueError:
            return
        if working_dir == "":
            return
        self.variable.set(working_dir)
        self.dir_callback_func(self.variable.get())

    def get_save_file_name(self,
                           extension: str = ".xlsx"
                           ) -> None:
        try:
            full_path = filedialog.asksaveasfilename(
                defaultextension=extension
            )
        except ValueError:
            return
        if full_path == "":
            return
        self.variable.set(os.path.relpath(full_path, self.dir.get()))

    def get_file_name(self) -> None:
        try:
            full_path = filedialog.askopenfilename(parent=self.frame)
        except ValueError:
            return
        if full_path == "":
            return
        self.variable.set(os.path.relpath(full_path, self.dir.get()))
