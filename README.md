# slack-bot-deployment (KubeOps Manager)

A Slack Bot designed to interact with your Kubernetes cluster directly from Slack. It provides an intuitive Interactive Menu and CLI commands to fetch statuses, inspect health, check logs, view rollout history, and restart deployments.

## Features

- **Interactive Menu:** Triggered by `/k8s`, opens a dynamic Slack modal to select namespaces, deployments, and actions.
- **Get Status:** Check the current state and replicas of a deployment.
- **Check Health:** View deployment availability and pods status (e.g., catching `CrashLoopBackOff` or high restarts).
- **Fetch Logs:** Get the last 50 lines of logs from all containers in the specific deployment.
- **Rollout History:** Inspect rollout history and details of specific revisions.
- **Restart Deployment:** Safely trigger a rollout restart with confirmation prompts.

## Prerequisites

- Python 3.8+
- `slack_bolt` package
- `slack_sdk` package
- `kubectl` configured and authenticated to your cluster

## Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd slack-bot-deployment
   ```

2. **Install dependencies:**
   ```bash
   pip install slack_bolt slack_sdk
   ```

3. **Configure Environment Variables:**
   Create a `.env` file based on your environment:
   ```env
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   KUBECONFIG_PATH=/path/to/your/kubeconfig.yaml
   ```

4. **Update Script Paths (Optional):**
   Adjust the `BASE_DIR`, `ENV_FILE`, and `PYTHON_SCRIPT` variables in `start_bot.sh` if your directory structure differs.

5. **Run the bot:**
   ```bash
   chmod +x start_bot.sh
   ./start_bot.sh
   ```
   Or run it in the background:
   ```bash
   nohup ./start_bot.sh > bot.log 2>&1 &
   ```

## Usage

In your Slack workspace, simply run:
```
/k8s
```
This will open the Interactive UI. You can also use the CLI approach:
```
/k8s help
/k8s status <namespace> <deployment>
```
