import os
import re

files_to_check = [
    "alter_schema.py", "audit_concurrent.py", "audit_db.py", "audit_nlp.py",
    "audit_trace.py", "check_address_schema.py", "check_conv_messages_schema.py",
    "check_schema.py", "db_investigate.py", "debug_tracking.py", "explorer.py",
    "get_schema.py", "inspect_cancel_values.py", "inspect_schema.py",
    "inspect_db.py", "inspect_db2.py", "inspect_db3.py", "inspect_db4.py", 
    "inspect_db5.py", "inspect_db6.py", "inspect_db7.py", "inspect_db8.py",
    "inspect_history.py", "inspect_history_all.py", "profile_db.py", "query.py",
    "reproduce_bug.py", "runtime_investigation.py", "trace.py",
    "output.log", "pyfiles.txt", "pyfiles_utf8.txt", "search_handoff.txt",
    "validation_results.json", "test_goodbye_results.json"
]

project_root = "."

# Map to store references
# { file_name: [ "path/to/file:line_number: match" ] }
references = {f: [] for f in files_to_check}

pattern = re.compile(r'|'.join([re.escape(f).replace(r'\.py', r'(?:\.py)?') for f in files_to_check]))

for root, dirs, files in os.walk(project_root):
    if ".git" in root or "__pycache__" in root or "venv" in root:
        continue
        
    for file in files:
        file_path = os.path.join(root, file)
        
        # skip binary or unreadable
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    for target_file in files_to_check:
                        # strip .py for import checking
                        base_name = target_file.replace(".py", "")
                        if target_file in line or base_name in line:
                            # Verify it's actually referencing the file
                            if target_file == file: continue # skip self reference
                            references[target_file].append(f"{file_path}:{line_idx+1}")
        except Exception:
            pass

for target, refs in references.items():
    if refs:
        print(f"--- References to {target} ---")
        for r in refs:
            print(f"  {r}")

print("Search complete.")
