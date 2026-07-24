"""Run desk scripts under a health ledger.

Every invocation of every collector goes through here: each script gets
timed, its exit code and output tail recorded, and one JSON line appended to
collected/health.jsonl. The nightly session reads that ledger instead of
guessing from file mtimes whether the pipeline is alive.

    python run_with_health.py arb_executor_sim.py maker_sim.py maker_sim2.py

Exits nonzero if any script failed, so a CI run goes red on partial failure.
"""
import json
import pathlib
import socket
import subprocess
import sys
import time
import uuid

HERE = pathlib.Path(__file__).parent
LEDGER = HERE / "collected" / "health.jsonl"


def main() -> int:
    run_id = uuid.uuid4().hex[:12]
    worst = 0
    for script in sys.argv[1:]:
        t0 = time.time()
        p = subprocess.run([sys.executable, str(HERE / script)],
                           capture_output=True, text=True, timeout=1200)
        rec = {
            "ts": round(time.time(), 1),
            "run_id": run_id,
            "host": socket.gethostname().split(".")[0],
            "script": script,
            "rc": p.returncode,
            "secs": round(time.time() - t0, 1),
            "out_tail": (p.stdout + p.stderr)[-400:].strip(),
        }
        LEDGER.parent.mkdir(exist_ok=True)
        with LEDGER.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        status = "ok" if p.returncode == 0 else f"FAIL rc={p.returncode}"
        print(f"[{run_id}] {script}: {status} in {rec['secs']}s")
        worst = max(worst, p.returncode)
    return worst


if __name__ == "__main__":
    sys.exit(main())
