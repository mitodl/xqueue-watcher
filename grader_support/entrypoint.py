"""
Entrypoint wrapper for running grader_support.run inside a container.

Reads the student submission from the SUBMISSION_CODE environment variable
and writes it to a temporary file before invoking the standard runner.
This avoids having to pass code through argv (length limits) or requiring
a writable submission directory when the root filesystem is read-only.

Usage (set by Dockerfile ENTRYPOINT):
    python -m grader_support.entrypoint GRADER_FILE submission.py SEED
"""

import os
import sys
import tempfile

from . import run as _run_module


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python -m grader_support.entrypoint GRADER_FILE submission.py SEED",
            file=sys.stderr,
        )
        sys.exit(1)

    grader_name, submission_name, seed = sys.argv[1], sys.argv[2], sys.argv[3]
    code = os.environ.get("SUBMISSION_CODE", "")

    # Write the submission to a temp file in /tmp (always writable even with
    # read_only_root_filesystem=true, because /tmp is a separate tmpfs).
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="submission_",
        dir="/tmp",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(code)
        tmp_path = f.name

    # Temporarily add /tmp and the working directory to sys.path so that
    # grader_support.run can import the submission and grader by name.
    cwd = os.getcwd()
    sys.path.insert(0, "/tmp")
    sys.path.insert(0, cwd)

    # Rename so the module name matches what run.py expects (submission_name
    # without the .py extension becomes the importable module name).
    import shutil

    dest = os.path.join("/tmp", submission_name)
    shutil.move(tmp_path, dest)

    seed_int = int(seed)
    output = _run_module.run(
        grader_name[:-3] if grader_name.endswith(".py") else grader_name,
        submission_name[:-3] if submission_name.endswith(".py") else submission_name,
        seed_int,
    )

    import json

    print(json.dumps(output))


if __name__ == "__main__":
    main()
