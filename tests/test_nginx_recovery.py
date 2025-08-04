import subprocess
import time
import pytest


def run_kubectl(command):
    """Run a kubectl CLI command and return stdout."""
    result = subprocess.run(
        ["kubectl"] + command.split(),
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


@pytest.fixture
def restart_nginx_pod():
    """Delete nginx pod and return new pod name after restart."""
    # Get current pod name
    old_pod = run_kubectl("get pod -l app=nginx -o jsonpath={.items[0].metadata.name}")
    print(f"Old pod: {old_pod}")

    # Delete it
    run_kubectl(f"delete pod {old_pod}")
    time.sleep(10)

    # Wait for new pod to appear
    new_pod = ""
    for _ in range(10):
        new_pod = run_kubectl("get pod -l app=nginx -o jsonpath={.items[0].metadata.name}")
        if new_pod != old_pod:
            break
        time.sleep(3)

    # Confirm pod is ready
    run_kubectl(f"wait --for=condition=Ready pod/{new_pod} --timeout=60s")
    return new_pod


def test_nginx_logs_after_restart(restart_nginx_pod):
    """Test that nginx restarts cleanly and logs expected output."""
    logs = run_kubectl(f"logs {restart_nginx_pod}")

    assert "start worker process" in logs, "Expected log entry not found"
    assert "nginx" in logs.lower(), "Nginx not mentioned in logs"
    assert "error" not in logs.lower(), "Unexpected error found in logs"
