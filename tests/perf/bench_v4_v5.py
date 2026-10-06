#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v4 vs v5 performance comparison (merge checklist: "no regression on refresh latency").

Not a pytest module (no `test_` prefix): run it by hand, on an otherwise idle
machine, from the repository root:

    python tests/perf/bench_v4_v5.py [--config conf/glances.conf] [--runs 3]

Both versions get the same configuration file. Four measures per version,
each in a fresh process:

1. cycle: one forced update of every enabled plugin, timed in-process (v4
   `GlancesStats.update()` with every refresh timer expired; v5
   `AsyncScheduler.run_cycle()`), one cycle per second;
2. startup: from the server process start to its first answer on `/status`;
3. idle: CPU seconds the server uses per wall second, and its RSS, while
   nobody calls it. Not like for like: a v4 server collects only when asked,
   a v5 server on its own schedule (`--cached-time` dropped, decisions §10);
4. polled: the same while a client reads `/api/<v>/all` every 2 s, as an
   open WebUI does: the comparable server figure;
5. latency: sequential GET of `/api/<v>/all` and `/api/<v>/cpu`;
6. quiet: CPU per wall second and RSS of `--quiet` (standalone, no display),
   where both versions collect continuously.

Prints a JSON report; `--markdown` prints the summary table instead.
"""

import argparse
import json
import os
import socket
import statistics
import subprocess
import sys
import time

import psutil
import requests

HOST = "localhost"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q / 100 * (len(values) - 1))))]


def _summary(values):
    return {
        "median": statistics.median(values),
        "p95": _pct(values, 95),
        "max": max(values),
        "n": len(values),
    }


# ------------------------------------------------------------------ cycle


def child_cycle_v4(config, cycles):
    from glances.main import GlancesMain
    from glances.stats import GlancesStats
    from glances.timer import Timer

    sys.argv = ["glances", "-C", config, "--disable-check-update", "--quiet"]
    core = GlancesMain()
    stats = GlancesStats(config=core.get_config(), args=core.get_args())

    def expire():
        for name in stats.getPluginsList(enable=True):
            stats.get_plugin(name).refresh_timer = Timer(0)

    stats.update()  # warm-up: first sample, no rate yet
    durations = []
    for _ in range(cycles):
        time.sleep(1)
        expire()
        start = time.perf_counter()
        stats.update()
        durations.append(time.perf_counter() - start)
    return {"plugins": len(stats.getPluginsList(enable=True)), "cycle_s": durations}


def child_cycle_v5(config, cycles):
    import asyncio

    from glances.config_v5 import GlancesConfigV5
    from glances.main_v5 import assemble, build_parser

    args = build_parser().parse_args(["--no-tui", "-C", config])
    _app, scheduler, _host, _port, _tui = assemble(args, GlancesConfigV5(cli_config_path=config))

    async def run():
        await scheduler.run_cycle()  # warm-up
        durations = []
        for _ in range(cycles):
            await asyncio.sleep(1)
            start = time.perf_counter()
            await scheduler.run_cycle()
            durations.append(time.perf_counter() - start)
        await scheduler.stop()
        return durations

    durations = asyncio.run(run())
    return {"plugins": len(scheduler._entries), "cycle_s": durations}


# ------------------------------------------------------------------ server


def _server_command(version, config, port):
    if version == "v4":
        return [
            sys.executable, "-m", "glances", "-w", "--disable-webui", "--disable-check-update",
            "-C", config, "-B", "127.0.0.1", "-p", str(port),
        ]  # fmt: skip
    return [
        sys.executable, "-m", "glances.main_v5", "-s", "--disable-webui", "--disable-autodiscover",
        "-C", config, "-B", "127.0.0.1", "-p", str(port),
    ]  # fmt: skip


def measure_server(version, config, idle, requests_count, warmup):
    port = _free_port()
    base = f"http://{HOST}:{port}"
    api = f"{base}/api/{4 if version == 'v4' else 5}"
    status = f"{api}/status" if version == "v4" else f"{base}/status"
    start = time.perf_counter()
    proc = subprocess.Popen(
        _server_command(version, config, port), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    session = requests.Session()
    try:
        while True:
            if proc.poll() is not None:
                raise RuntimeError(f"{version} server exited with {proc.returncode}")
            try:
                if session.get(status, timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if time.perf_counter() - start > 120:
                raise RuntimeError(f"{version} server did not answer within 120 s")
            time.sleep(0.05)
        startup = time.perf_counter() - start

        time.sleep(warmup)
        server = psutil.Process(proc.pid)
        cpu_before = sum(server.cpu_times()[:2])
        wall_before = time.perf_counter()
        time.sleep(idle)
        cpu_idle = (sum(server.cpu_times()[:2]) - cpu_before) / (time.perf_counter() - wall_before)
        rss = server.memory_info().rss

        cpu_before = sum(server.cpu_times()[:2])
        wall_before = time.perf_counter()
        while time.perf_counter() - wall_before < idle:
            session.get(f"{api}/all", timeout=30).raise_for_status()
            time.sleep(2)
        cpu_polled = (sum(server.cpu_times()[:2]) - cpu_before) / (time.perf_counter() - wall_before)

        latency = {}
        for route in ("all", "cpu"):
            times, size = [], 0
            for _ in range(requests_count):
                t0 = time.perf_counter()
                response = session.get(f"{api}/{route}", timeout=30)
                times.append(time.perf_counter() - t0)
                response.raise_for_status()
                size = len(response.content)
            latency[route] = {**_summary(times), "bytes": size}
        return {
            "startup_s": startup,
            "idle_cpu_ratio": cpu_idle,
            "polled_cpu_ratio": cpu_polled,
            "rss_mb": rss / 2**20,
            "latency_s": latency,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


def measure_quiet(version, config, window, warmup):
    module = "glances" if version == "v4" else "glances.main_v5"
    command = [sys.executable, "-m", module, "--quiet", "-C", config]
    if version == "v4":
        command.append("--disable-check-update")
    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(warmup)
        if proc.poll() is not None:
            raise RuntimeError(f"{version} --quiet exited with {proc.returncode}")
        process = psutil.Process(proc.pid)
        cpu_before = sum(process.cpu_times()[:2])
        wall_before = time.perf_counter()
        time.sleep(window)
        cpu = (sum(process.cpu_times()[:2]) - cpu_before) / (time.perf_counter() - wall_before)
        return {"quiet_cpu_ratio": cpu, "quiet_rss_mb": process.memory_info().rss / 2**20}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


# ------------------------------------------------------------------ driver


def run_child(kind, version, config, cycles):
    out = subprocess.run(
        [sys.executable, __file__, "--child", f"{kind}-{version}", "--config", config, "--cycles", str(cycles)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="conf/glances.conf")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--idle", type=float, default=60.0, help="idle CPU window, seconds")
    parser.add_argument("--warmup", type=float, default=10.0)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--child", help=argparse.SUPPRESS)
    args = parser.parse_args()
    config = os.path.abspath(args.config)

    if args.child:
        func = {"cycle-v4": child_cycle_v4, "cycle-v5": child_cycle_v5}[args.child]
        print(json.dumps(func(config, args.cycles)))
        return

    report = {
        "machine": {
            "cpus": psutil.cpu_count(),
            "mem_gb": round(psutil.virtual_memory().total / 2**30, 1),
            "python": sys.version.split()[0],
            "psutil": psutil.__version__,
        },
        "config": args.config,
    }
    for version in ("v4", "v5"):
        runs = []
        for _ in range(args.runs):
            cycle = run_child("cycle", version, config, args.cycles)
            server = measure_server(version, config, args.idle, args.requests, args.warmup)
            quiet = measure_quiet(version, config, args.idle, args.warmup)
            runs.append({"plugins": cycle["plugins"], "cycle": _summary(cycle["cycle_s"]), **server, **quiet})
        report[version] = runs

    if not args.markdown:
        print(json.dumps(report, indent=2))
        return

    def med(version, getter):
        return statistics.median(getter(run) for run in report[version])

    rows = [
        ("plugins enabled", lambda r: r["plugins"], "{:.0f}"),
        ("full cycle, median (ms)", lambda r: r["cycle"]["median"] * 1000, "{:.1f}"),
        ("full cycle, p95 (ms)", lambda r: r["cycle"]["p95"] * 1000, "{:.1f}"),
        ("startup to /status (s)", lambda r: r["startup_s"], "{:.2f}"),
        ("server idle CPU (% of one core)", lambda r: r["idle_cpu_ratio"] * 100, "{:.1f}"),
        ("server polled every 2 s, CPU (% of one core)", lambda r: r["polled_cpu_ratio"] * 100, "{:.1f}"),
        ("server RSS (MiB)", lambda r: r["rss_mb"], "{:.0f}"),
        ("--quiet CPU (% of one core)", lambda r: r["quiet_cpu_ratio"] * 100, "{:.1f}"),
        ("--quiet RSS (MiB)", lambda r: r["quiet_rss_mb"], "{:.0f}"),
        ("GET /all, median (ms)", lambda r: r["latency_s"]["all"]["median"] * 1000, "{:.1f}"),
        ("GET /all, p95 (ms)", lambda r: r["latency_s"]["all"]["p95"] * 1000, "{:.1f}"),
        ("GET /all, size (KiB)", lambda r: r["latency_s"]["all"]["bytes"] / 1024, "{:.0f}"),
        ("GET /cpu, median (ms)", lambda r: r["latency_s"]["cpu"]["median"] * 1000, "{:.1f}"),
        ("GET /cpu, p95 (ms)", lambda r: r["latency_s"]["cpu"]["p95"] * 1000, "{:.1f}"),
    ]
    print(f"Machine: {report['machine']}, config {args.config}, {args.runs} runs (median of the runs)\n")
    print("| Measure | v4 | v5 | v5 / v4 |\n|---|---:|---:|---:|")
    for label, getter, fmt in rows:
        v4, v5 = med("v4", getter), med("v5", getter)
        ratio = f"{v5 / v4:.2f}" if v4 else "—"
        print(f"| {label} | {fmt.format(v4)} | {fmt.format(v5)} | {ratio} |")
    print("\n```json\n" + json.dumps(report, indent=2) + "\n```")


if __name__ == "__main__":
    main()
