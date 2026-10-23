import os
import re

patterns = [
    re.compile(r'AIza[0-9A-Za-z-_]{35}'),
    re.compile(r'api[_-]?key\s*[:=]\s*[\'"][0-9A-Za-z-_]{10,}[\'"]', re.I),
    re.compile(r'GOOGLE_API_KEY\s*[:=]\s*[\'"]?[0-9A-Za-z-_]{10,}', re.I),
    re.compile(r'sk-[0-9A-Za-z-_]{20,}')
]

hits = []
exclude_dirs = {'.git', '.cache', 'venv', 'venv312', '__pycache__', '.pytest_cache'}

for dp, dn, fnames in os.walk('.'):
    dn[:] = [d for d in dn if d not in exclude_dirs]
    for f in fnames:
        if f == '.env' or f.startswith('.env.'):
            continue
        p = os.path.join(dp, f)
        try:
            sz = os.path.getsize(p)
            if sz > 15 * 1024 * 1024:
                continue
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
                for pat in patterns:
                    matches = pat.findall(content)
                    real_m = [
                        x for x in matches
                        if 'your_key_here' not in x
                        and 'YOUR_API_KEY' not in x
                        and 'os.getenv' not in x
                        and 'os.environ' not in x
                        and 'GEMINI_API_KEY' not in x
                    ]
                    if real_m:
                        hits.append((p, pat.pattern))
                        break
        except Exception as e:
            pass

print(f"Total potential secret hits found: {len(hits)}")
for h in hits:
    print("HIT:", h[0])
