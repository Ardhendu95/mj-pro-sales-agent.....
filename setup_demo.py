"""Private local setup window. No credentials are printed or sent anywhere."""
import hashlib
import secrets
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parent

def hash_password(password):
    salt = secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + value

def main():
    path = ROOT / '.env'
    existing = dotenv_values(path) if path.exists() else {}
    window = tk.Tk()
    window.title('mjPROConnect — Private setup')
    window.geometry('600x620')
    window.minsize(480, 570)
    window.configure(background='#f3f6fa')
    style = ttk.Style(window)
    style.configure('TLabel', font=('Segoe UI', 11))
    style.configure('TButton', font=('Segoe UI', 11), padding=8)
    style.configure('TCheckbutton', font=('Segoe UI', 10))
    frame = ttk.Frame(window, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Connect your Gemini key', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='These details stay in your private local setup file.\nThis window does not make any Google requests.', wraplength=530).pack(anchor='w', pady=(8,18))
    entries = {}
    labels = [
        ('password', 'Admin password (12+ characters)' + (' — optional change' if existing.get('ADMIN_PASSWORD_HASH') else '')),
        ('repeat', 'Repeat the admin password'),
        ('key', 'Gemini API key' + (' — leave blank to keep current key' if existing.get('GEMINI_API_KEY') else ' — paste here')),
    ]
    for name, label in labels:
        ttk.Label(frame, text=label, wraplength=530).pack(anchor='w', pady=(8,4))
        entry = ttk.Entry(frame, show='●', font=('Segoe UI',12))
        entry.pack(fill='x', ipady=5)
        entries[name] = entry
    show_key = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text='Show API key on this screen', variable=show_key,
                    command=lambda: entries['key'].configure(show='' if show_key.get() else '●')).pack(anchor='w', pady=(8,14))
    confirmed = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text='I confirmed billing is disabled for this Google project.', variable=confirmed).pack(anchor='w')
    ttk.Label(frame, text='Check this in Google AI Studio before ticking the box.\nYou can save the admin password now and add a key later.', wraplength=530, font=('Segoe UI',10)).pack(anchor='w', pady=(6,14))
    status = tk.StringVar(value='Password dots appear as you type. Paste the key with Ctrl+V.')
    ttk.Label(frame, textvariable=status, wraplength=530, foreground='#145cb0').pack(anchor='w', pady=(0,12))
    saved = False
    def save():
        nonlocal saved
        password = entries['password'].get()
        repeat = entries['repeat'].get()
        key = entries['key'].get().strip()
        if password or repeat or not existing.get('ADMIN_PASSWORD_HASH'):
            if len(password)<12 or password!=repeat:
                status.set('Use at least 12 characters and repeat the same password.'); entries['password'].focus_set(); return
        if key and not confirmed.get():
            status.set('Confirm that billing is disabled before saving a Gemini key.'); return
        try:
            if not path.exists(): path.write_text('', encoding='utf-8')
            if password:
                set_key(str(path), 'ADMIN_USERNAME', 'admin')
                set_key(str(path), 'ADMIN_PASSWORD_HASH', hash_password(password))
            if key:
                set_key(str(path), 'GEMINI_API_KEY', key)
                set_key(str(path), 'GOOGLE_FREE_PROJECT_CONFIRMED', 'true')
            defaults = {'GEMINI_MODEL':'gemini-3.1-flash-lite', 'GEMINI_EMBED_MODEL':'gemini-embedding-001', 'MAX_DAILY_AI_CALLS':'100'}
            for name,value in defaults.items():
                if not existing.get(name): set_key(str(path),name,value)
        except Exception:
            status.set('Could not save the local setup. Keep this window open and ask for help.'); return
        saved = True
        for entry in entries.values(): entry.delete(0, 'end')
        messagebox.showinfo('Saved privately', 'Setup saved on this computer.\n\nNext: double-click START-DEMO.cmd in the project folder.\nSign in as admin, check Gemini, and re-index approved content.', parent=window)
        window.destroy()
    ttk.Button(frame, text='Save private setup', command=save).pack(anchor='w')
    entries['password' if not existing.get('ADMIN_PASSWORD_HASH') else 'key'].focus_set()
    window.mainloop()
    return 0 if saved else 1

if __name__ == '__main__':
    raise SystemExit(main())
