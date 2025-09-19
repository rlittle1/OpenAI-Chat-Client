import os
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog, filedialog
from openai import OpenAI
import unicodedata
import re
import threading
from pathlib import Path
from datetime import datetime

# --- Configuration ---
API_KEY = os.getenv("OPENAI_API_KEY")

# Don't exit immediately if no API key - let user set it through the UI
client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY)

# Ensure chats folder exists in the user's Documents directory
CHAT_DIR = Path.home() / "Documents" / "chats"
CHAT_DIR.mkdir(parents=True, exist_ok=True)

# --- Text cleaning ---
def clean_text_aggressive(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    invisible_chars = ["\u200B","\u200C","\u200D","\uFEFF","\u202F","\u2060","\u180E"]
    for ch in invisible_chars:
        text = text.replace(ch, "")
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)
    return text.strip()

# --- Functions ---
current_conversation = None
is_processing = False

def set_api_key():
    """Open dialog to set OpenAI API key"""
    global client, API_KEY
    
    # Create a custom dialog
    dialog = tk.Toplevel(root)
    dialog.title("Set OpenAI API Key")
    dialog.geometry("550x350")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (550 // 2)
    y = (dialog.winfo_screenheight() // 2) - (350 // 2)
    dialog.geometry(f"550x350+{x}+{y}")
    
    # Instructions
    instruction_frame = ttk.Frame(dialog)
    instruction_frame.pack(fill=tk.X, padx=20, pady=20)
    
    ttk.Label(instruction_frame, text="OpenAI API Key Setup", font=("Arial", 14, "bold")).pack(anchor="w")
    ttk.Label(instruction_frame, text="Enter your OpenAI API key to use this chat application.", font=("Arial", 10)).pack(anchor="w", pady=(5, 0))
    
    ttk.Label(instruction_frame, text="• Get your API key from: https://platform.openai.com/api-keys", font=("Arial", 9)).pack(anchor="w", pady=(10, 0))
    ttk.Label(instruction_frame, text="• Your key starts with 'sk-' followed by a long string", font=("Arial", 9)).pack(anchor="w", pady=(2, 0))
    ttk.Label(instruction_frame, text="• Keep your API key secure and don't share it", font=("Arial", 9)).pack(anchor="w", pady=(2, 0))
    
    # API key entry
    entry_frame = ttk.Frame(dialog)
    entry_frame.pack(fill=tk.X, padx=20, pady=10)
    
    ttk.Label(entry_frame, text="API Key:", font=("Arial", 10, "bold")).pack(anchor="w")
    
    api_key_var = tk.StringVar()
    if API_KEY:
        # Show partial key for security (first 7 chars + ... + last 4 chars)
        if len(API_KEY) > 15:
            masked_key = API_KEY[:7] + "..." + API_KEY[-4:]
        else:
            masked_key = "sk-..." + API_KEY[-4:] if API_KEY.startswith("sk-") else API_KEY
        api_key_var.set(masked_key)
    
    key_entry = ttk.Entry(entry_frame, textvariable=api_key_var, width=60, show="*")
    key_entry.pack(fill=tk.X, pady=(5, 0))
    
    # Status label
    status_var = tk.StringVar()
    status_label = ttk.Label(entry_frame, textvariable=status_var, font=("Arial", 9))
    status_label.pack(anchor="w", pady=(5, 0))
    
    if API_KEY:
        status_var.set("✓ API key is currently set")
        status_label.config(foreground="green")
    else:
        status_var.set("⚠ No API key set - required to use the application")
        status_label.config(foreground="red")
    
    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=20, pady=20)
    
    def save_api_key():
        global client, API_KEY
        new_key = api_key_var.get().strip()
        
        # If showing masked key and user didn't change it, don't update
        if API_KEY and new_key.startswith(API_KEY[:7]) and new_key.endswith(API_KEY[-4:]) and "..." in new_key:
            dialog.destroy()
            return
            
        if not new_key:
            status_var.set("⚠ Please enter your API key")
            status_label.config(foreground="red")
            return
            
        if not new_key.startswith("sk-"):
            status_var.set("⚠ API key should start with 'sk-'")
            status_label.config(foreground="red")
            return
            
        if len(new_key) < 20:
            status_var.set("⚠ API key appears to be too short")
            status_label.config(foreground="red")
            return
        
        try:
            # Test the API key by creating a client
            test_client = OpenAI(api_key=new_key)
            
            # Try a minimal API call to validate the key
            test_response = test_client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
            
            # If we get here, the key works
            API_KEY = new_key
            client = test_client
            
            # Set environment variable for current session
            os.environ["OPENAI_API_KEY"] = new_key
            
            # Try to save to a .env file for persistence
            try:
                env_file = ".env"
                env_content = ""
                
                # Read existing .env file if it exists
                if os.path.exists(env_file):
                    with open(env_file, "r") as f:
                        lines = f.readlines()
                    
                    # Update existing OPENAI_API_KEY line or keep other lines
                    updated = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith("OPENAI_API_KEY="):
                            lines[i] = f"OPENAI_API_KEY={new_key}\n"
                            updated = True
                            break
                    
                    if updated:
                        env_content = "".join(lines)
                    else:
                        env_content = "".join(lines) + f"OPENAI_API_KEY={new_key}\n"
                else:
                    env_content = f"OPENAI_API_KEY={new_key}\n"
                
                # Write the .env file
                with open(env_file, "w") as f:
                    f.write(env_content)
                
                status_var.set("✓ API key saved successfully!")
                status_label.config(foreground="green")
                
                # Close dialog after short delay
                dialog.after(1500, dialog.destroy)
                
            except Exception as e:
                # Even if .env save fails, we still have it for this session
                status_var.set("✓ API key set for this session (couldn't save to .env file)")
                status_label.config(foreground="orange")
                print(f"Couldn't save to .env file: {e}")
                dialog.after(2000, dialog.destroy)
                
        except Exception as e:
            status_var.set(f"⚠ Invalid API key: {str(e)[:50]}...")
            status_label.config(foreground="red")
    
    def clear_api_key():
        global client, API_KEY
        confirm = messagebox.askyesno("Clear API Key", "Are you sure you want to clear the API key?", parent=dialog)
        if confirm:
            API_KEY = None
            client = None
            os.environ.pop("OPENAI_API_KEY", None)
            
            # Remove from .env file
            try:
                env_file = ".env"
                if os.path.exists(env_file):
                    with open(env_file, "r") as f:
                        lines = f.readlines()
                    
                    # Remove OPENAI_API_KEY line
                    filtered_lines = [line for line in lines if not line.strip().startswith("OPENAI_API_KEY=")]
                    
                    with open(env_file, "w") as f:
                        f.writelines(filtered_lines)
            except Exception as e:
                print(f"Couldn't update .env file: {e}")
            
            dialog.destroy()
    
    save_btn = ttk.Button(button_frame, text="Save API Key", command=save_api_key)
    save_btn.pack(side=tk.LEFT, ipadx=10, ipady=5)
    
    cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
    cancel_btn.pack(side=tk.LEFT, padx=(10, 0), ipadx=10, ipady=5)
    
    if API_KEY:
        clear_btn = ttk.Button(button_frame, text="Clear Key", command=clear_api_key)
        clear_btn.pack(side=tk.RIGHT, ipadx=10, ipady=5)
    
    # Focus on entry field
    key_entry.focus_set()
    key_entry.select_range(0, tk.END)

def check_api_key_on_send():
    """Check if API key is set before sending"""
    global client, API_KEY
    if not API_KEY or not client:
        messagebox.showwarning("API Key Required", "Please set your OpenAI API key first.\n\nGo to Settings → Set API Key")
        return False
    return True

def generate_chat_title(prompt_text):
    """Generate a short chat title from the first user prompt."""
    models_to_try = [
        ("gpt-5-nano", {}),
        ("gpt-4.1-nano", {}),
        ("gpt-5-mini", {"temperature": 0.3}),
        ("gpt-4.1-mini", {"temperature": 0.3})
    ]
    for model, params in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Create a short, descriptive 3-5 word title for this chat based on the user's message. Respond only with the title, no quotes or extra text."},
                    {"role": "user", "content": prompt_text}
                ],
                max_tokens=20,
                **params
            )
            title = response.choices[0].message.content.strip()
            if title:
                title = re.sub(r"[\r\n]+", " ", title).strip().strip('"').strip("'")
                return sanitize_filename(title)
        except Exception as e:
            print(f"Title generation failed with {model}: {e}")
            continue
    # Fallback
    words = prompt_text.split()[:4]
    fallback_title = " ".join(words)
    if len(fallback_title) > 30:
        fallback_title = fallback_title[:30]
    return sanitize_filename(fallback_title)

