# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 11:35:25 2019

@author: japeach
"""

import tkinter as tk
from tkinter import ttk, filedialog
import json
import os
import threading
import queue
import traceback
from webbrowser import open_new
from telmos_script import telmos_all
from widget_templates import LabelledEntry, TextLog


# Global Parameters
REBASING_RUN = 0

VAR_DEFAULTS = {
    "delta_root": ["Delta Root Directory", "DELTA"],
    "tmfs_root": ["TMfS Root Directory", ""],
    "forecast_year": ["Forecast Year", "18"],
    "forecast_id": ["Forecast ID", "XXX"],
    "forecast_scenario": ["Forecast Scenario", "XX"],
    "base_year": ["Base Year", "18"],
    "base_id": ["Base ID", "ZZZ"],
    "base_scenario": ["Base Scenario", "ZZ"],
    "RTF File": ["RTF File", ""],
    "PTF File": ["PTF File", ""],
    "Airport Growth File": ["Airport Growth File", ""],
    "home_working": ["Integrate Home Working", 1],
    "old_tr_fmt": ["Use Old Trip Rate Format (Legacy)", 0],
    "rebasing_run": ["Rebasing Run", REBASING_RUN]
}

DESCRIPTION = (
    "This tool uses TELMoS planning data and trip rates from NTEM to "
    "apply growth to the calibrated forecast trip ends that are input "
    "to the demand model of the Transport Model for Scotland (TMfS). "
    "The trip end files produced by this tool should be run through "
    "the Cube smoothing process."
)

GITHUB_LINK = (
    "https://github.com/TransportScotland/tmfs18-trip-end-model/releases"
)

DELTA_DIR_TT = (
    "Has sub-directories containing the TELMoS planning data csv "
    "files and goods dat files. Folders and files should be named "
    "according to the year and scenario code.\n"
    "E.g. DELTA\\DL\\{PlanningData} where DELTA is the directory "
    "to be selected and DL is one of the scenario codes.\n"
    "See the README for info on the required planning data."
)

TMFS_DIR_TT = (
    "Contains the 'Factors' folder and the 'Runs' folder.\n"
    "'Factors' contains all internal factor files used by the model\n"
    "'Runs' contains the base year trip ends and is where the model "
    "will output the new trip ends.\n"
    "E.g. TMFS\\Factors\\{FactorsFiles}; and "
    "TMFS\\Runs\\18\\Demand\\ADL\\{TripEndFiles} where TMFS "
    "is the directory to be selected, 18 is the base year "
    "and ADL is the base ID. An empty directory should also be "
    "created for the forecast year\n"
    "See the README for info on the required factors files."
)


def toggle_widgets(base, target_state):
    """Toggles all child widgets of "base" to the target states, disabling
    input for text entry and button widgets. Skips widgets where this is
    not possible.

    Args:
        base (ttk.Frame): The parent widget or Frame
        target_state (str): "normal" or "disabled"
    """
    try:
        base.configure(state=target_state)
    except tk.TclError:
        # This is used to catch errors when setting the state on a tkinter
        # object where this cannot be done
        pass
    for child_widget in base.winfo_children():
        toggle_widgets(child_widget, target_state)


class Application:
    def __init__(self, parent):

        parent.title("TMfS18 Trip End Model")
        self.after = parent.after

        # Create dictionary of display names for the variables
        self.user_names = {var: val[0] for var, val in VAR_DEFAULTS.items()}

        # Build dictionary of variables used by the GUI
        self.vars = {}
        for k, value in VAR_DEFAULTS.items():
            def_val = value[1]
            if type(def_val) == int:
                self.vars[k] = tk.IntVar()
            else:
                self.vars[k] = tk.StringVar()
            self.vars[k].set(def_val)

        self.new_thread = None
        self.init_widgets(parent)
        parent.resizable(height=False, width=False)

    def init_widgets(self, parent):

        # Setup new frames to store the widgets
        self.main_frame = ttk.Frame(parent)
        log_frame = ttk.Frame(parent)
        title_frame = ttk.Frame(self.main_frame,
                                borderwidth=3,
                                relief=tk.GROOVE)
        input_frame = ttk.Frame(self.main_frame)
        run_frame = ttk.Frame(self.main_frame)

        self.main_frame.pack(side="left")
        log_frame.pack(side="left")
        title_frame.pack(fill="x", padx=5, pady=5)
        input_frame.pack(fill="x", expand=True, padx=5, pady=5)
        run_frame.pack(fill="x")

        # Define the styles for headers and title
        style = ttk.Style()
        style.configure("HEAD.TLabel", font=("Helvetica", 10, "bold"))
        style.configure("TIT.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("BIG.TButton", font=("Helvetica", 12, "bold"))

        # Create Title widget
        ttk.Label(
            title_frame,
            text="TMfS18 Trip End Model",
            style="TIT.TLabel"
        ).pack()
        # Create Description below the title
        ttk.Label(
            title_frame,
            text=DESCRIPTION,
            wraplength=500
        ).pack(fill="x", padx=5, pady=5)
        # Add a button linking to GitHub
        ttk.Button(
            title_frame,
            text="Check for Newer Releases",
            command=lambda: open_new(GITHUB_LINK)
        ).pack(anchor="w", padx=5, pady=5)

        # Create sub frame in the user input frame for each category
        # Split into directory selection, scenario definition and other options
        directory_frame = ttk.Frame(
            input_frame,
            borderwidth=3,
            relief=tk.GROOVE
        )
        directory_frame.pack()
        scenario_frame = ttk.Frame(input_frame)
        scenario_frame.pack(fill="x")
        factor_frame = ttk.Frame(
            input_frame,
            borderwidth=3,
            relief=tk.GROOVE
        )
        factor_frame.pack(anchor="w", fill="x", expand=True)
        save_frame = ttk.Frame(
            input_frame,
            borderwidth=3,
            relief=tk.GROOVE
        )
        save_frame.pack(fill="x")

        # Directory information
        delta_dir = LabelledEntry(
            directory_frame,
            self.user_names["delta_root"],
            self.vars["delta_root"],
            pack_side="left",
            inter_pack_side="top",
            w=30,
            text_style="HEAD.TLabel",
            tool_tip_text=DELTA_DIR_TT
        )
        delta_dir.add_directory()

        tmfs_dir = LabelledEntry(
            directory_frame,
            self.user_names["tmfs_root"],
            self.vars["tmfs_root"],
            pack_side="left",
            inter_pack_side="top",
            w=30,
            text_style="HEAD.TLabel",
            tool_tip_text=TMFS_DIR_TT
        )
        tmfs_dir.add_directory()

        # Scenario information
        for scenario in ["Base", "Forecast"]:
            frame = ttk.Frame(scenario_frame, borderwidth=3, relief=tk.GROOVE)
            frame.pack(side="left", fill="x", expand=True)

            ttk.Label(frame, text="{} Scenario".format(scenario),
                      style="HEAD.TLabel").pack()

            for widget in ["year", "id", "scenario"]:
                key = "{}_{}".format(scenario.lower(), widget)
                LabelledEntry(frame, self.user_names[key], self.vars[key],
                              lw=20, w=10, anchor="center")

        # Additional options
        # Add text to explain that these are optional files
        ttk.Label(factor_frame, text="Factor Files (Optional)",
                  style="HEAD.TLabel").pack(anchor="w", padx=10)
        # Add tickbox for home working integration
        ttk.Checkbutton(
            factor_frame,
            text=self.user_names["home_working"],
            variable=self.vars["home_working"]
        ).pack(side="top", anchor="w", padx=10)
        # Add tickbox for using old style of trip rates
        ttk.Checkbutton(
            factor_frame,
            text=self.user_names["old_tr_fmt"],
            variable=self.vars["old_tr_fmt"]
        ).pack(side="top", anchor="w", padx=10)

        for factor_var in ["RTF File", "PTF File", "Airport Growth File"]:
            widget = LabelledEntry(
                factor_frame,
                self.user_names[factor_var],
                self.vars[factor_var],
                pack_side="top",
                inter_pack_side="left",
                w=30,
                lw=30
            )
            widget.add_browse(os.getcwd())

        # Add buttons for exporting/importing settings files
        # Export Button
        ttk.Button(
            save_frame,
            text="Export Settings",
            command=self.export_settings
        ).pack(side="left", fill="x", expand=True)
        # Import Button
        ttk.Button(
            save_frame,
            text="Import Settings",
            command=self.import_settings
        ).pack(side="left", fill="x", expand=True)

        # Add the button to start the Trip End Model
        ttk.Button(
            run_frame,
            text="Generate",
            command=self.callback_run_script,
            style="BIG.TButton"
        ).pack(padx=20, pady=10, fill="x")

        # Create the log text box and progress bar
        ttk.Label(
            log_frame,
            text="Event Log",
            style="HEAD.TLabel"
        ).pack(pady=2)
        self.log = TextLog(log_frame, width=50, height=25)
        self.progress = ttk.Progressbar(
            log_frame,
            length=280,
            mode="indeterminate"
        )
        self.progress.pack(padx=5, pady=5)

    def callback_run_script(self):
        args = {k: x.get() for k, x in self.vars.items()}

        boolean_args = ["rebasing_run", "home_working", "old_tr_fmt"]

        for var_name in args:
            if var_name in boolean_args:
                args[var_name] = bool(int(args[var_name]))
        args = tuple(args.values())

        toggle_widgets(self.main_frame, "disabled")

        self.thread_queue = queue.Queue()
        self.new_thread = threading.Thread(target=telmos_all,
                                           args=args)
        self.new_thread._kwargs = {"thread_queue": self.thread_queue,
                                   "print_func": self.log.add_message}
        self.new_thread.daemon = True
        self.new_thread.start()
        self.progress.start()
        self.after(100, self.listen_for_result)

    def listen_for_result(self):
        # Check if something is in queue
        try:
            exc = self.thread_queue.get(0)
        except queue.Empty:
            self.after(100, self.listen_for_result)
        else:
            # If exception was raised print to the log
            if exc is not None:
                self.log.add_message(
                    "\n".join(traceback.format_exception_only(exc[0], exc[1])),
                    color="RED")
                traceback.print_tb(exc[2])
            toggle_widgets(self.main_frame, "normal")
            self.progress.stop()
            self.new_thread = None

    def export_settings(self):
        """
        Export the current settings to a log file in the corresponding "Runs"
        directory.
        """
        args = {self.user_names[x]: self.vars[x].get()
                for x in self.user_names}
        output_dir = os.path.join(
            self.vars["tmfs_root"].get(),
            "Runs",
            self.vars["forecast_year"].get(),
            "Demand",
            self.vars["forecast_id"].get()
        )
        if not os.path.exists(output_dir):
            output_dir = ""

        file_path = filedialog.asksaveasfilename(
            parent=self.main_frame, title="Save Settings File",
            defaultextension=".json", initialdir=output_dir,
            filetypes=[("JSON files (*.json)", "*.json"), ("All files", "*.*")]
        )
        if file_path == "":
            return

        with open(file_path, "w", newline="") as f:
            json.dump(args, f, indent=4)

        self.log.add_message("Exported Settings to {}".format(file_path))

    def import_settings(self):
        """
        Load a previously exported settings file. Does not check content of
        settings file.
        """
        file_path = filedialog.askopenfilename(
            parent=self.main_frame, title="Select Settings File",
            filetypes=[("JSON files (*.json)", "*.json"), ("All files", "*.*")]
        )
        if file_path == "":
            return

        reverse_user_names = {v: k for k, v in self.user_names.items()}

        with open(file_path, "r") as f:
            settings = json.load(f)
        for u_key in settings:
            try:
                key = reverse_user_names[u_key]
                self.vars[key].set(settings[u_key])
            except KeyError as e:
                self.log.add_message("Setting {} does not exist".format(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)

    root.protocol("WM_DELETE_WINDOW", root.destroy)

    root.mainloop()
