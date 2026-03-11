## Grader Base Image

This Dockerfile builds the base image that all course-specific grader images extend.

### What it contains

- Python 3.11 (slim)
- The `grader_support` package (test framework and runner used by all graders)
- An entrypoint that reads student submissions from the `SUBMISSION_CODE` environment variable

### Building

```bash
docker build -t grader-base:latest -f grader_support/Dockerfile.base .
```

Or via the Makefile:

```bash
make docker-build
```

### Course team usage

Course teams create their own image `FROM grader-base` and add their grader scripts and any Python dependencies their graders require:

```dockerfile
FROM registry.example.com/grader-base:latest

# Install course-specific Python dependencies
RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.12.0

# Copy grader scripts into the image
COPY graders/ /graders/
```

Then reference the image in the xqueue-watcher handler config (`conf.d/my-course.json`):

```json
{
  "my-course-queue": {
    "SERVER": "http://xqueue:18040",
    "CONNECTIONS": 2,
    "AUTH": ["lms", "lms"],
    "HANDLERS": [
      {
        "HANDLER": "xqueue_watcher.containergrader.ContainerGrader",
        "KWARGS": {
          "grader_root": "/graders/my-course/",
          "image": "registry.example.com/my-course-grader:latest",
          "backend": "kubernetes",
          "cpu_limit": "500m",
          "memory_limit": "256Mi",
          "timeout": 20
        }
      }
    ]
  }
}
```

### Security properties

Grader containers run with:
- Non-root user (UID 1000)
- Read-only root filesystem (`/tmp` is a tmpfs for submission files)
- No network access (`network_disabled: true` / Kubernetes NetworkPolicy)
- CPU and memory limits enforced by the container runtime
- Hard wall-clock timeout via `activeDeadlineSeconds` (Kubernetes) or `timeout` (Docker)