def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name or datetime.now().strftime("Chat_%Y-%m-%d_%H-%M-%S")

def send_prompt_async():
    """Run the API call in a separate thread to prevent UI freezing."""
    global is_processing
    
    # Check API key first
    if not check_api_key_on_send():
        return
    
    if is_processing:
        return
    
    user_text = prompt_entry.get("1.0", tk.END)
    cleaned_input = clean_text_aggressive(user_text)
    if not cleaned_input:
        return
    
    is_processing = True
    
    # Update UI immediately
    send_button.config(state="disabled", text="Sending...")
    prompt_entry.config(state="disabled")
    
    # Clear input immediately for better UX
    prompt_entry.delete("1.0", tk.END)
    
    # Add user message to display immediately
    output_box.config(state=tk.NORMAL)
    output_box.insert(tk.END, f"You: {cleaned_input}\n", "user")
    output_box.insert(tk.END, "AI: Thinking...\n", "thinking")
    output_box.config(state=tk.DISABLED)
    output_box.see(tk.END)
    
    def api_call():
        global current_conversation
        try:
            if not current_conversation:
                start_new_conversation()

            current_conversation["messages"].append({"role": "user", "content": cleaned_input})
            user_count = sum(1 for m in current_conversation["messages"] if m.get("role") == "user")
            is_first_user_message = (user_count == 1)

            model_name = model_var.get()
            response = client.chat.completions.create(
                model=model_name,
                messages=current_conversation["messages"]
            )
            reply = response.choices[0].message.content
            current_conversation["messages"].append({"role": "assistant", "content": reply})

            # Update UI in main thread
            root.after(0, lambda: update_ui_after_response(reply, cleaned_input, is_first_user_message))

        except Exception as e:
            # Handle errors in main thread; include original cleaned input so we can restore it
            root.after(0, lambda: handle_api_error(str(e), cleaned_input))

    # Start the API call in a separate thread
    threading.Thread(target=api_call, daemon=True).start()

