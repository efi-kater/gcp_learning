import argparse
import subprocess
import json
import sys

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}\n{e.stderr}", file=sys.stderr)
        return None

def check_pods():
    print("\n=== Pod Health Check ===")
    output = run_cmd(["kubectl", "get", "pods", "--no-headers", "-o", "custom-columns=NAME:.metadata.name,STATUS:.status.phase"])
    if output is None:
        print("Failed to get pods.")
        return
    lines = output.strip().split('\n')
    problems = False
    for line in lines:
        name, status = line.split(None, 1)
        if status != "Running":
            print(f"⚠️ Pod '{name}' status: {status}")
            problems = True
        else:
            print(f"✅ Pod '{name}' is Running")
    if not problems:
        print("All pods are running.")

def check_services():
    print("\n=== Service EXTERNAL-IP Check ===")
    output = run_cmd(["kubectl", "get", "svc", "--no-headers"])
    if output is None:
        print("Failed to get services.")
        return
    lines = output.strip().split('\n')
    problems = False
    for line in lines:
        parts = line.split()
        name = parts[0]
        external_ip = parts[3] if len(parts) > 3 else None
        if external_ip in ("", "<none>", "<pending>", None):
            print(f"⚠️ Service '{name}' has no EXTERNAL-IP")
            problems = True
        else:
            print(f"✅ Service '{name}' EXTERNAL-IP: {external_ip}")
    if not problems:
        print("All services have EXTERNAL-IP assigned.")

def show_logs():
    print("\n=== Pod Logs (first 10 lines) ===")
    pods_output = run_cmd(["kubectl", "get", "pods", "-o", "jsonpath={.items[*].metadata.name}"])
    if pods_output is None:
        print("Failed to get pod names.")
        return
    pod_names = pods_output.strip().split()
    if not pod_names:
        print("No pods found.")
        return
    for pod in pod_names:
        print(f"\nLogs from pod '{pod}':")
        logs = run_cmd(["kubectl", "logs", pod, "--tail=10"])
        if logs:
            print(logs.strip())
        else:
            print("No logs or failed to fetch logs.")

def check_env_vars():
    print("\n=== Pod Environment Variables (APP_MODE, ENV) ===")
    pods_output = run_cmd(["kubectl", "get", "pods", "-o", "json"])
    if pods_output is None:
        print("Failed to get pods JSON.")
        return
    pods_json = json.loads(pods_output)
    for pod in pods_json.get("items", []):
        pod_name = pod["metadata"]["name"]
        containers = pod.get("spec", {}).get("containers", [])
        found_vars = []
        for container in containers:
            envs = container.get("env", [])
            for env in envs:
                if env.get("name") in ("APP_MODE", "ENV"):
                    found_vars.append(f"{env['name']}={env.get('value', 'undefined')}")
        if found_vars:
            print(f"Pod '{pod_name}': " + ", ".join(found_vars))
        else:
            print(f"Pod '{pod_name}': No APP_MODE or ENV vars found.")

def cleanup_resources():
    print("\n=== Cleanup: Deleting all pods and services ===")
    # Warning: This will delete all pods and services in the current namespace!
    confirm = input("Are you sure you want to delete ALL pods and services? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cleanup aborted.")
        return
    pods = run_cmd(["kubectl", "get", "pods", "-o", "jsonpath={.items[*].metadata.name}"])
    svcs = run_cmd(["kubectl", "get", "svc", "-o", "jsonpath={.items[*].metadata.name}"])
    if pods:
        pod_list = pods.strip().split()
        for pod in pod_list:
            print(f"Deleting pod: {pod}")
            run_cmd(["kubectl", "delete", "pod", pod])
    if svcs:
        svc_list = svcs.strip().split()
        for svc in svc_list:
            # Skip default kubernetes service which can't be deleted
            if svc == "kubernetes":
                continue
            print(f"Deleting service: {svc}")
            run_cmd(["kubectl", "delete", "svc", svc])
    print("Cleanup complete.")

def main():
    parser = argparse.ArgumentParser(description="Sanity check tool for Kubernetes test environments.")
    parser.add_argument("--cleanup", action="store_true", help="Delete all pods and services after checks")
    parser.add_argument('--app', type=str, help='Name of the app to check')
    args = parser.parse_args()

    print("\n=== Running Sanity Checks ===")
    check_pods()
    check_services()
    show_logs()
    check_env_vars()

    if args.cleanup:
        cleanup_resources()

if __name__ == "__main__":
    main()
