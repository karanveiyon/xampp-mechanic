import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import subprocess


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # For PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def is_mysql_running():
    try:
        tasklist = subprocess.check_output("tasklist", shell=True).decode().lower()
        return "mysqld.exe" in tasklist
    except Exception as e:
        log_output(f"⚠️ Error checking MySQL status: {e}")
        return False


def get_unique_dir(base_path, base_name):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    candidate = os.path.join(base_path, f"{base_name}_{timestamp}")
    while os.path.exists(candidate):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        candidate = os.path.join(base_path, f"{base_name}_{timestamp}")
        time.sleep(1)
    return candidate


def log_output(msg):
    output_box.insert(tk.END, msg + '\n')
    output_box.see(tk.END)


def run_netstat(port, output_text):
    try:
        result = subprocess.check_output(f'netstat -aon | findstr :{port}', shell=True, text=True)
    except subprocess.CalledProcessError:
        result = f"No active connections found on port {port}"
    output_text.config(state='normal')
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, result)
    output_text.config(state='disabled')


def kill_pid(pid_input, output_text, dialog):
    pid = pid_input.get().strip()
    if not pid:
        messagebox.showerror("Error", "Please enter a valid PID.")
        return
    try:
        subprocess.check_call(f'taskkill /PID {pid} /F', shell=True)
        messagebox.showinfo("Success", f"Process {pid} has been terminated.")
        dialog.destroy()
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", f"Failed to kill PID {pid}.")


def show_port_dialog():
    dialog = tk.Toplevel(root)
    dialog.title("Check Port Usage")
    dialog.geometry("650x450")

    # Port + Find button frame
    port_frame = tk.Frame(dialog)
    port_frame.pack(pady=10)

    port_label = tk.Label(port_frame, text="Enter Port:")
    port_label.pack(side=tk.LEFT, padx=5)

    port_input = tk.Entry(port_frame, width=10)
    port_input.insert(0, "3306")
    port_input.pack(side=tk.LEFT)

    output_text = tk.Text(dialog, height=12, state='disabled')
    output_text.pack(pady=10, fill=tk.BOTH, expand=True)

    scroll = tk.Scrollbar(dialog, command=output_text.yview)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    output_text.config(yscrollcommand=scroll.set)

    find_btn = tk.Button(port_frame, text="Find 🔍", command=lambda: run_netstat(port_input.get(), output_text))
    find_btn.pack(side=tk.LEFT, padx=5)

    pid_label = tk.Label(dialog, text="Enter PID to Stop:")
    pid_label.pack(pady=5)

    pid_input = tk.Entry(dialog)
    pid_input.pack(pady=5)

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)

    stop_btn = tk.Button(btn_frame, text="Stop", command=lambda: kill_pid(pid_input, output_text, dialog))
    stop_btn.pack(side=tk.LEFT, padx=5)


