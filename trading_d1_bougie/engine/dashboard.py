# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/dashboard.py
# DESCRIPTION  : Dashboard terminal Rich temps réel
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from datetime import datetime
from typing import Any, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class Dashboard:
    """
    Dashboard terminal Rich pour TRADING-D1-BOUGIE.

    Affiche en temps réel pour chaque paire surveillée :
      - Rectangle D1 (HIGH / LOW / 50% Fibo)
      - Tendance M15 (BULLISH / BEARISH / NEUTRAL)
      - Dernier signal structure (BOS / CHoCH / NONE)
      - Statut zone entrée (IN ZONE / TOO FAR / FORBIDDEN FIBO)
      - P&L position ouverte (pips + USD)
      - Stats journalières
      - Spread live
      - Éligibilité prochain trade
      - Timestamps UTC | Europe/Paris
      - Connexion IB Gateway (🟢 / 🔴)
    """

    TITLE = "📊 TRADING-D1-BOUGIE — D1 Range / M15 Structure Bot"

    def __init__(self, pairs: list[str]) -> None:
        self.pairs = pairs
        self.console = Console()
        self._state: dict[str, dict[str, Any]] = {
            pair: self._default_state() for pair in pairs
        }
        self._ib_connected: bool = False
        self._daily_stats: dict[str, dict] = {
            pair: {"trades": 0, "pnl_pips": 0.0, "pnl_usd": 0.0}
            for pair in pairs
        }

    def _default_state(self) -> dict:
        return {
            "d1_high": None,
            "d1_low": None,
            "d1_mid": None,
            "trend": "NEUTRAL",
            "structure": "NONE",
            "zone_status": "—",
            "open_pnl_pips": 0.0,
            "open_pnl_usd": 0.0,
            "spread_pips": 0.0,
            "eligible": False,
        }

    # ------------------------------------------------------------------ #
    # Mise à jour état                                                    #
    # ------------------------------------------------------------------ #

    def update_pair(self, pair: str, **kwargs: Any) -> None:
        """Met à jour les données d'affichage pour une paire."""
        if pair in self._state:
            self._state[pair].update(kwargs)

    def set_ib_connected(self, connected: bool) -> None:
        self._ib_connected = connected

    def update_daily_stats(self, pair: str, trades: int, pnl_pips: float, pnl_usd: float) -> None:
        if pair in self._daily_stats:
            self._daily_stats[pair] = {"trades": trades, "pnl_pips": pnl_pips, "pnl_usd": pnl_usd}

    # ------------------------------------------------------------------ #
    # Rendu                                                               #
    # ------------------------------------------------------------------ #

    def _build_header(self) -> Panel:
        ib_status = "[green]🟢 IB CONNECTED[/green]" if self._ib_connected else "[red]🔴 IB DISCONNECTED[/red]"
        now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        from zoneinfo import ZoneInfo
        from datetime import timezone
        paris = datetime.now(tz=ZoneInfo("Europe/Paris")).strftime("%H:%M:%S %Z")

        title = Text(self.TITLE, style="bold cyan")
        status_line = f"{ib_status}   🕐 {now_utc}  |  {paris}"
        return Panel(
            f"[bold cyan]{self.TITLE}[/bold cyan]\n{status_line}",
            border_style="cyan",
        )

    def _build_table(self) -> Table:
        table = Table(
            show_header=True,
            header_style="bold white on dark_blue",
            border_style="blue",
            expand=True,
        )

        table.add_column("Paire", style="bold yellow", width=8)
        table.add_column("D1 HIGH", justify="right", width=10)
        table.add_column("D1 LOW", justify="right", width=10)
        table.add_column("D1 MID (50%)", justify="right", width=12)
        table.add_column("Tendance M15", justify="center", width=12)
        table.add_column("Structure", justify="center", width=10)
        table.add_column("Zone", justify="center", width=16)
        table.add_column("P&L (pips)", justify="right", width=10)
        table.add_column("P&L (USD)", justify="right", width=10)
        table.add_column("Spread", justify="right", width=8)
        table.add_column("Trades J", justify="center", width=9)
        table.add_column("Eligible", justify="center", width=9)

        for pair in self.pairs:
            s = self._state[pair]
            ds = self._daily_stats[pair]

            d1_high = f"{s['d1_high']:.5f}" if s["d1_high"] else "—"
            d1_low = f"{s['d1_low']:.5f}" if s["d1_low"] else "—"
            d1_mid = f"{s['d1_mid']:.5f}" if s["d1_mid"] else "—"

            trend_color = {
                "BULLISH": "green", "BEARISH": "red", "NEUTRAL": "yellow"
            }.get(s["trend"], "white")
            trend = f"[{trend_color}]{s['trend']}[/{trend_color}]"

            struct_color = {
                "BOS": "cyan", "CHoCH": "magenta", "NONE": "dim"
            }.get(s["structure"], "white")
            structure = f"[{struct_color}]{s['structure']}[/{struct_color}]"

            zone_color = "green" if "IN ZONE" in str(s["zone_status"]) else "red"
            zone = f"[{zone_color}]{s['zone_status']}[/{zone_color}]"

            pnl_pips_color = "green" if s["open_pnl_pips"] >= 0 else "red"
            pnl_pips = f"[{pnl_pips_color}]{s['open_pnl_pips']:+.1f}[/{pnl_pips_color}]"

            pnl_usd_color = "green" if s["open_pnl_usd"] >= 0 else "red"
            pnl_usd = f"[{pnl_usd_color}]{s['open_pnl_usd']:+.2f}[/{pnl_usd_color}]"

            eligible = "[green]✅ OUI[/green]" if s["eligible"] else "[dim]❌ NON[/dim]"

            table.add_row(
                pair,
                d1_high,
                d1_low,
                d1_mid,
                trend,
                structure,
                zone,
                pnl_pips,
                pnl_usd,
                f"{s['spread_pips']:.1f}",
                str(ds["trades"]),
                eligible,
            )

        return table

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._build_header(), size=4),
            Layout(self._build_table()),
        )
        return layout

    def start_live(self) -> Live:
        """Retourne un contexte Rich Live pour l'affichage temps réel."""
        return Live(
            self.render(),
            console=self.console,
            refresh_per_second=1,
        )
