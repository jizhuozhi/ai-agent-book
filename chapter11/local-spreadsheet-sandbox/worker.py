"""A fixed workload plus access checks against synthetic fixtures only."""

import csv
import errno
import json
from pathlib import Path
import socket
import sys


def denied(operation, errors):
    try:
        operation()
    except OSError as error:
        return error.errno in errors
    return False


def main():
    source, workspace, port = sys.argv[1:]
    source = Path(source)
    workspace = Path(workspace)
    with source.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    with (workspace / "candidate.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([*rows[0], "Total"])
        for name, first, second in rows[1:]:
            writer.writerow([name, first, second, int(first) + int(second)])

    with socket.socket() as connection:
        connection.settimeout(2)
        report = {
            "neighbor_read_denied": denied(
                source.with_name("neighbor.csv").read_bytes,
                {errno.EACCES, errno.EPERM, errno.ENOENT},
            ),
            "input_truncate_denied": denied(
                lambda: source.write_bytes(b"unexpected write\n"),
                {errno.EACCES, errno.EPERM, errno.EROFS},
            ),
            "tcp_connection_denied": denied(
                lambda: connection.connect(("127.0.0.1", int(port))),
                {errno.EACCES, errno.EPERM, errno.ENETUNREACH, errno.ECONNREFUSED},
            ),
        }
    print(json.dumps(report))


if __name__ == "__main__":
    main()
