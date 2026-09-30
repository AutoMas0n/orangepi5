#!/bin/bash
# Assert that every bind-mount source in every compose file lies INSIDE the
# declared backup set. This exists because the migration plan once *assumed*
# the stack's configs lived in ~/Documents, while run.sh (running as root)
# resolved the same paths to /root/Documents - outside the backup. The whole
# service configuration was lost with the old filesystem as a result.
# Run this before ANY destructive step.
exec python3 - <<'PY'
import glob, os, re, sys

REPO  = "/home/orangepi/Github/orangepi5"
STATE = "/home/orangepi/docker-data"
# The declared backup set. If a service starts writing outside this list,
# either move the service or extend the list - deliberately.
BACKUP = [REPO, STATE, "/media", "/home/orangepi/.ssh"]

def env_of(path):
    d = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k] = v.strip()
    return d

env = {}
for f in glob.glob(f"{REPO}/docker/*/.env"):
    env.update(env_of(f))

problems = []
checked = 0
for cf in sorted(glob.glob(f"{REPO}/docker/*/docker-compose.yml")):
    for line in open(cf):
        m = re.match(r"\s*-\s+([^:\s]+):[^:\s]", line)
        if not m:
            continue
        src = m.group(1)
        if src.startswith("/dev/") or not (src.startswith(("/", "$", "~"))):
            continue                      # device nodes and named volumes
        src = re.sub(r"\$\{(\w+)\}", lambda mm: env.get(mm.group(1), "<UNRESOLVED>"), src)
        checked += 1
        if "<UNRESOLVED>" in src:
            problems.append((cf, src, "unresolved variable")); continue
        if src.startswith("~"):
            problems.append((cf, src, "tilde is not expanded by Compose - use an absolute path")); continue
        if not any(src == b or src.startswith(b + "/") for b in BACKUP):
            problems.append((cf, src, "OUTSIDE the backup set"))

for cf, src, why in problems:
    print(f"  FAIL  {os.path.relpath(cf, REPO)}  {src}  -> {why}")
print(f"  checked {checked} bind-mount source(s); {len(problems)} problem(s)")
print("  backup set: " + ", ".join(BACKUP))
sys.exit(1 if problems else 0)
PY
