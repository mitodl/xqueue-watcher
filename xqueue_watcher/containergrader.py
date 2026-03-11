"""
A grader implementation that executes student code inside an isolated container.

Supports two backends:
  - "kubernetes": creates a batch/v1 Job per submission (production)
  - "docker": runs a local Docker container (local dev / CI)

This is the recommended replacement for JailedGrader on Kubernetes deployments.
No AppArmor or elevated host privileges are required.
"""

import importlib
import json
import logging
import os
import random
import tempfile
import time
import uuid
from path import Path

from .grader import Grader
from grader_support.gradelib import EndTest
from grader_support.graderutil import LANGUAGE


_BACKEND_KUBERNETES = "kubernetes"
_BACKEND_DOCKER = "docker"
_SUPPORTED_BACKENDS = (_BACKEND_KUBERNETES, _BACKEND_DOCKER)

# Label applied to all grading Jobs so they can be bulk-cleaned up if needed.
_JOB_LABEL = "app.kubernetes.io/component=xqueue-grader"


def _truncate(out):
    TOO_LONG = 5000
    if len(out) > TOO_LONG:
        out = out[:TOO_LONG] + "...OUTPUT TRUNCATED"
    return out


def _prepend_coding(code):
    return "# coding: utf8\n" + code


class ContainerGrader(Grader):
    """
    Grades student submissions by running them inside an isolated container.

    Configuration (passed as KWARGS in the conf.d JSON handler config):

      grader_root   - Path to the directory containing grader scripts.
                      Must be accessible inside the container at the same path,
                      either via a PVC (Kubernetes) or a bind mount (Docker).
      image         - Docker image to run. Should extend grader-base and include
                      all course-specific dependencies.
      backend       - "kubernetes" (default) or "docker".
      namespace     - Kubernetes namespace to create Jobs in (default: "default").
      cpu_limit     - CPU limit for the grading container (default: "500m").
      memory_limit  - Memory limit for the grading container (default: "256Mi").
      timeout       - Maximum wall-clock seconds a grading job may run (default: 20).
    """

    def __init__(
        self,
        grader_root,
        image,
        backend=_BACKEND_KUBERNETES,
        namespace="default",
        cpu_limit="500m",
        memory_limit="256Mi",
        timeout=20,
        **kwargs,
    ):
        if backend not in _SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported backend {backend!r}. Choose from {_SUPPORTED_BACKENDS}."
            )
        super().__init__(grader_root=grader_root, fork_per_item=False, **kwargs)
        self.image = image
        self.backend = backend
        self.namespace = namespace
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal: container execution
    # ------------------------------------------------------------------

    def _run(self, grader_path, code, seed):
        """
        Invoke the grader_support runner inside a container.

        Returns the raw stdout bytes from the container (JSON from run.py).
        Raises RuntimeError on timeout or non-zero exit.
        """
        if self.backend == _BACKEND_KUBERNETES:
            return self._run_kubernetes(grader_path, code, seed)
        return self._run_docker(grader_path, code, seed)

    def _run_kubernetes(self, grader_path, code, seed):
        """Create a Kubernetes Job, wait for it, collect stdout, delete it."""
        try:
            from kubernetes import client as k8s_client, config as k8s_config, watch as k8s_watch
        except ImportError:
            raise RuntimeError(
                "The 'kubernetes' package is required for the kubernetes backend. "
                "Install it with: uv add kubernetes"
            )

        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        job_name = f"xqueue-grader-{uuid.uuid4().hex[:12]}"
        batch_v1 = k8s_client.BatchV1Api()
        core_v1 = k8s_client.CoreV1Api()

        job_manifest = self._build_k8s_job(job_name, grader_path, code, seed)

        try:
            batch_v1.create_namespaced_job(namespace=self.namespace, body=job_manifest)
            self.log.debug("Created Job %s", job_name)

            stdout = self._wait_and_collect_k8s(
                batch_v1, core_v1, job_name, timeout=self.timeout
            )
            return stdout
        finally:
            try:
                batch_v1.delete_namespaced_job(
                    name=job_name,
                    namespace=self.namespace,
                    body=k8s_client.V1DeleteOptions(propagation_policy="Foreground"),
                )
            except Exception:
                self.log.warning("Failed to delete Job %s", job_name, exc_info=True)

    def _build_k8s_job(self, job_name, grader_path, code, seed):
        """Return a kubernetes Job manifest dict for the given grading run."""
        from kubernetes import client as k8s_client

        grader_rel = str(Path(grader_path).basename())
        grader_dir = str(Path(grader_path).dirname())

        return k8s_client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=k8s_client.V1ObjectMeta(
                name=job_name,
                labels={
                    "app.kubernetes.io/component": "xqueue-grader",
                    "app.kubernetes.io/managed-by": "xqueue-watcher",
                },
            ),
            spec=k8s_client.V1JobSpec(
                backoff_limit=0,
                active_deadline_seconds=self.timeout,
                ttl_seconds_after_finished=300,
                template=k8s_client.V1PodTemplateSpec(
                    spec=k8s_client.V1PodSpec(
                        restart_policy="Never",
                        security_context=k8s_client.V1PodSecurityContext(
                            run_as_non_root=True,
                            run_as_user=1000,
                        ),
                        containers=[
                            k8s_client.V1Container(
                                name="grader",
                                image=self.image,
                                args=[grader_rel, "submission.py", str(seed)],
                                working_dir=grader_dir,
                                env=[
                                    k8s_client.V1EnvVar(
                                        name="SUBMISSION_CODE",
                                        value=code,
                                    ),
                                ],
                                resources=k8s_client.V1ResourceRequirements(
                                    limits={
                                        "cpu": self.cpu_limit,
                                        "memory": self.memory_limit,
                                    },
                                    requests={
                                        "cpu": "100m",
                                        "memory": "64Mi",
                                    },
                                ),
                                security_context=k8s_client.V1SecurityContext(
                                    allow_privilege_escalation=False,
                                    read_only_root_filesystem=True,
                                    capabilities=k8s_client.V1Capabilities(drop=["ALL"]),
                                ),
                            )
                        ],
                    )
                ),
            ),
        )

    def _wait_and_collect_k8s(self, batch_v1, core_v1, job_name, timeout):
        """Poll until the Job completes, then return its pod's stdout bytes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = batch_v1.read_namespaced_job(name=job_name, namespace=self.namespace)
            if job.status.succeeded:
                break
            if job.status.failed:
                raise RuntimeError(f"Grading Job {job_name} failed.")
            time.sleep(1)
        else:
            raise RuntimeError(
                f"Grading Job {job_name} exceeded timeout of {timeout}s."
            )

        pods = core_v1.list_namespaced_pod(
            namespace=self.namespace,
            label_selector=f"job-name={job_name}",
        )
        if not pods.items:
            raise RuntimeError(f"No pods found for Job {job_name}.")

        pod_name = pods.items[0].metadata.name
        log = core_v1.read_namespaced_pod_log(name=pod_name, namespace=self.namespace)
        return log.encode("utf-8")

    def _run_docker(self, grader_path, code, seed):
        """Run a local Docker container and return stdout bytes."""
        try:
            import docker as docker_sdk
        except ImportError:
            raise RuntimeError(
                "The 'docker' package is required for the docker backend. "
                "Install it with: uv add docker"
            )

        grader_dir = str(Path(grader_path).dirname().absolute())
        grader_rel = str(Path(grader_path).basename())

        client = docker_sdk.from_env()
        try:
            result = client.containers.run(
                image=self.image,
                command=[grader_rel, "submission.py", str(seed)],
                working_dir="/grader",
                environment={"SUBMISSION_CODE": code},
                volumes={grader_dir: {"bind": "/grader", "mode": "ro"}},
                mem_limit=self.memory_limit,
                nano_cpus=int(_parse_cpu_millis(self.cpu_limit) * 1_000_000),
                network_disabled=True,
                read_only=True,
                remove=True,
                stdout=True,
                stderr=False,
                timeout=self.timeout,
            )
        except docker_sdk.errors.ContainerError as exc:
            raise RuntimeError(
                f"Grading container exited with error: {exc}"
            ) from exc

        return result if isinstance(result, bytes) else result.encode("utf-8")

    # ------------------------------------------------------------------
    # Public grading interface (mirrors JailedGrader.grade)
    # ------------------------------------------------------------------

    def grade(self, grader_path, grader_config, submission):
        import gettext
        import sys

        if not isinstance(submission, str):
            self.log.warning("Submission is NOT unicode")

        results = {
            "errors": [],
            "tests": [],
            "correct": False,
            "score": 0,
        }

        if grader_config.get("skip_grader", False):
            results["correct"] = True
            results["score"] = 1
            self.log.debug("Skipping the grader.")
            return results

        lang = grader_config.get("lang", LANGUAGE)
        locale_dir = self.grader_root / "conf" / "locale"
        if locale_dir.exists():
            trans = gettext.translation(
                "graders", localedir=str(locale_dir), fallback=True, languages=[lang]
            )
            trans.install(names=None)

        # Load the grader module to access its test definitions and preprocessors.
        # The module runs outside the sandbox (trusted code).
        sf_loader = importlib.machinery.SourceFileLoader("grader_module", str(grader_path))
        grader_module = sf_loader.load_module()
        grader = grader_module.grader

        errors = grader.input_errors(submission)
        if errors:
            results["errors"].extend(errors)
            return results

        answer_path = Path(grader_path).dirname() / "answer.py"
        with open(answer_path, "rb") as f:
            answer = f.read().decode("utf-8")

        processed_answer = _prepend_coding(grader.preprocess(answer))
        processed_submission = _prepend_coding(grader.preprocess(submission))

        seed = str(random.randint(0, 20000))

        # Run the staff answer inside the container.
        expected_ok = False
        expected_outputs = None
        expected_exc = None
        try:
            expected_outputs = self._run(grader_path, processed_answer, seed)
            if expected_outputs:
                expected = json.loads(expected_outputs.decode("utf-8"))
                expected_ok = True
        except Exception:
            expected_exc = sys.exc_info()
        else:
            if expected_ok:
                if (
                    expected["exceptions"]
                    or expected["grader"]["status"] != "ok"
                    or expected["submission"]["status"] != "ok"
                ):
                    expected_ok = False

        if not expected_ok:
            results["errors"].append(
                "There was a problem running the staff solution (Staff debug: L364)"
            )
            self.log.error(
                "Couldn't run staff solution. grader = %s, output: %r",
                grader_path,
                expected_outputs,
                exc_info=expected_exc,
            )
            return results

        # Run the student submission inside the container.
        actual_ok = False
        actual_outputs = None
        actual_exc = None
        try:
            actual_outputs = self._run(grader_path, processed_submission, seed)
            if actual_outputs:
                actual = json.loads(actual_outputs.decode("utf-8"))
                actual_ok = True
            else:
                results["errors"].append(
                    "There was a problem running your solution (Staff debug: L379)."
                )
        except Exception:
            actual_exc = sys.exc_info()
        else:
            if actual_ok and actual["grader"]["status"] == "ok":
                if actual["submission"]["status"] != "ok":
                    shown_error = actual["submission"]["exception"] or (
                        "There was an error thrown while running your solution."
                    )
                    results["errors"].append(shown_error)
            else:
                actual_ok = False

        if not actual_ok:
            results["errors"].append(
                "We couldn't run your solution (Staff debug: L397)."
            )
            self.log.error(
                "Couldn't run student solution. grader = %s, output: %r",
                grader_path,
                actual_outputs,
                exc_info=actual_exc,
            )
            return results

        corrects = []
        if not results["errors"]:
            expected_results = expected["results"]
            actual_results = actual["results"]
            if len(expected_results) != len(actual_results):
                results["errors"].append(
                    "Something went wrong: different numbers of tests ran for "
                    "your code and for our reference code."
                )
                return results

            for test, exp, act in zip(grader.tests(), expected_results, actual_results):
                exp_short_desc, exp_long_desc, exp_output = exp
                act_short_desc, act_long_desc, act_output = act
                if exp_short_desc != act_short_desc:
                    results["errors"].append(
                        "Something went wrong: tests don't match up."
                    )
                    return results
                act_output = _truncate(act_output)
                try:
                    correct = test.compare_results(exp_output, act_output)
                except EndTest as e:
                    if e is not None:
                        act_output += "\n"
                        act_output += f"*** ERROR: {e} ***"
                    correct = False
                corrects.append(correct)
                if not grader_config.get("hide_output", False):
                    results["tests"].append(
                        (exp_short_desc, exp_long_desc, correct, exp_output, act_output)
                    )

        n = len(corrects)
        results["correct"] = all(corrects) and n > 0
        results["score"] = float(sum(corrects)) / n if n > 0 else 0

        if n == 0 and not results["errors"]:
            results["errors"] = [
                "There was a problem while running your code (Staff debug: L450). "
                "Please contact the course staff for assistance."
            ]

        return results


def _parse_cpu_millis(cpu_str):
    """Convert a Kubernetes CPU string like '500m' or '1' to a float of millicores."""
    cpu_str = str(cpu_str).strip()
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1])
    return float(cpu_str) * 1000
