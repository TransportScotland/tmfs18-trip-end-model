# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 11:35:25 2019

@author: japeach
"""

import tkinter as tk 
from tkinter import ttk, filedialog
import csv
import json
import os
import threading
import queue
import traceback
from webbrowser import open_new
from telmos_script import telmos_all
from widget_templates import LabelledEntry, CreateToolTip, TextLog


REBASING_RUN = 0


def toggle_widgets(base, target_state):
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
        self.var_names = ["delta_root","tmfs_root", "forecast_year", 
                          "forecast_id", "forecast_scenario", 
                     "base_year", "base_id", "base_scenario",
                     "RTF File", "PTF File", "Airport Growth File"]
        user_friendly_names = ["Delta Root Directory", "TMfS Root Directory",
                               "Forecast Year", "Forecast ID", "Forecast Scenario",
                               "Base Year", "Base ID", "Base Scenario",
                               "RTF File", "PTF File", "Airport Growth File"]
        self.user_names = {var:name for var, name in zip(
                self.var_names, user_friendly_names)}
        extra_var_names = ["rebasing_run"]
        var_defaults = ['Data/Structure/delta_root', 
                         'Data/Structure/tmfs_root', 
                         '', '', '', 
                         '18', 'ADL', 'DL', 
                         "", "", "",
                         REBASING_RUN]
        self.extra_var_defaults = {name:tk.IntVar() for name in extra_var_names}
        self.vars = {name:tk.StringVar() for name in self.var_names}
        self.vars = {**self.vars, **self.extra_var_defaults}
        for key, value in zip(self.vars, var_defaults):
            self.vars[key].set(value)
        
        self.new_thread = None
        self.init_widgets(parent)
        parent.resizable(height=False, width=False)
        
        
    def init_widgets(self, parent):
        self.main_frame = ttk.Frame(parent)
        log_frame = ttk.Frame(parent)
        self.main_frame.pack(side="left")
        log_frame.pack(side="left")
        title_frame = ttk.Frame(self.main_frame, borderwidth=3, relief=tk.GROOVE)
        input_frame = ttk.Frame(self.main_frame)
        run_frame = ttk.Frame(self.main_frame)
        
        style = ttk.Style()
        # Headers style
        style.configure("HEAD.TLabel", font=("Helvetica", 10, "bold"))
        
        # Title and explanation
        title_frame.pack(fill="x", padx=5, pady=5)
        style.configure("TIT.TLabel", font=("Helvetica", 16, "bold"))
        title = ttk.Label(title_frame, text="TMfS18 Trip End Model", 
                          style="TIT.TLabel")
        title.pack()
        sub_text = (
        "This tool uses TELMoS planning data and trip rates from NTEM to apply "
        "growth to the calibrated forecast trip ends that are input to the demand model "
        "of the Transport Model for Scotland (TMfS). "
        "The trip end files produced by this tool should be run through the"
        "Cube smoothing process.")
        sub_title = ttk.Label(title_frame, text=sub_text, wraplength=500)
        sub_title.pack(fill="x", padx=5, pady=5)
        github_releases_link = ("https://github.com/TransportScotland/"
                                "tmfs18-trip-end-model/releases")
        github_link = ttk.Button(title_frame, text="Check for Newer Releases", 
                                 command=lambda : open_new(
                                         github_releases_link))
        github_link.pack(anchor="w", padx=5, pady=5)
        
        # User input frame
        # Split into directory selection, scenario definition and other options
        input_frame.pack(fill="x", expand=True, padx=5, pady=5)
        
        # Directory information
        directory_frame = ttk.Frame(input_frame, borderwidth=3, relief=tk.GROOVE)
        directory_frame.pack()
        delta_dir_tt = ("Has sub-directories containing the TELMoS planning data csv files "
                        "and goods dat files. Folders and files should be named according to the "
                        "year and scenario code.\n"
                        "E.g. DELTA\\DL\\{PlanningData} where DELTA is the directory "
                        "to be selected and DL is one of the scenario codes.\n"
                        "See the README for info on the required planning data." )
        delta_dir = LabelledEntry(directory_frame, self.user_names["delta_root"], 
                                  self.vars["delta_root"],
                                  pack_side="left", inter_pack_side="top",
                                  w=30, text_style="HEAD.TLabel",
                                  tool_tip_text=delta_dir_tt)
        delta_dir.add_directory()
        tmfs_dir_tt = ("Contains the 'Factors' folder and the 'Runs' folder.\n"
                       "'Factors' contains all internal factor files used by the model\n"
                       "'Runs' contains the base year trip ends and is where the model "
                       "will output the new trip ends.\n"
                       "E.g. TMFS\\Factors\\{FactorsFiles}; and "
                       "TMFS\\Runs\\18\\Demand\\ADL\\{TripEndFiles} where TMFS "
                       "is the directory to be selected, 18 is the base year "
                       "and ADL is the base ID. An empty directory should also be "
                       "created for the forecast year\n"
                       "See the README for info on the required factors files.")
        tmfs_dir = LabelledEntry(directory_frame, self.user_names["tmfs_root"], 
                                  self.vars["tmfs_root"],
                                  pack_side="left", inter_pack_side="top",
                                  w=30, text_style="HEAD.TLabel",
                                  tool_tip_text=tmfs_dir_tt)
        tmfs_dir.add_directory()
        # Scenario information
        scenario_frame = ttk.Frame(input_frame)
        scenario_frame.pack(fill="x")
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
        
        factor_frame = ttk.Frame(input_frame, borderwidth=3, relief=tk.GROOVE)
        # Add text to explain that these are optional files
        ttk.Label(factor_frame, text="Factor Files (Optional)", 
                  style="HEAD.TLabel").pack(anchor="w", padx=10)
        for factor_var in ["RTF File", "PTF File", "Airport Growth File"]:
            widget = LabelledEntry(factor_frame, self.user_names[factor_var], 
                                  self.vars[factor_var],
                                  pack_side="top", inter_pack_side="left",
                                  w=30, lw=30)
            widget.add_browse(os.getcwd())
        factor_frame.pack(anchor="w", fill="x", expand=True)
        
        options_frame = ttk.Frame(input_frame, borderwidth=3, relief=tk.GROOVE)
        options_frame.pack(fill="x")
        ttk.Button(options_frame, text="Export Settings",
                   command=self.export_settings).pack(side="left", fill="x", 
                                               expand=True)
        ttk.Button(options_frame, text="Import Settings",
                   command=self.import_settings).pack(side="left", fill="x",
                                               expand=True)
        
        # Execute frame
        run_frame.pack(fill="x")
        style.configure("BIG.TButton", font=("Helvetica", 12, "bold"))
        b = ttk.Button(run_frame, text="Generate", command=self.callback_run_script,
                   style="BIG.TButton")
        b.pack(padx=20, pady=10, fill="x")
        
        
        
        # Log Frame
        ttk.Label(log_frame, text="Event Log", style="HEAD.TLabel").pack(pady=2)
        self.log = TextLog(log_frame, width=50, height=25)
        self.progress = ttk.Progressbar(log_frame, length=280, 
                                        mode="indeterminate")
        self.progress.pack(padx=5, pady=5)
        
        
        
    def callback_run_script(self):
        args = [x.get() for x in self.vars.values()]
        for i in range(len(args)):
            if args[i] == 0 or args[i] == 1:
                args[i] = bool(args[i])
        args = tuple(args)
        
        toggle_widgets(self.main_frame, "disabled")
        
        self.thread_queue = queue.Queue()
        self.new_thread = threading.Thread(target=telmos_all,
                                           args=args)
        self.new_thread._kwargs = {"thread_queue":self.thread_queue,
                                   "print_func":self.log.add_message}
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
        args = {self.user_names[x]:self.vars[x].get() for x in self.user_names}
        output_dir = os.path.join(self.vars["tmfs_root"].get(), "Runs", 
                                  self.vars["forecast_year"].get(), "Demand", 
                                  self.vars["forecast_id"].get())
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
            json.dump(args, f)
            
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
        
        reverse_user_names = {v:k for k, v in self.user_names.items()}
        
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
