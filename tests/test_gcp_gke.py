import subprocess
import time
import pytest
import os
import json


def run_kubectl(cmd):
    try:
        result = subprocess.run(
            ["kubectl"] + cmd.split(),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # If error means resource not found, return empty string
        if "NotFound" in e.stderr or "No resources found" in e.stderr:
            return ""
        else:
            raise



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


@pytest.fixture
def create_pod_with_app_mode_env_vars():
    # Check if deployment hello-app exists
    deployments = run_kubectl("get deployments -l app=hello-app -o jsonpath={.items[*].metadata.name}").strip()

    if deployments == "" or "hello-app" not in deployments.split():
        run_kubectl("create deployment hello-app --image=gcr.io/google-samples/hello-app:1.0")
        run_kubectl("set env deployment/hello-app APP_MODE=qa ENV=CLOUD")
        run_kubectl("expose deployment hello-app --port=8080 --type=LoadBalancer")
    time.sleep(10)
    pod = run_kubectl("get pod -l app=hello-app -o jsonpath={.items[0].metadata.name}")

    yield pod  # <-- control passes to the test here

    # Teardown: runs AFTER the test finishes
    run_kubectl("delete service hello-app")
    run_kubectl("delete deployment hello-app")

def update_deployment_image():
    # update  deployment hello-app image
    run_kubectl("set image deployment/hello-app hello-app=gcr.io/google-samples/hello-app:2.0")
    time.sleep(10)

def get_pod_image(pod_json):
    if "items" in pod_json and pod_json["items"]:
        spec = pod_json["items"][0]["spec"]
    else:
        spec = pod_json["spec"]
    return spec["containers"][0]["image"]

def rollout_deployment():
    # rollback deployment hello-app
    run_kubectl("rollout undo deployment/hello-app")
    time.sleep(10)





def test_pod_logs_after_restart(restart_nginx_pod):
    """Test that nginx restarts cleanly and logs expected output."""
    logs = run_kubectl(f"logs {restart_nginx_pod}")

    assert "start worker process" in logs, "Expected log entry not found"
    assert "nginx" in logs.lower(), "Nginx not mentioned in logs"
    assert "error" not in logs.lower(), "Unexpected error found in logs"

def test_deployment_with_env_vars(create_pod_with_app_mode_env_vars):
    """Test env vars using pod spec JSON instead of exec."""
    raw = run_kubectl(f"get pod {create_pod_with_app_mode_env_vars} -o json")
    pod_json = json.loads(raw)

    env_list = pod_json["spec"]["containers"][0].get("env", [])
    env_dict = {item["name"]: item["value"] for item in env_list}

    assert env_dict.get("APP_MODE", "").upper() == "QA", "APP_MODE not set to 'QA'"
    assert env_dict.get("ENV", "").upper() == "CLOUD", "ENV not set to 'CLOUD'"

def test_deployment_update_image(create_pod_with_app_mode_env_vars):
    """Verify that the deployment's container image is the expected version."""
    raw = run_kubectl(f"get pods {create_pod_with_app_mode_env_vars} -o json")
    pod_list = json.loads(raw)

    image = get_pod_image(pod_list)

    #verify original image
    assert image.lower() == "gcr.io/google-samples/hello-app:1.0", \
        f"Image is {image}, expected 'gcr.io/google-samples/hello-app:1.0'"

    #update the image
    update_deployment_image()

    #verify updated image
    new_raw = run_kubectl(f"get pods -l app=hello-app -o json")
    new_pod_list = json.loads(new_raw)


    new_image = get_pod_image(new_pod_list)

    #verify updated image
    assert new_image.lower() == "gcr.io/google-samples/hello-app:2.0", \
        f"Image is {new_image}, expected 'gcr.io/google-samples/hello-app:2.0'"

    #rollback deployment
    rollout_deployment()

    #verify rollback succeed
    rolled_raw = run_kubectl(f"get pods -l app=hello-app -o json")
    rolled_pod_list = json.loads(rolled_raw)


    rolled_image = get_pod_image(rolled_pod_list)

    #verify rolled image
    assert rolled_image.lower() == "gcr.io/google-samples/hello-app:1.0", \
        f"Image is {rolled_image}, expected 'gcr.io/google-samples/hello-app:1.0'"





