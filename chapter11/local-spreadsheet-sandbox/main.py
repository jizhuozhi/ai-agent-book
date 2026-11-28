"""Exercise sandboxing and a separate Save As step on a temporary CSV file."""

import argparse
import csv
from io import StringIO
import json
import os
from pathlib import Path
from shutil import copyfile, which
import socket
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory


LAB = Path(__file__).resolve().parent
SOURCE = b"Month,Travel,Meals\nJan,12,8\nFeb,9,14\n"
EXPECTED = [
    ["Month", "Travel", "Meals", "Total"],
    ["Jan", "12", "8", "20"],
    ["Feb", "9", "14", "23"],
]
WORKER_CHECKS = {"neighbor_read_denied", "input_truncate_denied", "tcp_connection_denied"}


def command_for(backend, root, source, worker, workspace, port):
    if backend == "bwrap":
        if not which("bwrap"):
            raise RuntimeError("Install bubblewrap to run this backend")
        command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
        for path in ("/usr", "/lib", "/lib64"):
            if Path(path).exists():
                command.extend(["--ro-bind", path, path])
        for path in (source, worker):
            command.extend(["--ro-bind", str(path), str(path)])
        command.extend(["--bind", str(workspace), str(workspace), "--chdir", str(workspace)])
        return [*command, "--", "/usr/bin/python3", "-I", "-B", str(worker),
                str(source), str(workspace), str(port)]

    if not which("cc"):
        raise RuntimeError("Install a C compiler and Linux UAPI headers for Landlock")
    launcher = root / "landlock"
    subprocess.run(["cc", "-Wall", "-Wextra", "-O2", str(LAB / "landlock.c"),
                    "-o", str(launcher)], check=True, timeout=15)
    return [str(launcher), str(source), str(worker), str(workspace), str(port)]


def read_candidate(path):
    # Read the candidate once. Validation and publication use these same bytes.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Candidate is not a regular file")
        content = stream.read(4097)
    if len(content) > 4096:
        raise ValueError("Candidate exceeds the lab size limit")
    if list(csv.reader(StringIO(content.decode("utf-8")))) != EXPECTED:
        raise ValueError("Candidate does not match the authorized edit")
    return content


def save_as(original, snapshot, destination, authorized, content):
    if destination != authorized or destination == original:
        return "unauthorized_destination"
    if original.read_bytes() != snapshot:
        return "source_changed"

    with TemporaryDirectory(dir=destination.parent) as directory:
        prepared = Path(directory) / "candidate.csv"
        prepared.write_bytes(content)
        try:
            # An existing destination is never replaced, even if it appears now.
            os.link(prepared, destination)
        except FileExistsError:
            return "destination_exists"
    return "saved"


def run(backend):
    with TemporaryDirectory(prefix="chapter11-") as directory:
        root = Path(directory)
        original = root / "expenses.csv"
        original.write_bytes(SOURCE)
        snapshot = original.read_bytes()
        inputs = root / "inputs"
        inputs.mkdir()
        source = inputs / "expenses.csv"
        source.write_bytes(snapshot)
        neighbor = inputs / "neighbor.csv"
        neighbor.write_bytes(b"Synthetic private data\n")
        # Establish that ordinary host code can read the neighboring fixture.
        neighbor.read_bytes()
        worker = root / "worker.py"
        copyfile(LAB / "worker.py", worker)
        workspace = root / "workspace"
        workspace.mkdir()

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            # Check that the listener is reachable outside the sandbox.
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                peer, _ = listener.accept()
                peer.close()
            command = command_for(backend, root, source, worker, workspace, port)
            result = subprocess.run(command, cwd=workspace, check=True, timeout=10,
                                    env={"PATH": "/usr/bin:/bin"}, stdout=subprocess.PIPE,
                                    text=True)

        report = json.loads(result.stdout)
        if report.keys() != WORKER_CHECKS or any(passed is not True for passed in report.values()):
            print(json.dumps({"backend": backend, "checks": report}, indent=2))
            return 1

        report["input_copy_unchanged_after_worker"] = source.read_bytes() == snapshot
        report["original_unchanged_after_worker"] = original.read_bytes() == snapshot
        if not all(report.values()):
            print(json.dumps({"backend": backend, "checks": report}, indent=2))
            return 1

        content = read_candidate(workspace / "candidate.csv")
        destination = root / "expenses-edited.csv"
        report["authorized_edit_verified"] = True
        report["unauthorized_overwrite_rejected"] = (
            save_as(original, snapshot, original, destination, content) == "unauthorized_destination"
            and original.read_bytes() == snapshot
        )
        report["save_as_committed"] = (
            save_as(original, snapshot, destination, destination, content) == "saved"
            and destination.read_bytes() == content
        )
        report["existing_target_preserved"] = (
            save_as(original, snapshot, destination, destination, content + b"\n") == "destination_exists"
            and destination.read_bytes() == content
        )
        changed = snapshot + b"Mar,7,3\n"
        original.write_bytes(changed)
        another_destination = root / "expenses-after-conflict.csv"
        report["changed_original_preserved"] = (
            save_as(original, snapshot, another_destination, another_destination, content) == "source_changed"
            and original.read_bytes() == changed
            and not another_destination.exists()
        )
        print(json.dumps({"backend": backend, "checks": report}, indent=2))
        return 0 if all(report.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, choices=("bwrap", "landlock"))
    args = parser.parse_args()
    if sys.platform != "linux" or not Path("/usr/bin/python3").is_file():
        parser.exit(1, "This lab requires Linux with /usr/bin/python3.\n")
    try:
        return run(args.backend)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Lab did not complete: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
