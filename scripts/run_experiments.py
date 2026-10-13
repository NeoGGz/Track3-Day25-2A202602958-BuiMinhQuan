"""Reproduce report ablations without changing the submitted client or config.

Run: python scripts/run_experiments.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gameday_lab.client import ResilientClient
from gameday_lab.factory import build_client
from gameday_lab.sim.config import load_config
from gameday_lab.sim.engine import run_scenario


class UnfilteredClient(ResilientClient):
    """Deliberately unsafe capability routing, for the requested ablation only."""

    def ladder(self, task: str) -> list[str]:
        return list(self.order)


def main() -> None:
    cfg = load_config("configs/gameday.yaml", "configs/scenarios.yaml")
    output = {}
    for budget_enabled in (True, False):
        variant = copy.deepcopy(cfg)
        variant.client["breaker"]["min_calls"] = 1_000_000_000
        variant.client["max_attempts_per_provider"] = 5
        if not budget_enabled:
            variant.client.update(retry_budget_ratio=100, retry_budget_max_tokens=1e9,
                                  retry_budget_min_per_s=1e6)
        name = "broken_breaker_budget_on" if budget_enabled else "broken_breaker_budget_off"
        output[name] = {key: run_scenario(variant, key, build_client("resilient", variant)).metrics()
                        for key in ("G2_overload_storm", "G3_brownout")}
    variant = copy.deepcopy(cfg)
    variant.client["attempt_timeout_s"] = 30.0
    output["timeout_30"] = {
        key: run_scenario(variant, key, build_client("resilient", variant)).metrics()
        for key in ("G6_provider_outage", "G4_slow_region")
    }
    client = UnfilteredClient(cfg.provider_infos(), cfg.fallback_order, cfg.client, cfg.seed)
    output["unfiltered_tools"] = run_scenario(cfg, "G6_provider_outage", client).metrics()

    cache_cfg = load_config("configs/gameday.yaml", "configs/scenarios_cache.yaml")
    cache_variants = [("threshold", "similarity_threshold", value) for value in (0.80, 0.90, 0.97)]
    cache_variants += [("ttl", "ttl_s", value) for value in (30, 60, 300)]
    cache_variants += [("stale", "max_stale_s", 0)]
    for label, parameter, value in cache_variants:
        variant = copy.deepcopy(cache_cfg)
        variant.cache[parameter] = value
        output[f"{label}_{value}"] = run_scenario(
            variant, "C1_faq_outage", build_client("cached", variant)
        ).metrics()
    Path("reports/experiments.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    for name, result in output.items():
        print(name, json.dumps(result))


if __name__ == "__main__":
    main()
