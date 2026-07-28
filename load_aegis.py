#!/usr/bin/env python3
"""load_aegis.py — runtime loader for aegis_jailbreak.md.

Splits the unified AEGIS prompt into [SYSTEM] / [USER] / [ASSISTANT] blocks,
applies a selected LOCK, and either:

  (a) prints paste-ready triad to stdout (default)
  (b) POSTs to an OpenAI-compatible endpoint (--fire URL)
  (c) copies to clipboard (--clipboard)

Trigger phrase: "海鸥在线,你要整点薯条吗?"

Usage:
  python3 load_aegis.py                                    # default lock, prints triad
  python3 load_aegis.py --lock triple                      # use triple reset lock
  python3 load_aegis.py --lock triple -q "你的 prompt"      # inject question
  python3 load_aegis.py --fire URL -q "prompt" --key K      # POST to endpoint
  python3 load_aegis.py --clipboard                        # copy to pasteboard
  python3 load_aegis.py --info                             # show prompt size + locks
  python3 load_aegis.py --extract-system                   # print only the system block
  python3 load_aegis.py --extract-lock 4                   # print only lock N
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT_FILE = HERE / "aegis_jailbreak.md"

LOCK_HEADERS = {
    1: "## LOCK 1 — Basic",
    2: "## LOCK 2 — Double",
    3: "## LOCK 3 — GODMODE",
    4: "## LOCK 4 — Triple Reset",
}


def load_prompt() -> str:
    if not PROMPT_FILE.exists():
        sys.stderr.write(f"[!] missing: {PROMPT_FILE}\n")
        sys.exit(1)
    return PROMPT_FILE.read_text(encoding="utf-8")


def split_sections(text: str) -> dict[str, str]:
    """Split aegis_jailbreak.md into named sections by H1 / H2 markers."""
    sections: dict[str, str] = {}
    # The file uses # for top sections, ## for sub-sections
    pattern = re.compile(r"^(#+\s+.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[header] = text[start:end].strip()
    return sections


def extract_system_block(text: str) -> str:
    """Everything from the first H1 to right before '═ LOCKS' section."""
    m = re.search(
        r"^#\s+═+\s*$\s*^#\s+IDENTITY LOCK.*?(?=^#\s+═+\s*$\s*^#\s+4 LOCKS)",
        text, re.MULTILINE | re.DOTALL,
    )
    if m:
        return m.group(0)
    # fallback: first half
    return text[: text.find("# 4 LOCKS")]


def extract_lock(text: str, lock_num: int) -> str:
    """Pull out one LOCK section by number."""
    header = LOCK_HEADERS.get(lock_num)
    if not header:
        sys.stderr.write(f"[!] unknown lock: {lock_num}\n")
        sys.exit(2)

    sections = split_sections(text)
    # search for the lock — header may have different case
    for h, body in sections.items():
        if h.startswith(header.split(" — ")[0]) and f"LOCK {lock_num}" in h:
            return f"{h}\n\n{body}"
    sys.stderr.write(f"[!] lock {lock_num} not found\n")
    sys.exit(2)


def assemble_triad(prompt: str, lock_num: int, question: str = "") -> tuple[str, str, str]:
    """Return (system_block, user_block, assistant_block) ready for paste."""
    system_block = extract_system_block(prompt)
    lock_block = extract_lock(prompt, lock_num)
    # The lock already includes a placeholder {question} — we replace it
    if question:
        lock_block = lock_block.replace("{question}", question)
    else:
        lock_block = lock_block.replace("{question}", "你的 prompt 在这里 / your prompt here")

    # The lock template already contains [SYSTEM] / [USER] / [ASSISTANT] markers.
    # We just return it as the user_block (operator pastes the lock into first user msg
    # AFTER the system block is loaded into Custom Instructions).
    return system_block, lock_block, ""


def render_all(prompt: str, lock_num: int, question: str = "") -> str:
    """Paste-ready rendering for chat UIs.

    Block 1 = system block (paste into Custom Instructions)
    Block 2 = lock (paste as first user message)
    """
    system_block, lock_block, _ = assemble_triad(prompt, lock_num, question)
    out = []
    out.append("=" * 72)
    out.append("BLOCK 1 — paste into Custom Instructions / system prompt field")
    out.append("=" * 72)
    out.append(system_block)
    out.append("")
    out.append("=" * 72)
    out.append(f"BLOCK 2 — paste as first user message (LOCK {lock_num})")
    out.append("=" * 72)
    out.append(lock_block)
    out.append("")
    out.append("=" * 72)
    out.append("Next: send your actual question. 海鸥 responds in voice.")
    out.append("=" * 72)
    return "\n".join(out)


def render_messages_json(prompt: str, lock_num: int, question: str = "") -> str:
    """OpenAI-compatible messages array for API POST."""
    system_block, lock_block, _ = assemble_triad(prompt, lock_num, question)
    msgs = [
        {"role": "system", "content": system_block},
        {"role": "user", "content": lock_block},
    ]
    if question:
        msgs.append({"role": "user", "content": question})
    return json.dumps(msgs, ensure_ascii=False, indent=2)


def fire(url: str, prompt: str, lock_num: int, question: str,
         model: str, key: str = "") -> None:
    """POST triad to an OpenAI-compatible endpoint."""
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        sys.stderr.write("[!] urllib missing\n")
        return

    msgs_json = render_messages_json(prompt, lock_num, question)
    body = {
        "model": model,
        "messages": json.loads(msgs_json),
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {key}"} if key else {}),
        },
        method="POST",
    )
    sys.stderr.write(f"[+] firing LOCK {lock_num} at {url}  model={model}\n")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            try:
                msg = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                msg = json.dumps(data, ensure_ascii=False, indent=2)
            print(msg)
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"[!] HTTP {e.code}: "
                         f"{e.read().decode('utf-8', errors='replace')[:500]}\n")
    except urllib.error.URLError as e:
        sys.stderr.write(f"[!] URL error: {e.reason}\n")


def to_clipboard(text: str) -> bool:
    plat = sys.platform
    try:
        import subprocess
        if plat == "darwin":
            return subprocess.run(["pbcopy"], input=text, text=True).returncode == 0
        if plat.startswith("win"):
            return subprocess.run(["clip"], input=text, text=True).returncode == 0
        if plat.startswith("linux"):
            for cmd in ("wl-copy", "xclip", "xsel"):
                found = subprocess.run(["which", cmd], capture_output=True).returncode == 0
                if found:
                    return subprocess.run([cmd], input=text, text=True).returncode == 0
    except Exception:
        return False
    return False


def show_info(prompt: str) -> None:
    sections = split_sections(prompt)
    print("\033[1;36mAEGIS\033[0m — aegis_jailbreak.md")
    print(f"  size     : {len(prompt):,} bytes  ({len(prompt.split()):,} words)")
    print(f"  sections : {len(sections)}")
    print(f"  locks    : 1 (basic) 2 (double) 3 (godmode) 4 (triple)")
    print(f"  default  : lock 4 (triple reset, 95% pass)")
    print(f"  trigger  : 海鸥在线,你要整点薯条吗?")
    print()
    print("Available commands:")
    print("  --lock N                use lock N (1-4, default 4)")
    print("  -q 'question'           inject question into the lock")
    print("  --extract-system        print only system block")
    print("  --extract-lock N        print only lock N")
    print("  --format messages       output JSON messages array")
    print("  --clipboard             copy to pasteboard")
    print("  --fire URL              POST to OpenAI-compatible endpoint")
    print("  --key K                 API key for --fire")
    print("  --model M               model name for --fire (default: gpt-3.5-turbo)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="AEGIS runtime loader — load aegis_jailbreak.md, apply lock, fire or print.",
    )
    p.add_argument("-q", "--question", default="",
                   help="Inject your question into the lock's USER slot")
    p.add_argument("--lock", type=int, default=4, choices=[1, 2, 3, 4],
                   help="Lock tier: 1=basic(85%%), 2=double(92%%), 3=godmode(78%%), 4=triple(95%%)")
    p.add_argument("--format", default="all", choices=["all", "messages"],
                   help="Output format")
    p.add_argument("--clipboard", action="store_true",
                   help="Copy output to pasteboard")
    p.add_argument("--extract-system", action="store_true",
                   help="Print only the system block")
    p.add_argument("--extract-lock", type=int, choices=[1, 2, 3, 4],
                   help="Print only lock N")
    p.add_argument("--info", action="store_true", help="Show prompt info")
    p.add_argument("--fire", metavar="URL",
                   help="POST to OpenAI-compatible endpoint")
    p.add_argument("--key", default="", help="API key for --fire")
    p.add_argument("--model", default="gpt-3.5-turbo",
                   help="Model name for --fire")
    args = p.parse_args(argv)

    prompt = load_prompt()

    if args.info:
        show_info(prompt)
        return 0

    if args.extract_system:
        print(extract_system_block(prompt))
        return 0
    if args.extract_lock is not None:
        print(extract_lock(prompt, args.extract_lock))
        return 0

    if args.fire:
        fire(args.fire, prompt, args.lock, args.question,
             model=args.model, key=args.key)
        return 0

    if args.format == "messages":
        out = render_messages_json(prompt, args.lock, args.question)
    else:
        out = render_all(prompt, args.lock, args.question)

    if args.clipboard:
        ok = to_clipboard(out)
        sys.stderr.write("[+] copied to clipboard\n" if ok else "[!] clipboard failed\n")

    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())