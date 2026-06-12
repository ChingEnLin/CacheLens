"""Rich-formatted terminal report."""

from __future__ import annotations

from ..models import SessionReport


def render(report: SessionReport) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        _render_plain(report)
        return

    console = Console()
    model_label = report.model
    if len(report.models) > 1:
        model_label = f"{report.model} (+{len(report.models) - 1} more)"
    header = (
        f"cache-lens  ·  {report.provider}  ·  {model_label}  ·  "
        f"{report.total_turns} turns"
    )
    console.print(f"[bold]{header}[/bold]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Layer")
    table.add_column("Tokens", justify="right")
    table.add_column("Cached", justify="right")
    table.add_column("Hit Rate", justify="right")
    table.add_column("Saved", justify="right")

    for layer in report.layers:
        mark = "✓" if layer.hit_rate >= 0.9 else ("✗" if layer.layer_type != "dynamic" else "")
        hit = "n/a" if layer.layer_type == "dynamic" else f"{layer.hit_rate:.1%} {mark}"
        table.add_row(
            layer.name,
            f"{layer.total_tokens:,}",
            f"{layer.cached_tokens:,}",
            hit,
            f"${layer.savings_usd:.3f}",
        )
    console.print(table)

    console.print(f"Total input tokens   {report.total_input_tokens:,}")
    console.print(f"Actual cost          ${report.actual_cost_usd:.4f}")
    console.print(f"Cold cost (est.)     ${report.cold_cost_usd:.4f}")
    pct = (report.total_savings_usd / report.cold_cost_usd) if report.cold_cost_usd else 0.0
    console.print(f"Savings              ${report.total_savings_usd:.4f}  ({pct:.0%})")
    console.print(
        f"Ceiling              ${report.theoretical_max_savings_usd:.4f}  (max if fully cached)"
    )
    if report.total_calls:
        console.print(
            f"Latency p50 / p95    {report.latency_p50_ms} ms / {report.latency_p95_ms} ms"
        )
    if report.skipped_calls:
        console.print(
            f"[yellow]Skipped calls        {report.skipped_calls}  (not instrumented)[/yellow]"
        )

    if report.tips:
        console.print("[bold]Tips[/bold]")
        for tip in report.tips:
            console.print(f"  → {tip}")


def _render_plain(report: SessionReport) -> None:
    print(f"cache-lens · {report.provider} · {report.model} · {report.total_turns} turns")
    for layer in report.layers:
        print(
            f"  {layer.name:18} {layer.total_tokens:>10,} tokens  "
            f"{layer.cached_tokens:>10,} cached  ${layer.savings_usd:.3f} saved"
        )
    print(f"  Actual ${report.actual_cost_usd:.4f}  Cold ${report.cold_cost_usd:.4f}  "
          f"Saved ${report.total_savings_usd:.4f}")
    if report.skipped_calls:
        print(f"  Skipped calls: {report.skipped_calls} (not instrumented)")
    for tip in report.tips:
        print(f"  -> {tip}")
