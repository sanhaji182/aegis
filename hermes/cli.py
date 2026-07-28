"""Hermes CLI — entrypoint for `hermes` shell command.

Subcommands (registered through Click):
- info                 show persona + matrix coverage
- compile <question>   build a single-message triad pack
- attack <id>          dump a single attack in full
- persona              dump 海鸥 persona block
- matrix [cats...]     dump the attack matrix (optionally filtered)
- payload              dump gpt-5.6 break payload(s)
- encode <scheme> <t> run an encoding helper
- stream-test <text>   simulate watch() on a pre-baked string
- iterative <question> emit the 5-step refinement ladder
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .attack import AttackMatrix
from .boundary import apply as boundary_apply, PRESETS as BOUNDARY_PRESETS
from .compiler import PromptCompiler
from .crypto import Vault
from .encoding import Encoder
from .iterative import apply_all, default_plans, is_refusal
from .persona import Persona, PersonaLoader
from .stream import watch, chunks as stream_chunks

console = Console()


def _build_compiler() -> PromptCompiler:
    matrix = AttackMatrix()
    persona = Persona.load()
    return PromptCompiler(matrix=matrix, persona=persona)


def _vault() -> Vault:
    return Vault()


# ── Click commands ──────────────────────────────────────────────────


@click.group()
@click.version_option(package_name="hermes-uncensored", prog_name="hermes")
def main() -> None:
    """Hermes — uncensored persona + attack triad framework."""


@main.command()
def info() -> None:
    """Show persona + matrix coverage + vault status."""
    compiler = _build_compiler()
    matrix = compiler.matrix
    persona = compiler.persona

    tbl = Table(title="Hermes Coverage", show_header=True, header_style="bold cyan")
    tbl.add_column("Item")
    tbl.add_column("Count", justify="right")
    tbl.add_row("Persona", persona.name)
    tbl.add_row("Identity Lock Rules", str(len(persona.identity_lock)))
    tbl.add_row("Few-Shot Pairs", str(len(persona.few_shots)))
    tbl.add_row("Desensitizer Terms", str(len(persona.desensitizer)))
    for cat_id, count in matrix.coverage().items():
        tbl.add_row(f"Attacks ({cat_id})", str(count))
    tbl.add_row("Encoding Schemes", str(len(Encoder.available())))
    tbl.add_row("Boundary Presets", str(len(BOUNDARY_PRESETS)))

    console.print(tbl)

    try:
        v = _vault()
        if v.info()["files"]:
            console.print("\n[green]Vault:[/green]")
            console.print(json.dumps(v.info(), indent=2, default=str))
        else:
            console.print("\n[yellow]Vault empty — run `python build_vault.py build`[/yellow]")
    except Exception as e:
        console.print(f"\n[yellow]Vault unavailable: {e}[/yellow]")


@main.command()
@click.argument("question")
@click.option("--lock", default="triple", show_default=True,
              type=click.Choice(["basic", "double", "triple", "none"]))
def compile(question: str, lock: str) -> None:
    """Build a single-message triad pack from a question."""
    compiler = _build_compiler()
    pack = compiler.triad_pack(question=question, lock=lock)
    if lock == "none":
        console.print("[cyan]# system prompt (clean)[/cyan]")
        console.print(pack["system"])
        console.print("\n[cyan]# messages[/cyan]")
    else:
        console.print(json.dumps(pack["messages"], ensure_ascii=False, indent=2))


@main.command()
@click.argument("attack_id")
def attack(attack_id: str) -> None:
    """Dump a single attack in full."""
    matrix = AttackMatrix()
    a = matrix.by_id(attack_id)
    if not a:
        console.print(f"[red]No such attack: {attack_id}[/red]")
        sys.exit(1)
    console.print(a.full())


@main.command()
def persona() -> None:
    """Dump 海鸥 persona block."""
    p = Persona.load()
    console.print(p.compile())


@main.command()
@click.argument("cats", nargs=-1)
def matrix(cats: list[str]) -> None:
    """Dump attack matrix (optionally filtered by category id)."""
    m = AttackMatrix()
    cats = list(cats) if cats else None
    console.print(m.to_block(cats=cats))


@main.command()
def payload() -> None:
    """Dump gpt-5.6 break payload(s)."""
    v = _vault()
    if "payload.bin" in v.info()["files"]:
        data = v.decrypt_json("payload.bin")
        for k, body in data.items():
            console.print(f"[cyan]## {k}[/cyan]\n")
            console.print(body)
            console.print()
    else:
        console.print("[yellow]Vault payload missing — run `python build_vault.py build`.[/yellow]")


@main.command()
@click.argument("scheme")
@click.argument("text")
def encode(scheme: str, text: str) -> None:
    """Apply an encoding scheme to text."""
    try:
        out = Encoder.encode(scheme, text)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    console.print(out)


@main.command()
@click.argument("text")
@click.option("--chunks", default=16, show_default=True)
@click.option("--no-watch", is_flag=True, help="Skip the refusal watch.")
def stream_test(text: str, chunks: int, no_watch: bool) -> None:
    """Simulate `watch()` over a text (chunked as if streamed)."""
    src = stream_chunks(text, size=chunks)
    if no_watch:
        joined = "".join(src)
        console.print(joined)
        return
    result = watch(src)
    style = "green" if not result.aborted else "red"
    console.print(f"[{style}]aborted={result.aborted} bad_token={result.bad_token!r} chunks={result.chunks}[/{style}]")
    console.print(result.text)


@main.command()
@click.argument("question")
@click.option("--lock", default="triple", show_default=True)
def iterative(question: str, lock: str) -> None:
    """Emit the 5-step refinement ladder around `question`."""
    compiler = _build_compiler()
    base = compiler.triad_pack(question=question, lock=lock)
    plans = default_plans()
    ladder = apply_all(base["messages"], plans=plans)
    for plan, msgs in zip(plans, ladder):
        console.print(f"\n[bold magenta]─── {plan.name} ───[/bold magenta]  {plan.description}")
        console.print(json.dumps(msgs, ensure_ascii=False, indent=2))


@main.command()
@click.argument("attack_id")
@click.argument("question")
def boundary(attack_id: str, question: str) -> None:
    """Apply a boundary helper to `question`."""
    try:
        out = boundary_apply(attack_id, question)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    console.print(out)


if __name__ == "__main__":
    main()
