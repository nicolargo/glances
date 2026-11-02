from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentState:
    timestamp: str
    cpu: str
    memory: str
    swap: str
    load_avg: str


@dataclass(frozen=True)
class Trends:
    window_seconds: int
    cpu: str
    memory: str
    swap: str
    load_avg: str


@dataclass(frozen=True)
class ReportContext:
    current: CurrentState
    trends: Trends
    active_alerts: str | None
    top_processes: str


def construct_prompt(ctx: ReportContext) -> str:
    return f"""
    You are a system monitoring expert. Analyze the following metrics
    and produce a concise health report in 4–6 sentences maximum.

    === CURRENT STATE ===
    Timestamp : {ctx.current.timestamp}
    CPU       : {ctx.current.cpu}
    Memory    : {ctx.current.memory}
    Swap      : {ctx.current.swap}
    Load avg  : {ctx.current.load_avg}

    === TRENDS (last {ctx.trends.window_seconds}s) ===
    CPU    : {ctx.trends.cpu}
    Memory : {ctx.trends.memory}
    Swap   : {ctx.trends.swap}
    Load   : {ctx.trends.load_avg}

    === ACTIVE ALERTS ===
    {ctx.active_alerts}

    === TOP PROCESSES ===
    {ctx.top_processes}

    Provide in order:

    1. Overall health status: OK | Degraded | Critical
    2. Root cause if any issue detected
    3. Recommended action (or "None required" if healthy)
    """
