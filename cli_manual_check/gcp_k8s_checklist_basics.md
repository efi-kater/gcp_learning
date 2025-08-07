# 🧪 Infra QA Sanity Checklist

Use this checklist to validate Kubernetes deployments and GCP environments during CI/CD or manual testing.

| ✅ Check              | Command                                         | Notes                                           |
|----------------------|--------------------------------------------------|-------------------------------------------------|
| Pod health           | `kubectl get pods`                              | All pods should be in `Running` or `Ready` state |
| Service availability | `kubectl get svc`                               | Ensure external IP is assigned (for LoadBalancer) |
| Log health           | `kubectl logs <pod>`                            | Check for errors, crashes, or startup failures  |
| Restart recovery     | `kubectl delete pod <pod>` → watch re-creation | Tests HA and controller behavior                |
| Env var validation   | `kubectl get pod -o json` or `exec printenv`    | Ensure app reads config/env values correctly    |
| Metrics (optional)   | via Prometheus/Grafana (if setup)               | Check resource use, alerts, uptime              |
| Teardown             | `kubectl delete deployment <app>`              | Avoid leftover resources                        |

> Tip: Automate this flow using a Python or Bash script and include it in CI.