def perform_repair():
    if is_mysql_running():
        proceed = messagebox.askyesno("MySQL is Running", "⚠️ MySQL appears to be running.\n\nDo you want to proceed and stop the process manually?")
        if proceed:
            show_port_dialog()
            return  # Wait for user to kill manually before proceeding
        else:
            messagebox.showinfo("Aborted", "Operation cancelled by user.")
            return

    mysql_dir = mysql_path.get()
    if not os.path.isdir(mysql_dir):
        messagebox.showerror("Invalid Path", "Selected XAMPP MySQL directory is invalid.")
        return

    log_output(f"🔧 Starting repair at: {mysql_dir}")

    data_dir = os.path.join(mysql_dir, "data")
    backup_dir = os.path.join(mysql_dir, "backup")

    # Step 1: Rename data folder
    if os.path.exists(data_dir):
        data_old_dir = os.path.join(mysql_dir, "data_old")
        if os.path.exists(data_old_dir):
            data_old_dir = get_unique_dir(mysql_dir, "data_old")
            log_output(f"⚠️ 'data_old' exists. Renaming to {data_old_dir}")
        else:
            log_output(f"➡️ Renaming 'data' to 'data_old'")
        shutil.move(data_dir, data_old_dir)
    else:
        log_output("❌ 'data' folder not found.")
        data_old_dir = None

    # Step 2: Copy backup to data
    if os.path.exists(backup_dir):
        shutil.copytree(backup_dir, data_dir)
        log_output("✅ 'backup' copied to 'data'")
    else:
        log_output("❌ 'backup' directory not found.")
        return

    # Step 3: Copy old DBs (excluding system folders)
    if data_old_dir:
        exclude = {"mysql", "performance_schema", "phpmyadmin"}
        for item in os.listdir(data_old_dir):
            src = os.path.join(data_old_dir, item)
            dst = os.path.join(data_dir, item)
            if os.path.isdir(src) and item not in exclude:
                if os.path.exists(dst):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    log_output(f"📁 Merged {item} into 'data'")
                else:
                    shutil.copytree(src, dst)
                    log_output(f"📁 Copied {item} to 'data'")
        ibdata1 = os.path.join(data_old_dir, "ibdata1")
        if os.path.exists(ibdata1):
            shutil.copy2(ibdata1, data_dir)
            log_output("✅ 'ibdata1' copied successfully.")
        else:
            log_output("⚠️ 'ibdata1' not found in 'data_old'.")
    else:
        log_output("⚠️ No 'data_old' created. Skipping DB copy.")

    log_output("✅ Repair completed successfully!")


def choose_folder():
    path = filedialog.askdirectory(title="Select XAMPP MySQL Directory")
    if path:
        mysql_path.set(path)


def toggle_folder_selection():
    if path_choice.get() == "default":
        mysql_path.set("C:/xampp/mysql")
        select_btn.configure(state="disabled")
    else:
        mysql_path.set("")
        select_btn.configure(state="normal")


# 🔵 MAIN GUI
root = tk.Tk()
root.title("Techscription Xampp Mechanic!")
root.geometry("700x530")
root.resizable(False, False)

# Title + Logo
title_frame = tk.Frame(root)
title_frame.pack(pady=10)

try:
    logo_img = Image.open(get_resource_path("xampp_mechanic.png"))
    logo_img = logo_img.resize((40, 40), Image.LANCZOS)
    logo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(title_frame, image=logo)
    logo_label.pack(side=tk.LEFT, padx=10)
except Exception as e:
    print("Logo load failed:", e)

title_label = tk.Label(title_frame, text="Techscription Xampp Mechanic!", font=("Segoe UI", 16, "bold"))
title_label.pack(side=tk.LEFT)

# Path selection
frame = ttk.Frame(root, padding=10)
frame.pack()

path_choice = tk.StringVar(value="default")
mysql_path = tk.StringVar(value="C:/xampp/mysql")

ttk.Radiobutton(frame, text="Use Default Path (C:/xampp/mysql)", variable=path_choice,
                value="default", command=toggle_folder_selection).grid(row=0, column=0, sticky="w", columnspan=2)

ttk.Radiobutton(frame, text="Use Custom Path", variable=path_choice,
                value="custom", command=toggle_folder_selection).grid(row=1, column=0, sticky="w", columnspan=2)

select_btn = ttk.Button(frame, text="📁 Select Custom MySQL Path", command=choose_folder)
select_btn.grid(row=2, column=0, sticky="w", pady=8)

path_entry = ttk.Entry(frame, textvariable=mysql_path, width=70)
path_entry.grid(row=3, column=0, columnspan=2, pady=5)

# Repair button
repair_btn = ttk.Button(root, text="🛠️ Repair Now", command=perform_repair)
repair_btn.pack(pady=10)

# Output display
output_box = tk.Text(root, height=17, width=85, bg="#f4f4f4", fg="#333", wrap="word")
output_box.pack(padx=10, pady=10)

# Initialize state
toggle_folder_selection()

root.mainloop()
