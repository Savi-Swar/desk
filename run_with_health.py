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
SCRIPT_TIMEOUT_S = 1800   # must exceed the longest looping collector


def main() -> int:
    run_id = uuid.uuid4().hex[:12]
    worst = 0
    for script in sys.argv[1:]:
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, str(HERE / script)],
                               capture_output=True, text=True,
                               timeout=SCRIPT_TIMEOUT_S)
            rc, out = p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired as exc:
            # a hung script is a health record, not a dead run: the other
            # collectors in this slot still need to execute
            rc = 124
            out = f"TIMEOUT after {SCRIPT_TIMEOUT_S}s\n" + (
                (exc.stdout or b"").decode("utf-8", "replace")
                if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
        rec = {
            "ts": round(time.time(), 1),
            "run_id": run_id,
            "host": socket.gethostname().split(".")[0],
            "script": script,
            "rc": rc,
            "secs": round(time.time() - t0, 1),
            "out_tail": out[-400:].strip(),
        }
        LEDGER.parent.mkdir(exist_ok=True)
        with LEDGER.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        status = "ok" if rc == 0 else f"FAIL rc={rc}"
        print(f"[{run_id}] {script}: {status} in {rec['secs']}s")
        worst = max(worst, rc)
    return worst


if __name__ == "__main__":
    sys.exit(main())
