import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import *
from tkinter import filedialog
from pathlib import Path
import fbx

from UI import layout
from ConvertSRM import convert_srm_to_fbx

_debug = True  # Set to False to disable debug prints

def on_click_input():
    path = filedialog.askopenfilename(
        title="Select SRM File",
        filetypes=[("SRM Files", "*.srm"), ("All Files", "*.*")]
    )
    if path:
        _w1.input_path.set(path)
        if _debug: print(f"[DEBUG] Selected input: {path}")

def on_click_output():
    folder = filedialog.askdirectory(title="Select Output Folder")
    if folder:
        _w1.output_path.set(folder)
        if _debug: print(f"[DEBUG] Selected output: {folder}")

def on_click_export():
    _w1.export_cancelled = False
    _w1.widgets["BTN_Export"].configure(state="disabled")

    input_path_str = _w1.input_path.get()
    output_folder_str = _w1.output_path.get()
    export_all = _w1.che52.get() == 1
    write_debug_log = _w1.che56.get() == 1

    if not input_path_str or not output_folder_str:
        print("Input or output path is empty. Please select paths.")
        _w1.widgets["BTN_Export"].configure(state="normal")
        return

    input_path = Path(input_path_str)
    output_folder = Path(output_folder_str)
    if not output_folder.exists():
        print(f"Output folder does not exist: {output_folder}")
        _w1.widgets["BTN_Export"].configure(state="normal")
        return

    if export_all and input_path.is_file():
        srm_files = list(input_path.parent.glob("*.srm"))
        if _debug: print(f"[DEBUG] Exporting all {len(srm_files)} SRM files from {input_path.parent}")
    elif input_path.is_file():
        srm_files = [input_path]
        if _debug: print(f"[DEBUG] Exporting single SRM file: {input_path}")
    else:
        print("Please select a valid SRM file as input.")
        _w1.widgets["BTN_Export"].configure(state="normal")
        return

    total_files = len(srm_files)
    _w1.PRG_Bar['maximum'] = total_files
    _w1.PRG_Bar['value'] = 0

    log_lines = ["Export debug log\n"]

    manager = fbx.FbxManager.Create()
    if not manager:
        print("Failed to create FBX manager.")
        _w1.widgets["BTN_Export"].configure(state="normal")
        return

    for idx, srm_file in enumerate(srm_files, start=1):
        if _w1.export_cancelled:
            print("Export cancelled by user.")
            log_lines.append("Export cancelled by user.\n")
            break

        log_lines.append(f"Starting export of: {srm_file}\n")
        if _debug:
            print(f"[DEBUG] Starting export of: {srm_file}")

        scene = convert_srm_to_fbx(srm_file, manager)
        if scene is None:
            error_msg = f"Failed to convert {srm_file.name}\n"
            print(error_msg)
            log_lines.append(error_msg)
            continue

        output_file = output_folder / (srm_file.stem + ".fbx")

        exporter = fbx.FbxExporter.Create(manager, "")
        if not exporter.Initialize(str(output_file), -1, manager.GetIOSettings()):
            error_msg = f"Failed to initialize exporter for {output_file}\n"
            print(error_msg)
            log_lines.append(error_msg)
            exporter.Destroy()
            continue

        if not exporter.Export(scene):
            error_msg = f"Failed to export {output_file}\n"
            print(error_msg)
            log_lines.append(error_msg)
            exporter.Destroy()
            continue

        exporter.Destroy()

        log_lines.append(f"Exported {output_file}\n")
        if _debug:
            print(f"[DEBUG] Exported {output_file}")

        _w1.PRG_Bar['value'] = idx
        _w1.top.update()

    manager.Destroy()

    if write_debug_log:
        debug_log_path = output_folder / "export_debug_log.txt"
        try:
            with open(debug_log_path, "w", encoding="utf-8") as f:
                f.writelines(log_lines)
            print(f"[DEBUG] Export debug log written to {debug_log_path}")
        except Exception as e:
            print(f"Failed to write debug log: {e}")

    _w1.widgets["BTN_Export"].configure(state="normal")
    _w1.PRG_Bar['value'] = 0

def on_click_cancel():
    if _debug:
        print("[DEBUG] Cancel button clicked")
    _w1.export_cancelled = True

def main(*args):
    '''Main entry point for the application.'''
    global root, _top1, _w1
    root = tk.Tk()
    root.protocol('WM_DELETE_WINDOW', root.destroy)

    _top1 = root
    _w1 = layout.Toplevel1(_top1)

    # Initialize cancel flag
    _w1.export_cancelled = False

    # Hook up the buttons
    _w1.widgets["BTN_Input"].configure(command=on_click_input)
    _w1.widgets["BTN_Output"].configure(command=on_click_output)
    _w1.widgets["BTN_Export"].configure(command=on_click_export)
    _w1.widgets["BTN_Cancel"].configure(command=on_click_cancel)

    root.mainloop()

if __name__ == '__main__':
    main()