def update_ui_after_response(reply, user_input, is_first_user_message):
    global is_processing
    
    # Clear the input field now that we have a successful response
    prompt_entry.config(state="normal")  # Enable first
    prompt_entry.delete("1.0", tk.END)
    
    # Remove "Thinking..." line and add real response
    output_box.config(state=tk.NORMAL)
    # Remove the last "AI: Thinking..." line
    output_box.delete("end-2l", "end-1c")
    output_box.insert(tk.END, f"AI: {reply}\n\n", "ai")
    output_box.config(state=tk.DISABLED)
    output_box.see(tk.END)

    # Handle renaming for first message
    if is_first_user_message:
        def generate_title_async():
            title = generate_chat_title(user_input)
            root.after(0, lambda: handle_title_generated(title))
        
        threading.Thread(target=generate_title_async, daemon=True).start()
    else:
        save_current_conversation()
        refresh_chat_list()

    # Re-enable controls
    send_button.config(state="normal", text="Send")
    prompt_entry.focus_set()
    is_processing = False

def handle_title_generated(title):
    if title and title != current_conversation["title"]:
        old_title = current_conversation["title"]
        old_path = os.path.join(CHAT_DIR, f"{old_title}.json")
        new_path = os.path.join(CHAT_DIR, f"{title}.json")
        counter = 1
        base_title = title
        while os.path.exists(new_path):
            title = f"{base_title}_{counter}"
            new_path = os.path.join(CHAT_DIR, f"{title}.json")
            counter += 1
        try:
            current_conversation["title"] = title
            if os.path.exists(old_path):
                os.remove(old_path)
            save_current_conversation()
            refresh_chat_list()
        except Exception as e:
            print(f"Error during rename: {e}")
            current_conversation["title"] = old_title
            save_current_conversation()
    else:
        save_current_conversation()

