"""Check publishable Git files without displaying possible credential values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "provider or GitHub token": re.compile(r"(?:sk-(?:or-v1-)?[A-Za-z0-9_-]{25,}|SG\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}|AKIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "database password in URI": re.compile(r"mongodb(?:\+srv)?://[^\s/:@]+:([^\s/@]+)@"),
}


def scan():
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, stdout=subprocess.PIPE,
    )
    names = sorted(set(result.stdout.decode().split("\0")) - {""})
    findings = []
    for name in names:
        path = ROOT / name
        if not path.is_file():
            continue
        if path.name.startswith(".env") and not path.name.endswith(".example"):
            findings.append(f"{name}: real environment file must not be published")
            continue
        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            findings.append(f"{name}: private credential file must not be published")
            continue
        raw = path.read_bytes()
        if b"\0" in raw:
            continue
        for number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
            for label, pattern in PATTERNS.items():
                match = pattern.search(line)
                if not match:
                    continue
                if label == "database password in URI" and match.group(1) == "YOUR_PASSWORD":
                    continue
                findings.append(f"{name}:{number}: possible {label}")
    stages = subprocess.check_output(["git", "ls-files", "--stage"], cwd=ROOT, text=True)
    if any(line.startswith("160000 ") for line in stages.splitlines()):
        findings.append("Nested Git repository detected; publish actual source files.")
    if findings:
        print("Publication checks failed; possible values are intentionally hidden:")
        print("\n".join(findings))
        return 1
    print(f"Checked {len(names)} publishable files: no common credential patterns or nested Git links found.")
    return 0


if __name__ == "__main__":
    sys.exit(scan())
