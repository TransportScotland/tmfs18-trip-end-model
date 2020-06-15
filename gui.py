# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 11:35:25 2019

@author: japeach
"""

import tkinter as tk 
from tkinter import ttk
import threading
import queue
import traceback
from telmos_script import telmos_all
from widget_templates import LabelledEntry, CreateToolTip, TextLog

class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TMfS18 Trip End Model")
        var_names = ["delta_root","tmfs_root", "tel_year", "tel_id", "tel_scenario", 
                     "base_year", "base_id", "base_scenario"]
        extra_var_names = ["rebasing_run"]
        var_defaults = ['Data/Structure/delta_root', 
                         'Data/Structure/tmfs_root', 
                         '', '', '', 
                         '18', 'ADL', 'DL', 
                         0, 1, 0]
        self.extra_var_defaults = {name:tk.IntVar() for name in extra_var_names}
        self.vars = {name:tk.StringVar() for name in var_names}
        self.vars = {**self.vars, **self.extra_var_defaults}
        for key, value in zip(self.vars, var_defaults):
            self.vars[key].set(value)
        
        self.init_widgets()
        self.root.resizable(height=False, width=False)
        
        
    def init_widgets(self):
        main_frame = ttk.Frame(self.root)
        log_frame = ttk.Frame(self.root)
        main_frame.pack(side="left")
        log_frame.pack(side="left")
        title_frame = ttk.Frame(main_frame, borderwidth=3, relief=tk.GROOVE)
        input_frame = ttk.Frame(main_frame)
        run_frame = ttk.Frame(main_frame)
        
        style = ttk.Style()
        # Headers style
        style.configure("HEAD.TLabel", font=("Helvetica", 10, "bold"))
        
        # Title and explanation
        title_frame.pack(fill="x", padx=5, pady=5)
        style.configure("TIT.TLabel", font=("Helvetica", 16, "bold"))
        title = ttk.Label(title_frame, text="TMfS18 Trip End Model", 
                          style="TIT.TLabel")
        title.pack()
        sub_text = "Conversion of the VB TMfS14 trip end model"
        sub_title = ttk.Label(title_frame, text=sub_text)
        sub_title.pack()
        
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
        delta_dir = LabelledEntry(directory_frame, "Delta Root Directory", 
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
        tmfs_dir = LabelledEntry(directory_frame, "TMfS Root Directory", 
                                  self.vars["tmfs_root"],
                                  pack_side="left", inter_pack_side="top",
                                  w=30, text_style="HEAD.TLabel",
                                  tool_tip_text=tmfs_dir_tt)
        tmfs_dir.add_directory()
        # Scenario information
        scenario_frame = ttk.Frame(input_frame)
        scenario_frame.pack(fill="x")
        base_frame = ttk.Frame(scenario_frame, borderwidth=3, relief=tk.GROOVE)
        base_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(base_frame, text="Base Scenario", style="HEAD.TLabel").pack()
        LabelledEntry(base_frame, "Year", self.vars["base_year"], lw=10, 
                      w=10, anchor="center", tool_tip_text="Base scenario year")
        LabelledEntry(base_frame, "ID", self.vars["base_id"], lw=10, 
                      w=10, anchor="center", tool_tip_text="Base scenario ID")
        LabelledEntry(base_frame, "Scenario", self.vars["base_scenario"], 
                      lw=10, w=10, anchor="center", 
                      tool_tip_text="Base scenario name")
        tel_frame = ttk.Frame(scenario_frame, borderwidth=3, relief=tk.GROOVE)
        tel_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(tel_frame, text="Tel Scenario", style="HEAD.TLabel").pack()
        LabelledEntry(tel_frame, "Year", self.vars["tel_year"], lw=10, 
                      w=10, anchor="center", tool_tip_text="Future scenario year")
        LabelledEntry(tel_frame, "ID", self.vars["tel_id"], lw=10, 
                      w=10, anchor="center", tool_tip_text="Future scenario ID")
        LabelledEntry(tel_frame, "Scenario", self.vars["tel_scenario"], 
                      lw=10, w=10, anchor="center", 
                      tool_tip_text="Future scenario name")
        # Additional options
        options_frame = ttk.Frame(input_frame, borderwidth=3, relief=tk.GROOVE)
        options_frame.pack(fill="x")
        rebasing = ttk.Checkbutton(options_frame, text="Rebasing Run",
                                   variable=self.vars["rebasing_run"])
        CreateToolTip(rebasing, text="Tick if a rebasing run is required")
        rebasing.pack(side="left", padx=5)
        
        # Execute frame
        run_frame.pack(fill="x")
        style.configure("BIG.TButton", font=("Helvetica", 12, "bold"))
        self.b = ttk.Button(run_frame, text="Generate", command=self.callback_run_script,
                   style="BIG.TButton")
        self.b.pack(padx=20, pady=10, fill="x")
        
        # Log Frame
        ttk.Label(log_frame, text="Event Log", style="HEAD.TLabel").pack(pady=2)
        self.log = TextLog(log_frame, width=50, height=20)
        
        
        
    def callback_run_script(self):
        args = [x.get() for x in self.vars.values()]
        for i in range(len(args)):
            if args[i] == 0 or args[i] == 1:
                args[i] = bool(args[i])
        args = tuple(args)
        
        self.b["state"] = "disabled"
        
        self.thread_queue = queue.Queue()
        self.new_thread = threading.Thread(target=telmos_all,
                                           args=args)
        self.new_thread._kwargs = {"thread_queue":self.thread_queue,
                                   "print_func":self.log.add_message}
        self.new_thread.start()
        self.root.after(100, self.listen_for_result)
        
    def listen_for_result(self):
        # Check if something is in queue
        try:
            exc = self.thread_queue.get(0)
            # terminated
            self.b["state"] = "normal"
        except queue.Empty:
            self.root.after(100, self.listen_for_result)
        else:
            # If exception was raised print to the log
            if exc is not None:
                self.log.add_message(
                        "\n".join(traceback.format_exception_only(exc[0], exc[1])),
                        color="RED")
                traceback.print_tb(exc[2])
            self.b["state"] = "normal"
        #self.new_thread.join(0.1)
        
        

if __name__ == "__main__":
    app = Application()
    app.root.mainloop()