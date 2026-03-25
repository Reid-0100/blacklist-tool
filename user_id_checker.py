import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import re
import json
import unicodedata
from datetime import datetime


class UserIDCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Block List Checker")
        self.root.geometry("1050x760")

        self.db_file = "blocklist_db.json"
        self.blocked_ids = set()

        self.load_database()
        self.build_ui()
        self.update_status_label()

    def build_ui(self):
        title_label = tk.Label(
            self.root,
            text="Block List Checker",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)

        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=8, fill="x", padx=20)

        self.status_label = tk.Label(
            top_frame,
            text="Database: 0 blocked IDs",
            anchor="w",
            fg="blue"
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        export_button = tk.Button(
            top_frame,
            text="Export to TXT",
            command=self.export_to_txt,
            width=16
        )
        export_button.pack(side="right", padx=5)

        instruction_label = tk.Label(
            self.root,
            text=(
                "Paste one or more user IDs or log text below.\n"
                "This version supports normal lines and broken two-line IDs."
            ),
            justify="left",
            anchor="w"
        )
        instruction_label.pack(pady=5, padx=20, anchor="w")

        self.input_box = scrolledtext.ScrolledText(self.root, height=12, width=120)
        self.input_box.pack(padx=20, pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        add_button = tk.Button(
            button_frame,
            text="Add User ID(s)",
            command=self.add_user_ids,
            width=16
        )
        add_button.pack(side="left", padx=8)

        check_button = tk.Button(
            button_frame,
            text="Check User ID(s)",
            command=self.check_user_ids,
            width=16
        )
        check_button.pack(side="left", padx=8)

        clear_button = tk.Button(
            button_frame,
            text="Clear Input",
            command=self.clear_input,
            width=12
        )
        clear_button.pack(side="left", padx=8)

        result_label = tk.Label(
            self.root,
            text="Result:",
            font=("Arial", 12, "bold")
        )
        result_label.pack(anchor="w", padx=20, pady=(10, 0))

        self.result_box = scrolledtext.ScrolledText(
            self.root,
            height=26,
            width=120,
            state="disabled"
        )
        self.result_box.pack(padx=20, pady=10)

    def update_status_label(self):
        self.status_label.config(
            text=f"Database: {len(self.blocked_ids)} blocked IDs"
        )

    def load_database(self):
        if not os.path.exists(self.db_file):
            self.blocked_ids = set()
            self.save_database()
            return

        try:
            with open(self.db_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            ids = data.get("blocked_ids", [])
            cleaned_ids = set()

            for item in ids:
                normalized = self.normalize_extracted_id(str(item))
                if normalized:
                    cleaned_ids.add(normalized)

            self.blocked_ids = cleaned_ids

        except Exception:
            self.blocked_ids = set()
            self.save_database()

    def save_database(self):
        data = {
            "blocked_ids": sorted(self.blocked_ids),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(self.db_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def clean_text(self, text):
        cleaned_chars = []

        for ch in text:
            category = unicodedata.category(ch)
            if category in ("Cc", "Cf"):
                continue
            cleaned_chars.append(ch)

        text = "".join(cleaned_chars)

        text = text.replace("＃", "#")
        text = text.replace("，", ",")
        text = text.replace("；", ";")
        text = text.replace("\u00A0", " ")
        text = text.replace("\r", "\n")

        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def normalize_side_text(self, text):
        text = self.clean_text(text)
        text = re.sub(r"^[^\w\u00C0-\uFFFF#]+", "", text, flags=re.UNICODE)
        text = re.sub(r"[^\w\u00C0-\uFFFF#]+$", "", text, flags=re.UNICODE)
        return self.clean_text(text)

    def normalize_extracted_id(self, text):
        text = self.clean_text(text)
        if "#" not in text:
            return None

        left, right = text.split("#", 1)
        left = self.normalize_side_text(left)
        right = self.normalize_side_text(right)

        if not left or not right:
            return None

        return f"{left}#{right}"

    def strip_known_prefixes(self, text):
        text = self.clean_text(text)

        prefixes = [
            "joined the lobby",
            "joined the room",
            "has joined",
            "已加入组队房间",
            "已加入房间",
            "进入了房间",
        ]

        changed = True
        while changed:
            changed = False
            lower_text = text.lower()

            for prefix in prefixes:
                if lower_text.startswith(prefix.lower()):
                    text = text[len(prefix):].strip()
                    changed = True
                    break

        return text

    def strip_known_suffixes(self, text):
        text = self.clean_text(text)

        suffix_patterns = [
            r"\s*已加入组队房间.*$",
            r"\s*已加入房间.*$",
            r"\s*进入了房间.*$",
            r"\s*joined the lobby.*$",
            r"\s*joined the room.*$",
            r"\s*has joined.*$",
        ]

        changed = True
        while changed:
            changed = False

            for pattern in suffix_patterns:
                new_text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
                if new_text != text:
                    text = new_text
                    changed = True
                    break

        return text

    def extract_user_id_from_line(self, line):
        line = self.clean_text(line)

        if "#" not in line:
            return None

        line = self.strip_known_suffixes(line)

        if "#" not in line:
            return None

        hash_positions = [i for i, ch in enumerate(line) if ch == "#"]
        candidates = []

        for pos in hash_positions:
            left_raw = line[:pos]
            right_raw = line[pos + 1:]

            left = self.normalize_side_text(left_raw)
            right = self.normalize_side_text(right_raw)

            if len(left) > 16:
                left = self.normalize_side_text(left[-16:])

            if len(right) > 5:
                continue

            if not left or not right:
                continue

            if 1 <= len(left) <= 16 and 1 <= len(right) <= 5:
                candidates.append(f"{left}#{right}")

        if not candidates:
            return None

        candidate = candidates[-1]
        candidate = self.strip_known_prefixes(candidate)

        if "#" not in candidate:
            return None

        return self.normalize_extracted_id(candidate)

    def merge_broken_input_lines(self, raw_text):
        raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = raw_text.split("\n")

        cleaned_lines = []
        for line in raw_lines:
            cleaned = self.clean_text(line)
            if cleaned:
                cleaned_lines.append(cleaned)

        merged_lines = []
        i = 0

        while i < len(cleaned_lines):
            current = cleaned_lines[i]

            if i + 1 < len(cleaned_lines):
                next_line = cleaned_lines[i + 1]

                if (
                    "#" not in current
                    and next_line.startswith("#")
                ):
                    merged_lines.append(current + next_line)
                    i += 2
                    continue

            merged_lines.append(current)
            i += 1

        return merged_lines

    def parse_input_ids(self, raw_text):
        merged_lines = self.merge_broken_input_lines(raw_text)
        extracted_ids = []

        for line in merged_lines:
            parts = re.split(r"[;]", line)
            for part in parts:
                part = self.clean_text(part)
                if not part:
                    continue

                user_id = self.extract_user_id_from_line(part)
                if user_id:
                    extracted_ids.append(user_id)

        deduped = []
        seen = set()

        for item in extracted_ids:
            if item not in seen:
                seen.add(item)
                deduped.append(item)

        return deduped

    def add_user_ids(self):
        raw_text = self.input_box.get("1.0", tk.END)

        if not raw_text.strip():
            messagebox.showwarning("Warning", "Please enter at least one user ID or log text.")
            return

        extracted_ids = self.parse_input_ids(raw_text)

        if not extracted_ids:
            messagebox.showwarning(
                "Warning",
                "No valid user ID could be extracted from the input."
            )
            return

        added_ids = []
        skipped_ids = []

        for user_id in extracted_ids:
            if user_id in self.blocked_ids:
                skipped_ids.append(user_id)
            else:
                self.blocked_ids.add(user_id)
                added_ids.append(user_id)

        self.save_database()
        self.update_status_label()

        result_text = []
        result_text.append(f"Total extracted: {len(extracted_ids)}")
        result_text.append(f"Added: {len(added_ids)}")
        result_text.append(f"Skipped (already existed): {len(skipped_ids)}")
        result_text.append("")

        if added_ids:
            result_text.append("Added IDs:")
            for user_id in added_ids:
                result_text.append(f"  + {user_id}")
            result_text.append("")

        if skipped_ids:
            result_text.append("Skipped IDs:")
            for user_id in skipped_ids:
                result_text.append(f"  = {user_id}")

        self.show_result("\n".join(result_text))
        messagebox.showinfo("Success", f"Added {len(added_ids)} user ID(s) to the database.")

    def check_user_ids(self):
        if not self.blocked_ids:
            messagebox.showwarning(
                "Warning",
                "The database is empty. Please add some blocked user IDs first."
            )
            return

        raw_text = self.input_box.get("1.0", tk.END)

        if not raw_text.strip():
            messagebox.showwarning("Warning", "Please enter at least one user ID or log text.")
            return

        extracted_ids = self.parse_input_ids(raw_text)

        if not extracted_ids:
            messagebox.showwarning(
                "Warning",
                "No valid user ID could be extracted from the input."
            )
            return

        found_count = 0
        not_found_count = 0

        result_text = []
        result_text.append(f"Total checked: {len(extracted_ids)}")
        result_text.append("")

        for user_id in extracted_ids:
            if user_id in self.blocked_ids:
                result = "Found"
                found_count += 1
            else:
                result = "Not Found"
                not_found_count += 1

            result_text.append(f"Extracted ID : {user_id}")
            result_text.append(f"Result       : {result}")
            result_text.append("")

        result_text.insert(1, f"Found: {found_count}")
        result_text.insert(2, f"Not Found: {not_found_count}")

        self.show_result("\n".join(result_text))

    def export_to_txt(self):
        if not self.blocked_ids:
            messagebox.showwarning("Warning", "The database is empty. Nothing to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Block List",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                for user_id in sorted(self.blocked_ids):
                    file.write(user_id + "\n")

            messagebox.showinfo("Success", "Block list exported successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export TXT file.\n\n{e}")

    def show_result(self, text):
        self.result_box.config(state="normal")
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(tk.END, text)
        self.result_box.config(state="disabled")

    def clear_input(self):
        self.input_box.delete("1.0", tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = UserIDCheckerApp(root)
    root.mainloop()