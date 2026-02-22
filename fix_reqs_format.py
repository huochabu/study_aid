
import pkg_resources

installed = [d for d in pkg_resources.working_set]
# Sort by case-insensitive key
sorted_installed = sorted(installed, key=lambda d: d.project_name.lower())

with open('backend/requirements.txt', 'w', encoding='utf-8') as f:
    for d in sorted_installed:
        # Format: project_name==version
        f.write(f"{d.project_name}=={d.version}\n")
        
print("Requirements written to backend/requirements.txt in 'package==version' format")
