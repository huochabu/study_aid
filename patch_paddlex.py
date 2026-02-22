import os
import site
from pathlib import Path

# Find site-packages directories
site_packages = site.getsitepackages()
print(f"Searching in site-packages: {site_packages}")

target_rel_path = Path("paddlex") / "inference" / "models" / "common" / "static_infer.py"
found = False

for sp in site_packages:
    target_file = Path(sp) / target_rel_path
    if target_file.exists():
        print(f"Found target file: {target_file}")
        
        try:
            content = target_file.read_text(encoding='utf-8')
            
            # Look for the problematic line
            old_line = "config.set_optimization_level(3)"
            new_line = "# config.set_optimization_level(3) # Patched for Paddle 3.0 compatibility"
            
            if old_line in content:
                new_content = content.replace(old_line, new_line)
                target_file.write_text(new_content, encoding='utf-8')
                print("Success: File patched successfully.")
                found = True
                break
            elif new_line in content:
                print("Info: File is already patched.")
                found = True
                break
            else:
                print("Warning: Content to replace not found in this file.")
        except Exception as e:
            print(f"Error patching file {target_file}: {e}")

if not found:
    print("Error: Target file not found in any site-packages directory.")
    # Fallback: standard Anaconda path structure might not be in site.getsitepackages() if running as script?
    # But we run with the python executable of the env, so it should be fine.