def handle_api_error(error_msg, original_cleaned_text):
    global is_processing
    
    # Remove user message if API failed
    if current_conversation and current_conversation["messages"] and current_conversation["messages"][-1]["role"] == "user":
        current_conversation["messages"].pop()
    
    # Remove "Thinking..." message
    output_box.config(state=tk.NORMAL)
    output_box.delete("end-2l", "end-1c")
    output_box.insert(tk.END, f"AI: Error - {error_msg}\n\n", "error")
    output_box.config(state=tk.DISABLED)
    
    # Re-enable controls first
    send_button.config(state="normal", text="Send")
    prompt_entry.config(state="normal")
    
    # Restore the original cleaned text since the API call failed
    prompt_entry.delete("1.0", tk.END)
    prompt_entry.insert("1.0", original_cleaned_text)
    
    prompt_entry.focus_set()
    is_processing = False
    
    messagebox.showerror("API Error", error_msg)

def send_prompt():
    """Main send function that delegates to async version."""
    send_prompt_async()

def start_new_conversation():
    global current_conversation
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    current_conversation = {"title": f"Chat_{timestamp}", "messages": []}

def clear_chat_box():
    output_box.config(state=tk.NORMAL)
    output_box.delete("1.0", tk.END)
    output_box.config(state=tk.DISABLED)

