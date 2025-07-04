import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import subprocess

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
def is_mysql_running():
    """Checks if MySQL is running by looking for mysqld.exe in tasklist."""
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

def perform_repair():
    # ✅ Step 0: Check if MySQL is running
    if is_mysql_running():
        messagebox.showwarning("MySQL Running", "⚠️ Please stop MySQL from XAMPP Control Panel before proceeding.")
        return

    mysql_dir = mysql_path.get()
    if not os.path.isdir(mysql_dir):
        messagebox.showerror("Invalid Path", "Selected XAMPP MySQL directory is invalid.")
        return

    log_output(f"🔧 Starting repair at: {mysql_dir}")

    data_dir = os.path.join(mysql_dir, "data")
    backup_dir = os.path.join(mysql_dir, "backup")

    # Step 1: Rename 'data' to 'data_old' or with timestamp
    if os.path.exists(data_dir):
        data_old_dir = os.path.join(mysql_dir, "data_old")
        if os.path.exists(data_old_dir):
            data_old_dir = get_unique_dir(mysql_dir, "data_old")
            log_output(f"⚠️ 'data_old' exists. Renaming to {data_old_dir}")
        else:
            log_output(f"➡️ Renaming 'data' to 'data_old'")
        shutil.move(data_dir, data_old_dir)
    else:
        log_output("❌ 'data' folder not found. Skipping rename.")
        data_old_dir = None

    # Step 2: Copy 'backup' to 'data'
    if os.path.exists(backup_dir):
        shutil.copytree(backup_dir, data_dir)
        log_output("✅ 'backup' copied to 'data'")
    else:
        log_output("❌ 'backup' directory not found.")
        return

    # Step 3: Copy DB folders from old to new
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
        log_output("⚠️ Skipping DB folder copy. No 'data_old' created.")

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

# GUI Setup
root = tk.Tk()
root.title("Techscription Xampp Mechanic!")
root.geometry("700x530")
root.resizable(False, False)

# ---- Logo + Title ----
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

# ---- Options ----
frame = ttk.Frame(root, padding=10)
frame.pack()

path_choice = tk.StringVar(value="default")
mysql_path = tk.StringVar(value="C:/xampp/mysql")

# Radio buttons
ttk.Radiobutton(frame, text="Use Default Path (C:/xampp/mysql)", variable=path_choice,
                value="default", command=toggle_folder_selection).grid(row=0, column=0, sticky="w", columnspan=2)

ttk.Radiobutton(frame, text="Use Custom Path", variable=path_choice,
                value="custom", command=toggle_folder_selection).grid(row=1, column=0, sticky="w", columnspan=2)

select_btn = ttk.Button(frame, text="📁 Select Custom MySQL Path", command=choose_folder)
select_btn.grid(row=2, column=0, sticky="w", pady=8)

path_entry = ttk.Entry(frame, textvariable=mysql_path, width=70)
path_entry.grid(row=3, column=0, columnspan=2, pady=5)

# ---- Repair Button ----
repair_btn = ttk.Button(root, text="🛠️Repair Now", command=perform_repair)
repair_btn.pack(pady=10)

# ---- Output Box ----
output_box = tk.Text(root, height=17, width=85, bg="#f4f4f4", fg="#333", wrap="word")
output_box.pack(padx=10, pady=10)

# Set initial state
toggle_folder_selection()

root.mainloop()
