#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Compare the CPU and memory footprint of Glances v4 and Glances v5.

Both versions are started in TUI mode inside a pseudo-terminal of a fixed size,
so that curses is active and both draw the same surface whatever the calling
terminal is. Rounds alternate (v4, v5, v4, v5, ...) and the reported figure is
the median across rounds: that is what neutralises the inter-round CPU drift of
this kind of measurement.

Caveats, also printed in the report header:
  - the two TUIs do not display the same thing, so the gap includes a rendering
    difference, not only a collection difference;
  - psutil only sees the Glances process tree: the CPU burned by the Docker or
    Podman daemon behind the containers/vms plugins is invisible here;
  - the numbers are only meaningful as a back-to-back relative comparison.
"""

import argparse
import fcntl
import os
import pty
import signal
import statistics
import struct
import subprocess
import sys
import termios
import threading
import time

import psutil

# Same modules as the `make run` and `make run-v5` targets.
VERSIONS = (("v4", "glances"), ("v5", "glances.main_v5"))

MB = 1024 * 1024


def percentile(values, ratio):
    """Return the ratio-th percentile of values (nearest-rank, no interpolation)."""
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(ratio * len(ordered))) - 1)
    return ordered[max(0, index)]


def sample_tree(root):
    """Return (cpu_seconds, rss_bytes) summed over the whole process tree.

    Glances does not fork, so the tree is a single process in practice; the
    recursion is there to stay correct if a plugin ever spawns a helper.
    """
    cpu = 0.0
    rss = 0
    for proc in [root, *root.children(recursive=True)]:
        try:
            times = proc.cpu_times()
            cpu += times.user + times.system
            rss += proc.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return cpu, rss


def spawn_tui(module, config, rows, cols):
    """Start a Glances TUI attached to a pseudo-terminal of the given size."""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    process = subprocess.Popen(
        [sys.executable, "-m", module, "-C", config],
        stdin=slave,
        stdout=slave,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
        close_fds=True,
    )
    os.close(slave)

    master_file = os.fdopen(master, "rb", buffering=0)

    # The pty buffer must be drained continuously or curses blocks on write().
    def drain():
        try:
            while master_file.read(65536):
                pass
        except (OSError, ValueError):
            pass

    threading.Thread(target=drain, daemon=True).start()

    errors = []
    threading.Thread(target=lambda: errors.append(process.stderr.read()), daemon=True).start()

    return process, master_file, errors


def terminate(process, master_file):
    """Stop the whole process group, then release the pty."""
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        process.wait(timeout=5)
    except (ProcessLookupError, PermissionError):
        pass
    finally:
        master_file.close()


def run_round(module, config, args):
    """Measure one version once. Returns the per-round metrics."""
    process, master_file, errors = spawn_tui(module, config, args.rows, args.cols)
    try:
        root = psutil.Process(process.pid)

        # Warmup: imports and first collection cycle, reported apart.
        time.sleep(args.warmup)
        if process.poll() is not None:
            raise RuntimeError(b"".join(errors).decode(errors="replace"))
        startup_cpu, startup_rss = sample_tree(root)

        cpu_pct = []
        rss_mb = []
        elapsed = []
        psutil.cpu_percent(interval=None)  # arm the system-wide counter
        system_pct = []

        cores = psutil.cpu_count() or 1
        previous_cpu, previous_time = startup_cpu, time.monotonic()
        started = previous_time

        for tick in range(1, args.duration + 1):
            deadline = started + tick
            time.sleep(max(0.0, deadline - time.monotonic()))
            if process.poll() is not None:
                raise RuntimeError(b"".join(errors).decode(errors="replace"))

            system_pct.append(psutil.cpu_percent(interval=None) * cores / 100)
            cpu, rss = sample_tree(root)
            now = time.monotonic()

            cpu_pct.append((cpu - previous_cpu) / (now - previous_time) * 100)
            rss_mb.append(rss / MB)
            elapsed.append(now - started)
            previous_cpu, previous_time = cpu, now
    finally:
        terminate(process, master_file)

    slope, _ = statistics.linear_regression(elapsed, rss_mb)
    # The background load is what the rest of the system burned during the round.
    background = statistics.fmean(system_pct) - statistics.fmean(cpu_pct)

    return {
        # Mean, not median: v4 does all its work in a single burst every
        # refresh, so at 1Hz its samples are strictly bimodal (an idle
        # second, then a second holding the whole cycle) with nothing in
        # between. The median then lands on the cliff between the two
        # populations and only reflects the phase between the sampler and
        # the refresh loop -- it swung from 2.0 to 3.5 %core across
        # identical rounds while the mean stayed at 5.26. The mean over the
        # window is exactly total CPU / elapsed, which is what we want.
        # p95 below keeps the burstiness visible, since that is a real
        # difference between the two architectures.
        "cpu_mean": statistics.fmean(cpu_pct),
        "cpu_p95": percentile(cpu_pct, 0.95),
        "rss_mean": statistics.fmean(rss_mb),
        "rss_max": max(rss_mb),
        "rss_slope": slope * 60,
        "startup_cpu": startup_cpu,
        "startup_rss": startup_rss / MB,
        "background": max(0.0, background),
    }


ROWS = (
    ("CPU  %core   mean", "cpu_mean", "{:.2f}", True),
    ("CPU  %core   p95", "cpu_p95", "{:.2f}", True),
    ("RSS  MB      mean", "rss_mean", "{:.1f}", True),
    ("RSS  MB      max", "rss_max", "{:.1f}", True),
    ("RSS  MB/min  slope", "rss_slope", "{:+.2f}", False),
    ("Startup      CPU-s", "startup_cpu", "{:.2f}", True),
    ("Startup      RSS MB", "startup_rss", "{:.1f}", True),
)


def report(results, args):
    """Print the comparison table. results maps a version name to its rounds."""
    medians = {
        name: {key: statistics.median([r[key] for r in rounds]) for key in rounds[0]}
        for name, rounds in results.items()
    }

    print()
    print(
        f"Glances v4 vs v5 - {args.repeat} rounds alternated, warmup {args.warmup}s, "
        f"sample {args.duration}s @1Hz, pty {args.cols}x{args.rows}"
    )
    print("Median across rounds. Relative back-to-back comparison only: the two TUIs do not")
    print("display the same thing, and the CPU of the Docker/Podman daemon is not counted.")
    print()
    print(f"{'':<26}{'v4':>10}{'v5':>10}{'delta':>11}")

    for label, key, fmt, with_delta in ROWS:
        v4, v5 = medians["v4"][key], medians["v5"][key]
        if with_delta and v4:
            delta = f"{(v5 - v4) / v4 * 100:+.1f} %"
        else:
            delta = "-"
        print(f"{label:<26}{fmt.format(v4):>10}{fmt.format(v5):>10}{delta:>11}")

    print()
    print(
        "Background load (system CPU, Glances excluded): "
        f"v4 {medians['v4']['background']:.1f} %core | v5 {medians['v5']['background']:.1f} %core"
    )
    print("A large gap between those two makes the deltas above unreliable.")
    print()


def preflight(config):
    if not os.path.isfile(config):
        sys.exit(f"Configuration file not found: {config}")
    check = subprocess.run(
        [sys.executable, "-c", "import glances, glances.main_v5"],
        capture_output=True,
    )
    if check.returncode:
        sys.exit(
            "Cannot import glances and glances.main_v5 with "
            f"{sys.executable}.\nRun this script through `make bench-v4-v5`.\n"
            f"{check.stderr.decode(errors='replace')}"
        )


def main():
    parser = argparse.ArgumentParser(description="Compare the CPU and memory footprint of Glances v4 and v5.")
    parser.add_argument("-C", "--config", default="conf/glances.conf", help="Configuration file given to both versions")
    parser.add_argument("--repeat", type=int, default=3, help="Number of alternated rounds per version")
    parser.add_argument("--duration", type=int, default=60, help="Sampling duration per round, in seconds")
    parser.add_argument("--warmup", type=int, default=10, help="Discarded startup time per round, in seconds")
    parser.add_argument("--cols", type=int, default=120, help="Pseudo-terminal width")
    parser.add_argument("--rows", type=int, default=40, help="Pseudo-terminal height")
    args = parser.parse_args()

    if args.duration < 2:
        sys.exit("--duration must be at least 2 seconds")
    preflight(args.config)

    total = args.repeat * len(VERSIONS) * (args.warmup + args.duration + 2)
    print(f"Benchmarking, about {total // 60} min {total % 60} s. Please leave the machine idle.")

    results = {name: [] for name, _ in VERSIONS}
    for round_number in range(1, args.repeat + 1):
        for name, module in VERSIONS:
            print(f"  round {round_number}/{args.repeat} - {name} ...", flush=True)
            try:
                results[name].append(run_round(module, args.config, args))
            except RuntimeError as exc:
                sys.exit(f"Glances {name} exited before the end of the round:\n{exc}")
            time.sleep(2)  # let the system settle between two rounds

    report(results, args)


if __name__ == "__main__":
    main()
