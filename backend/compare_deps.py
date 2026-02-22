def parse_requirements(file_path):
    reqs = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Handle diff formats like "package==version", "package>=version", just "package"
            parts = line.split('==')
            if len(parts) >= 2:
                name = parts[0].strip().lower().replace('_', '-')
                version = parts[1].strip()
                reqs[name] = version
            else:
                # Handle >= or just name
                # Simple extraction of name
                import re
                match = re.split(r'[=<>~!]', line)
                name = match[0].strip().lower().replace('_', '-')
                reqs[name] = None # No specific version constraint for equality check
    return reqs

def compare():
    frozen = parse_requirements('frozen_requirements.txt')
    reqs = parse_requirements('requirements.txt')
    
    missing = []
    
    # Check what is in frozen but not in reqs
    for pkg, ver in frozen.items():
        if pkg not in reqs:
            missing.append(f"{pkg}=={ver}")
            
    print("Dependencies installed but NOT in requirements.txt:")
    for m in missing:
        print(m)

if __name__ == "__main__":
    compare()
