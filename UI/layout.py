import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import *
import os.path

_location = os.path.dirname(__file__)

_bgcolor = '#919191'
_fgcolor = 'black'

_style_code_ran = 0
def _style_code():
    global _style_code_ran
    if _style_code_ran: 
        return        
    style = ttk.Style()
    style.theme_use('default')  # Use default theme to avoid errors
    style.configure('.', font="TkDefaultFont")
    _style_code_ran = 1

class Toplevel1:
    def __init__(self, top=None):
        '''This class configures and populates the toplevel window.
           top is the toplevel containing window.'''

        top.geometry("592x305+1122+614")
        top.minsize(120, 1)
        top.maxsize(5764, 1421)
        top.resizable(1, 1)
        top.title("Soul Reaver Remastered Exporter")
        top.configure(background="#919191")
        top.configure(highlightbackground="#919191")
        top.configure(highlightcolor="black")

        self.top = top

        # Define StringVars for binding with Entry widgets
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.che52 = tk.IntVar()  # Export All checkbox variable
        self.che56 = tk.IntVar()  # Debug checkbox variable

        self.menubar = tk.Menu(top, font="TkMenuFont", bg='#919191', fg='black')
        top.configure(menu=self.menubar)

        self.BTN_Input = tk.Button(self.top)
        self.BTN_Input.place(relx=0.743, rely=0.23, height=36, width=117)
        self.BTN_Input.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            background="#919191",
            disabledforeground="#6d6d6d",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            text='SRM File / Folder'
        )

        self.BTN_Output = tk.Button(self.top)
        self.BTN_Output.place(relx=0.743, rely=0.361, height=36, width=117)
        self.BTN_Output.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            background="#919191",
            cursor="fleur",
            disabledforeground="#6d6d6d",
            font="-family {Segoe UI} -size 9",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            text='Output Folder'
        )

        self.BTN_Export = tk.Button(self.top)
        self.BTN_Export.place(relx=0.743, rely=0.557, height=36, width=117)
        self.BTN_Export.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            background="#919191",
            cursor="fleur",
            disabledforeground="#6d6d6d",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            text='Export'
        )

        self.BTN_Cancel = tk.Button(self.top)
        self.BTN_Cancel.place(relx=0.777, rely=0.852, height=26, width=77)
        self.BTN_Cancel.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            background="#919191",
            disabledforeground="#6d6d6d",
            font="-family {Segoe UI} -size 9",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            text='Cancel'
        )

        _style_code()
        self.PRG_Bar = ttk.Progressbar(self.top)
        self.PRG_Bar.place(relx=0.051, rely=0.852, relwidth=0.676, height=18)
        self.PRG_Bar.configure(length=400)

        self.ENT_Input = tk.Entry(self.top)
        self.ENT_Input.place(relx=0.051, rely=0.23, height=30, relwidth=0.666)
        self.ENT_Input.configure(
            background="white",
            disabledforeground="#6d6d6d",
            font="TkFixedFont",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            insertbackground="black",
            selectbackground="#d9d9d9",
            selectforeground="black",
            textvariable=self.input_path
        )

        self.ENT_Output = tk.Entry(self.top)
        self.ENT_Output.place(relx=0.051, rely=0.361, height=30, relwidth=0.666)
        self.ENT_Output.configure(
            background="white",
            disabledforeground="#6d6d6d",
            font="-family {Courier New} -size 10",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            insertbackground="black",
            selectbackground="#d9d9d9",
            selectforeground="black",
            textvariable=self.output_path
        )

        self.LBL_Title = tk.Label(self.top)
        self.LBL_Title.place(relx=0.304, rely=0.098, height=21, width=204)
        self.LBL_Title.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            anchor='w',
            background="#919191",
            compound='left',
            disabledforeground="#6d6d6d",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            text='Soul Reaver Remastered Exporter'
        )

        self.CHK_Batch = tk.Checkbutton(self.top)
        self.CHK_Batch.place(relx=0.051, rely=0.525, relheight=0.056, relwidth=0.285)
        self.CHK_Batch.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            anchor='w',
            background="#919191",
            compound='left',
            disabledforeground="#6d6d6d",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            justify='left',
            text='Export All Files in Folder',
            variable=self.che52
        )

        self.CHK_Debug = tk.Checkbutton(self.top)
        self.CHK_Debug.place(relx=0.051, rely=0.59, relheight=0.082, relwidth=0.255)
        self.CHK_Debug.configure(
            activebackground="#d9d9d9",
            activeforeground="black",
            anchor='w',
            background="#919191",
            compound='left',
            disabledforeground="#6d6d6d",
            foreground="black",
            highlightbackground="#919191",
            highlightcolor="black",
            justify='left',
            text='Output Debug Text',
            variable=self.che56
        )

        # Collect widgets into a dictionary for easy access
        self.widgets = {
            "ENT_Input": self.ENT_Input,
            "ENT_Output": self.ENT_Output,
            "BTN_Input": self.BTN_Input,
            "BTN_Output": self.BTN_Output,
            "CHK_ExportAll": self.CHK_Batch,
            "BTN_Export": self.BTN_Export,
            "BTN_Cancel": self.BTN_Cancel,
            "CHK_Debug": self.CHK_Debug,
            "Progress": self.PRG_Bar,
        }
