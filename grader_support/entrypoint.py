"""
Entrypoint for running the complete grading pipeline inside a container.

The grader scripts (grader file, answer.py) are baked into this image.
This module reads SUBMISSION_CODE from the environment, runs both the staff
answer and the student submission through the grader, compares results, and
prints the final grade as JSON to stdout.

Usage (set by Dockerfile ENTRYPOINT):
    python -m grader_support.entrypoint GRADER_FILE SEED
"""

import importlib.util
import json
import os
import sys


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python -m grader_support.entrypoint GRADER_FILE SEED",
            file=sys.stderr,
        )
        sys.exit(1)

    grader_path = sys.argv[1]
    seed = int(sys.argv[2])
    submission_code = os.environ.get("SUBMISSION_CODE", "")

    results = {"errors": [], "tests": [], "correct": False, "score": 0}

    # Load the grader module to access test definitions, preprocessors, and
    # input validators.  The grader script is baked into this image.
    spec = importlib.util.spec_from_file_location("grader_module", grader_path)
    grader_module_obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader_module_obj)
    grader = grader_module_obj.grader

    # Validate submission format before doing any work.
    errors = grader.input_errors(submission_code)
    if errors:
        results["errors"].extend(errors)
        print(json.dumps(results))
        return

    # Locale support: course graders may translate error messages.
    import gettext
    lang = os.environ.get("GRADER_LANGUAGE", "en")
    grader_dir = os.path.dirname(os.path.abspath(grader_path))
    locale_dir = os.path.join(grader_dir, "conf", "locale")
    trans = gettext.translation(
        "graders", localedir=locale_dir, fallback=True, languages=[lang]
    )
    trans.install(names=None)

    # Preprocess both the staff answer and the student submission.
    answer_path = os.path.join(grader_dir, "answer.py")
    with open(answer_path, "rb") as f:
        answer = f.read().decode("utf-8")

    processed_answer = "# coding: utf8\n" + grader.preprocess(answer)
    processed_submission = "# coding: utf8\n" + grader.preprocess(submission_code)

    # Write to /tmp, which is backed by an emptyDir volume mount in Kubernetes
    # (readOnlyRootFilesystem=True prevents writes to the root FS).
    with open("/tmp/answer.py", "w", encoding="utf-8") as f:
        f.write(processed_answer)
    with open("/tmp/submission.py", "w", encoding="utf-8") as f:
        f.write(processed_submission)

    # Make /tmp and the grader directory importable so run.py can find them.
    sys.path.insert(0, "/tmp")
    sys.path.insert(0, grader_dir)

    from . import run as run_module
    from .gradelib import EndTest

    grader_name = os.path.splitext(os.path.basename(grader_path))[0]

    # Run the staff answer first to get expected outputs.
    expected_output = run_module.run(grader_name, "answer", seed)
    expected_ok = (
        not expected_output["exceptions"]
        and expected_output["grader"]["status"] == "ok"
        and expected_output["submission"]["status"] == "ok"
    )
    if not expected_ok:
        results["errors"].append(
            "There was a problem running the staff solution (Staff debug)."
        )
        print(json.dumps(results))
        return

    # Run the student submission.
    actual_output = run_module.run(grader_name, "submission", seed)
    actual_ok = actual_output["grader"]["status"] == "ok"

    if actual_output["submission"]["status"] != "ok":
        shown_error = actual_output["submission"].get("exception") or (
            "There was an error thrown while running your solution."
        )
        results["errors"].append(shown_error)
        actual_ok = False

    if not actual_ok:
        results["errors"].append("We couldn't run your solution (Staff debug).")
        print(json.dumps(results))
        return

    # Compare test results.
    expected_results = expected_output["results"]
    actual_results = actual_output["results"]

    if len(expected_results) != len(actual_results):
        results["errors"].append(
            "Something went wrong: different numbers of tests ran for "
            "your code and for our reference code."
        )
        print(json.dumps(results))
        return

    hide_output = os.environ.get("HIDE_OUTPUT", "").lower() in ("1", "true", "yes")
    TOO_LONG = 5000
    corrects = []

    for test, exp, act in zip(grader.tests(), expected_results, actual_results):
        exp_short, exp_long, exp_out = exp
        act_short, act_long, act_out = act

        if exp_short != act_short:
            results["errors"].append("Something went wrong: tests don't match up.")
            print(json.dumps(results))
            return

        if len(act_out) > TOO_LONG:
            act_out = act_out[:TOO_LONG] + "...OUTPUT TRUNCATED"

        try:
            correct = test.compare_results(exp_out, act_out)
        except EndTest as e:
            if e is not None:
                act_out += f"\n*** ERROR: {e} ***"
            correct = False

        corrects.append(correct)
        if not hide_output:
            results["tests"].append(
                (exp_short, exp_long, correct, exp_out, act_out)
            )

    n = len(corrects)
    results["correct"] = all(corrects) and n > 0
    results["score"] = float(sum(corrects)) / n if n > 0 else 0

    if n == 0 and not results["errors"]:
        results["errors"] = [
            "There was a problem while running your code (Staff debug). "
            "Please contact the course staff for assistance."
        ]

    print(json.dumps(results))


if __name__ == "__main__":
    main()
