
import pkg_resources

installed = [str(d) for d in pkg_resources.working_set]
sorted_installed = sorted(installed, key=str.lower)
with open('backend/requirements.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(sorted_installed))
print("Requirements written to backend/requirements.txt in UTF-8")
