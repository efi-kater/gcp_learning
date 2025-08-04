from kubernetes import client, config
import time

config.load_kube_config()
v1 = client.CoreV1Api()

# Find nginx pod
pods = v1.list_namespaced_pod(namespace="default", label_selector="app=nginx")
old_pod = pods.items[0].metadata.name
print(f"Original Pod: {old_pod}")

# Delete pod
v1.delete_namespaced_pod(name=old_pod, namespace="default")
print(f"Deleted pod {old_pod}. Waiting for new pod...")

# Wait for new pod
new_pod = None
for _ in range(20):
    time.sleep(3)
    pods = v1.list_namespaced_pod(namespace="default", label_selector="app=nginx")
    if pods.items:
        new_pod = pods.items[0]
        if new_pod.status.phase == "Running":
            break

if new_pod:
    print(f"New Pod: {new_pod.metadata.name}")
    logs = v1.read_namespaced_pod_log(name=new_pod.metadata.name, namespace="default")
    print("Logs:\n", logs)
else:
    print("New pod did not become ready in time.")