def save_current_conversation():
    if not current_conversation or not current_conversation["messages"]:
        return
    filename = os.path.join(CHAT_DIR, f"{current_conversation['title']}.json")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(current_conversation, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving: {e}")

def load_conversation(filename):
    global current_conversation
    try:
        with open(filename, "r", encoding="utf-8") as f:
            current_conversation = json.load(f)
        clear_chat_box()
        for msg in current_conversation["messages"]:
            role = "user" if msg["role"] == "user" else "ai"
            prefix = "You: " if role == "user" else "AI: "
            output_box.config(state=tk.NORMAL)
            output_box.insert(tk.END, prefix + msg["content"] + "\n\n", role)
            output_box.config(state=tk.DISABLED)
        output_box.see(tk.END)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load conversation: {e}")

def resize_input_box(event=None):
    lines = int(prompt_entry.index('end-1c').split('.')[0])
    # Reduce max height to prevent UI overflow
    max_height = 8  # Reduced from 20 to prevent send button getting pushed off screen
    new_height = min(max(lines, 3), max_height)  # Minimum 3 lines, maximum 8
    prompt_entry.config(height=new_height)

def refresh_chat_list():
    chat_listbox.delete(0, tk.END)
    try:
        files = sorted([f for f in os.listdir(CHAT_DIR) if f.endswith(".json")], reverse=True)  # Most recent first
        for file in files:
            chat_listbox.insert(tk.END, file[:-5])
        if current_conversation:
            try:
                idx = list(chat_listbox.get(0, tk.END)).index(current_conversation["title"])
                chat_listbox.selection_clear(0, tk.END)
                chat_listbox.selection_set(idx)
                chat_listbox.activate(idx)
            except ValueError:
                pass
    except Exception as e:
        print(f"Error refreshing chat list: {e}")

def on_chat_select(event):
    selections = chat_listbox.curselection()
    if len(selections) == 1 and not is_processing:  # Only load if single selection
        filename = chat_listbox.get(selections[0]) + ".json"
        load_conversation(os.path.join(CHAT_DIR, filename))
    elif len(selections) > 1:
        # Show selection count in status
        status_label.config(text=f"{len(selections)} chats selected", foreground="blue")
        root.after(2000, lambda: status_label.config(text="", foreground="black"))

def rename_chat(event=None):
    selections = chat_listbox.curselection()
    if len(selections) != 1:  # Only allow rename for single selection
        return
    index = selections[0]
    old_name = chat_listbox.get(index)
    new_name = simpledialog.askstring("Rename Chat", "Enter new chat name:", initialvalue=old_name)
    if new_name and new_name != old_name:
        old_path = os.path.join(CHAT_DIR, f"{old_name}.json")
        new_name = sanitize_filename(new_name)
        new_path = os.path.join(CHAT_DIR, f"{new_name}.json")
        try:
            os.rename(old_path, new_path)
            if current_conversation and current_conversation["title"] == old_name:
                current_conversation["title"] = new_name
                save_current_conversation()
            refresh_chat_list()
            status_label.config(text="Chat renamed successfully", foreground="green")
            root.after(3000, lambda: status_label.config(text="", foreground="black"))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename: {e}")

def delete_chat():
    selections = chat_listbox.curselection()
    if not selections:
        return
    
    if len(selections) == 1:
        chat_name = chat_listbox.get(selections[0])
        confirm = messagebox.askyesno("Delete Chat", f"Delete '{chat_name}'?\n\nThis action cannot be undone.")
    else:
        chat_names = [chat_listbox.get(i) for i in selections]
        confirm = messagebox.askyesno("Delete Chats", f"Delete {len(selections)} selected chats?\n\nThis action cannot be undone.")
    
    if confirm:
        current_chat_deleted = False
        try:
            for index in reversed(sorted(selections)):  # Delete in reverse order to maintain indices
                chat_name = chat_listbox.get(index)
                path = os.path.join(CHAT_DIR, f"{chat_name}.json")
                if os.path.exists(path):
                    os.remove(path)
                
                # Check if we're deleting the current conversation
                if current_conversation and current_conversation["title"] == chat_name:
                    current_chat_deleted = True
            
            # If current conversation was deleted, start a new one
            if current_chat_deleted:
                start_new_conversation()
                clear_chat_box()
                
            refresh_chat_list()
            
            if len(selections) == 1:
                status_label.config(text="Chat deleted successfully", foreground="green")
            else:
                status_label.config(text=f"{len(selections)} chats deleted successfully", foreground="green")
            root.after(3000, lambda: status_label.config(text="", foreground="black"))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete chats: {e}")

def delete_selected_chats():
    """Helper function for context menu"""
    delete_chat()

def export_chat():
    selections = chat_listbox.curselection()
    if not selections:
        return
    
    if len(selections) == 1:
        # Single chat export
        chat_name = chat_listbox.get(selections[0])
        filename = filedialog.asksaveasfilename(
            title="Export Chat",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
            initialvalue=f"{chat_name}.txt"
        )
        
        if filename:
            try:
                path = os.path.join(CHAT_DIR, f"{chat_name}.json")
                with open(path, "r", encoding="utf-8") as f:
                    conversation = json.load(f)
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"Chat: {chat_name}\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for msg in conversation["messages"]:
                        role = "You" if msg["role"] == "user" else "AI"
                        f.write(f"{role}: {msg['content']}\n\n")
                
                status_label.config(text=f"Chat exported to {os.path.basename(filename)}", foreground="green")
                root.after(3000, lambda: status_label.config(text="", foreground="black"))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")
    
    else:
        # Multiple chat export
        folder = filedialog.askdirectory(title="Select folder to export chats")
        if folder:
            try:
                exported_count = 0
                for selection in selections:
                    chat_name = chat_listbox.get(selection)
                    path = os.path.join(CHAT_DIR, f"{chat_name}.json")
                    
                    with open(path, "r", encoding="utf-8") as f:
                        conversation = json.load(f)
                    
                    # Sanitize filename for export
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', chat_name)
                    export_path = os.path.join(folder, f"{safe_name}.txt")
                    
                    with open(export_path, "w", encoding="utf-8") as f:
                        f.write(f"Chat: {chat_name}\n")
                        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("=" * 50 + "\n\n")
                        
                        for msg in conversation["messages"]:
                            role = "You" if msg["role"] == "user" else "AI"
                            f.write(f"{role}: {msg['content']}\n\n")
                    
                    exported_count += 1
                
                status_label.config(text=f"{exported_count} chats exported to {os.path.basename(folder)}", foreground="green")
                root.after(3000, lambda: status_label.config(text="", foreground="black"))
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export chats: {e}")

def copy_conversation():
    """Copy the current conversation to clipboard."""
    if not current_conversation or not current_conversation["messages"]:
        return
    
    text = f"Chat: {current_conversation['title']}\n"
    text += "=" * 50 + "\n\n"
    
    for msg in current_conversation["messages"]:
        role = "You" if msg["role"] == "user" else "AI"
        text += f"{role}: {msg['content']}\n\n"
    
    root.clipboard_clear()
    root.clipboard_append(text)
    status_label.config(text="Conversation copied to clipboard!", foreground="green")
    root.after(3000, lambda: status_label.config(text="", foreground="black"))

def on_enter(event):
    if event.state & 0x0001:  # Shift key pressed
        return
    elif is_processing:
        return "break"  # Don't send while processing
    else:
        send_prompt()
        return "break"

def autosave_conversation():
    if not is_processing:  # Only save when not processing
        save_current_conversation()
    root.after(5000, autosave_conversation)

def on_window_close():
    save_current_conversation()
    root.destroy()

is_dark_mode = False

def toggle_theme():
    """Toggle between light and dark themes"""
    global is_dark_mode
    is_dark_mode = not is_dark_mode
    
    if is_dark_mode:
        # Switch to dark mode
        root.config(bg='#2b2b2b')
        
        # Configure ttk styles for dark mode
        style.theme_use('clam')
        
        # Main frame and panel backgrounds
        style.configure('TFrame', background='#2b2b2b', borderwidth=0)
        style.configure('TLabel', background='#2b2b2b', foreground='white')
        style.configure('TButton', background='#404040', foreground='white', focuscolor='#505050', borderwidth=1, relief='solid')
        style.map('TButton', background=[('active', '#505050'), ('pressed', '#303030')])
        
        # LabelFrame (the boxes with titles)
        style.configure('TLabelFrame', background='#2b2b2b', foreground='white', borderwidth=1, relief='solid', bordercolor='#404040')
        style.configure('TLabelFrame.Label', background='#2b2b2b', foreground='white')
        
        # Combobox styling
        style.configure('TCombobox', fieldbackground='#404040', background='#404040', foreground='white', borderwidth=1, arrowcolor='white', focuscolor='#505050')
        style.map('TCombobox', fieldbackground=[('readonly', '#404040')], selectbackground=[('readonly', '#505050')])
        
        # PanedWindow (removes the white border between panels)
        style.configure('TPanedwindow', background='#2b2b2b', borderwidth=0)
        style.configure('TPanedwindow.Sash', background='#404040', borderwidth=1, sashthickness=3)
        
        # Text widgets
        output_box.config(bg='#1e1e1e', fg='white', insertbackground='white', highlightbackground='#404040', highlightcolor='#505050', selectbackground='#404040', selectforeground='white')
        prompt_entry.config(bg='#1e1e1e', fg='white', insertbackground='white', highlightbackground='#404040', highlightcolor='#505050', selectbackground='#404040', selectforeground='white')
        chat_listbox.config(bg='#1e1e1e', fg='white', selectbackground='#404040', selectforeground='white', highlightbackground='#404040')
        
        # Menu styling
        menubar.config(bg='#404040', fg='white', activebackground='#505050', activeforeground='white', borderwidth=0)
        settings_menu.config(bg='#404040', fg='white', activebackground='#505050', activeforeground='white', borderwidth=0)
        
        # Context menu styling
        chat_menu.config(bg='#404040', fg='white', activebackground='#505050', activeforeground='white', borderwidth=0)
        
        # Update root window title bar (if possible on Windows)
        root.title("OpenAI Chat Client - Dark Mode")
        
        theme_button.config(text="☀️ Light Mode")
        
    else:
        # Switch to light mode
        root.config(bg='SystemButtonFace')
        
        # Reset to default Windows theme
        style.theme_use('winnative' if root.tk.call('tk', 'windowingsystem') == 'win32' else 'default')
        
        # Reset text widgets to light mode
        output_box.config(bg='white', fg='black', insertbackground='black', highlightbackground='SystemButtonFace', highlightcolor='SystemHighlight', selectbackground='SystemHighlight', selectforeground='SystemHighlightText')
        prompt_entry.config(bg='white', fg='black', insertbackground='black', highlightbackground='SystemButtonFace', highlightcolor='SystemHighlight', selectbackground='SystemHighlight', selectforeground='SystemHighlightText')
        chat_listbox.config(bg='white', fg='black', selectbackground='SystemHighlight',selectforeground='SystemHighlightText', highlightbackground='SystemButtonFace')
        
        # Reset menu styling
        menubar.config(bg='SystemMenu', fg='SystemMenuText', activebackground='SystemHighlight', activeforeground='SystemHighlightText')
        settings_menu.config(bg='SystemMenu', fg='SystemMenuText', activebackground='SystemHighlight', activeforeground='SystemHighlightText')
        
        # Reset context menu
        chat_menu.config(bg='SystemMenu', fg='SystemMenuText', activebackground='SystemHighlight', activeforeground='SystemHighlightText')
        
        root.title("OpenAI Chat Client")
        theme_button.config(text="🌙 Dark Mode")

def update_text_stats():
    """Update word and character count for the input field"""
    text = prompt_entry.get("1.0", tk.END).strip()
    words = len(text.split()) if text else 0
    chars = len(text)
    stats_label.config(text=f"Words: {words} | Characters: {chars}")
    root.after(100, update_text_stats)  # Update every 100ms

# --- GUI setup ---
root = tk.Tk()
root.title("OpenAI Chat Client")
root.geometry("1200x800")
root.protocol("WM_DELETE_WINDOW", on_window_close)

# Configure style
style = ttk.Style()

# Create menu bar
menubar = tk.Menu(root)
root.config(menu=menubar)

# Settings menu
settings_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Settings", menu=settings_menu)
settings_menu.add_command(label="Set API Key...", command=set_api_key)
settings_menu.add_separator()
settings_menu.add_command(label="Toggle Dark Mode", command=toggle_theme)
settings_menu.add_separator()
settings_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", "OpenAI Chat Client\n\nA simple GUI for chatting with OpenAI models.\n\nRequires OpenAI API key to function.\n\nFeatures:\n• Dark/Light mode\n• Chat history\n• Export conversations\n• Auto-save"))

# Check API key on startup
def check_api_key_on_startup():
    if not API_KEY:
        response = messagebox.askyesno("API Key Required", "No OpenAI API key found.\n\nWould you like to set one now?")
        if response:
            set_api_key()

# Schedule API key check after GUI is ready
root.after(100, check_api_key_on_startup)

# Create main paned window for resizable panels
main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
main_paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

# Left frame: chat list
left_frame = ttk.Frame(main_paned)
main_paned.add(left_frame, weight=1)

# Chat list header with buttons
chat_header_frame = ttk.Frame(left_frame)
chat_header_frame.pack(fill=tk.X, pady=(0, 5))

ttk.Label(chat_header_frame, text="Previous Chats", font=("Arial", 10, "bold")).pack(side=tk.LEFT)

theme_button = ttk.Button(chat_header_frame, text="🌙 Dark Mode", command=toggle_theme)
theme_button.pack(side=tk.RIGHT)

chat_listbox = tk.Listbox(left_frame, width=35, font=("Arial", 9), selectmode=tk.EXTENDED)

# Right-click context menu
chat_menu = tk.Menu(chat_listbox, tearoff=0)
chat_menu.add_command(label="Rename", command=lambda: rename_chat())
chat_menu.add_command(label="Export...", command=lambda: export_chat())
chat_menu.add_separator()
chat_menu.add_command(label="Delete", command=lambda: delete_selected_chats())

def update_context_menu():
    """Update context menu based on selection count"""
    selections = chat_listbox.curselection()
    if not selections:
        return
        
    # Clear existing menu
    chat_menu.delete(0, tk.END)
    
    if len(selections) == 1:
        # Single selection menu
        chat_menu.add_command(label="Rename", command=lambda: rename_chat())
        chat_menu.add_command(label="Export...", command=lambda: export_chat())
        chat_menu.add_separator()
        chat_menu.add_command(label="Delete", command=lambda: delete_selected_chats())
    else:
        # Multiple selection menu
        chat_menu.add_command(label=f"Export {len(selections)} chats...", command=lambda: export_chat())
        chat_menu.add_separator()
        chat_menu.add_command(label=f"Delete {len(selections)} chats", command=lambda: delete_selected_chats())

def on_right_click(event):
    try:
        index = chat_listbox.nearest(event.y)
        if index < chat_listbox.size():
            # If the clicked item is not in current selection, select just this item
            current_selections = chat_listbox.curselection()
            if index not in current_selections:
                chat_listbox.selection_clear(0, tk.END)
                chat_listbox.selection_set(index)
                chat_listbox.activate(index)
            
            update_context_menu()
            chat_menu.tk_popup(event.x_root, event.y_root)
    finally:
        chat_menu.grab_release()

chat_listbox.bind("<Button-3>", on_right_click)  # Windows/Linux
chat_listbox.bind("<Button-2>", on_right_click)  # macOS
chat_listbox.bind("<Double-Button-1>", rename_chat)
chat_listbox.pack(fill=tk.BOTH, expand=True)
chat_listbox.bind("<<ListboxSelect>>", on_chat_select)

# Right frame: main chat area
right_frame = ttk.Frame(main_paned)
main_paned.add(right_frame, weight=3)

# Top controls frame
controls_frame = ttk.Frame(right_frame)
controls_frame.pack(fill=tk.X, padx=5, pady=5)

# Model selection
ttk.Label(controls_frame, text="Model:").grid(row=0, column=0, sticky="w", padx=(0, 5))
model_var = tk.StringVar(value="gpt-5-mini")
models = ["gpt-5-nano", "gpt-5-mini", "gpt-5", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1"]
model_dropdown = ttk.Combobox(controls_frame, textvariable=model_var, values=models, state="readonly", width=15)
model_dropdown.grid(row=0, column=1, sticky="w", padx=(0, 20))

# Buttons
new_chat_button = ttk.Button(controls_frame, text="New Chat", command=lambda: [start_new_conversation(), clear_chat_box()])
new_chat_button.grid(row=0, column=2, padx=5)

copy_button = ttk.Button(controls_frame, text="Copy All", command=copy_conversation)
copy_button.grid(row=0, column=3, padx=5)

clear_button = ttk.Button(controls_frame, text="Clear", command=clear_chat_box)
clear_button.grid(row=0, column=4, padx=5)

# Output area with frame
output_frame = ttk.LabelFrame(right_frame, text="Conversation")
output_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

output_box = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, width=60, height=20, state=tk.DISABLED, font=("Arial", 10), borderwidth=1, relief='solid')
output_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

# Enhanced styling tags
output_box.tag_config("user", foreground="blue", font=("Arial", 10, "bold"))
output_box.tag_config("ai", foreground="green", font=("Arial", 10))
output_box.tag_config("thinking", foreground="gray", font=("Arial", 10, "italic"))
output_box.tag_config("error", foreground="red", font=("Arial", 10))

input_frame = ttk.LabelFrame(right_frame, text="Your Message")
input_frame.pack(fill=tk.X, padx=2, pady=2)

# Text entry with controlled height
prompt_entry = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, width=50, height=4, font=("Arial", 10), borderwidth=1, relief='solid')
prompt_entry.pack(fill=tk.X, padx=2, pady=2)
prompt_entry.bind("<KeyRelease>", resize_input_box)
prompt_entry.bind("<Return>", on_enter)

bottom_frame = ttk.Frame(input_frame)
bottom_frame.pack(fill=tk.X, padx=2, pady=(0, 2))

# Text statistics
stats_label = ttk.Label(bottom_frame, text="Words: 0 | Characters: 0", font=("Arial", 8))
stats_label.pack(side=tk.LEFT)

# Help text
ttk.Label(bottom_frame, text="Press Enter to send, Shift+Enter for new line", font=("Arial", 8)).pack(side=tk.LEFT, padx=(20, 0))

# Send button with proper sizing
send_button = ttk.Button(bottom_frame, text="Send", command=send_prompt)
send_button.pack(side=tk.RIGHT, ipadx=15, ipady=3)

# Status bar
status_label = ttk.Label(right_frame, text="", font=("Arial", 8))
status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=2)

# Initialize
refresh_chat_list()
start_new_conversation()
autosave_conversation()
update_text_stats()  # Start text stats updates
prompt_entry.focus_set()

root.mainloop()
