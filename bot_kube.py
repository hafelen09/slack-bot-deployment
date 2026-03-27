import os
import subprocess
import shlex
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Get variables from OS Environment
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
KUBECONFIG_PATH = os.environ.get("KUBECONFIG_PATH")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN or not KUBECONFIG_PATH:
    print("Error: Missing environment variables! Please check your start_bot.sh script.")
    exit(1)

app = App(token=SLACK_BOT_TOKEN)
KUBECTL_BASE = f"kubectl --kubeconfig={KUBECONFIG_PATH}"

def run_kubectl(cmd):
    """Helper function to run kubectl commands safely."""
    full_cmd = f"{KUBECTL_BASE} {cmd}"
    try:
        args = shlex.split(full_cmd)
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            return f"Error:\n{result.stderr}"
        return result.stdout
    except Exception as e:
        return f"Execution Exception: {str(e)}"

def get_namespaces():
    out = run_kubectl("get ns -o json")
    try:
        data = json.loads(out)
        return [item["metadata"]["name"] for item in data.get("items", [])]
    except:
        return ["default"]

def get_deployments(namespace):
    out = run_kubectl(f"-n {namespace} get deploy -o json")
    try:
        data = json.loads(out)
        return [item["metadata"]["name"] for item in data.get("items", [])]
    except:
        return []

def build_modal_view(channel_id, selected_action="status", selected_namespace="default"):
    ns_list = get_namespaces()
    if selected_namespace not in ns_list and ns_list:
        selected_namespace = ns_list[0]

    ns_options = [{"text": {"type": "plain_text", "text": ns}, "value": ns} for ns in ns_list[:100]]
    ns_initial = next((opt for opt in ns_options if opt["value"] == selected_namespace), ns_options[0])

    dep_list = get_deployments(selected_namespace)
    if not dep_list:
        dep_options = [{"text": {"type": "plain_text", "text": "-- No Deployments Found --"}, "value": "none"}]
    else:
        dep_options = [{"text": {"type": "plain_text", "text": dep}, "value": dep} for dep in dep_list[:100]]

    action_options = [
        {"text": {"type": "plain_text", "text": "status"}, "value": "status"},
        {"text": {"type": "plain_text", "text": "health"}, "value": "health"},
        {"text": {"type": "plain_text", "text": "logs"}, "value": "logs"},
        {"text": {"type": "plain_text", "text": "history"}, "value": "history"},
        {"text": {"type": "plain_text", "text": "restart"}, "value": "restart"},
        {"text": {"type": "plain_text", "text": "detail-rev"}, "value": "detail-rev"}
    ]
    action_initial = next((opt for opt in action_options if opt["value"] == selected_action), action_options[0])

    return {
        "type": "modal",
        "callback_id": "k8s_modal_submit",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "KubeOps Manager"},
        "submit": {"type": "plain_text", "text": "Execute"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "action_block",
                "element": {
                    "type": "static_select",
                    "action_id": "action_select",
                    "options": action_options,
                    "initial_option": action_initial
                },
                "label": {"type": "plain_text", "text": "Action"}
            },
            {
                "type": "section",
                "block_id": "namespace_block",
                "text": {"type": "mrkdwn", "text": "*Select Namespace:*"},
                "accessory": {
                    "type": "static_select",
                    "action_id": "namespace_select",
                    "options": ns_options,
                    "initial_option": ns_initial
                }
            },
            {
                "type": "input",
                "block_id": "deployment_block",
                "element": {
                    "type": "static_select",
                    "action_id": "deployment_input",
                    "options": dep_options
                },
                "label": {"type": "plain_text", "text": "Select Deployment"}
            },
            {
                "type": "input",
                "block_id": "revision_block",
                "optional": True,
                "element": {"type": "plain_text_input", "action_id": "revision_input", "placeholder": {"type": "plain_text", "text": "Only for detail-rev (e.g., 120)"}},
                "label": {"type": "plain_text", "text": "Revision Number (Optional)"}
            }
        ]
    }

def execute_k8s_logic(action, namespace, deployment, revision=None):
    """Core logic to process actions from both CLI and Modal."""
    if action == "status":
        output = run_kubectl(f"-n {namespace} get deployment {deployment}")
        return f"Status for `{deployment}`:\n```{output}```", None

    elif action == "health":
        deploy_status = run_kubectl(f"-n {namespace} get deployment {deployment} -o wide")
        all_pods = run_kubectl(f"-n {namespace} get pods")

        if "Error" in all_pods or "Exception" in all_pods:
            pod_status = all_pods
        else:
            lines = all_pods.strip().split('\n')
            if not lines:
                pod_status = "No pods found."
            else:
                header = lines[0]
                filtered_lines = [line for line in lines[1:] if deployment in line]
                if filtered_lines:
                    pod_status = header + "\n" + "\n".join(filtered_lines)
                else:
                    pod_status = "No matching pods found for this deployment."

        msg = (
            f"🏥 *Health Check for `{deployment}` in `{namespace}`*\n\n"
            f"*Deployment Status:*\n```{deploy_status.strip()}```\n"
            f"*Pods Status (Check for Restarts/CrashLoopBackOff):*\n```{pod_status.strip()}```"
        )
        return msg, None

    elif action == "logs":
        output = run_kubectl(f"-n {namespace} logs deploy/{deployment} --all-containers=true --tail=50")
        return f"Logs for `{deployment}` (last 50 lines):\n```{output}```", None

    elif action == "history":
        rs_output = run_kubectl(f"-n {namespace} get rs -o json")
        if "Error" in rs_output or "Exception" in rs_output:
            return f"Error fetching history:\n```{rs_output}```", None

        try:
            rs_data = json.loads(rs_output)
            history_data = []

            for rs in rs_data.get("items", []):
                owners = rs.get("metadata", {}).get("ownerReferences", [])
                is_owned = any(owner.get("kind") == "Deployment" and owner.get("name") == deployment for owner in owners)

                if is_owned:
                    meta_annotations = rs.get("metadata", {}).get("annotations", {})
                    rev = meta_annotations.get("deployment.kubernetes.io/revision", "0")

                    tmpl_annotations = rs.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
                    restarted_at = tmpl_annotations.get("kubectl.kubernetes.io/restartedAt", "<No rollout restart>")

                    history_data.append({"rev": int(rev), "time": restarted_at})

            if not history_data:
                return f"No history found for `{deployment}` in namespace `{namespace}`.", None

            history_data.sort(key=lambda x: x["rev"])
            output_msg = f"{'REVISION'.ljust(12)} RESTARTED-AT\n"
            output_msg += "-" * 45 + "\n"
            for item in history_data:
                output_msg += f"{str(item['rev']).ljust(12)} {item['time']}\n"

            return f"🕒 *Rollout History for `{deployment}`:*\n```{output_msg}```", None

        except Exception as e:
            return f"Error parsing cluster data: {str(e)}", None

    elif action == "detail-rev":
        if not revision:
            return "⚠️ Please provide the revision number.", None
        output = run_kubectl(f"-n {namespace} rollout history deployment/{deployment} --revision={revision}")
        return f"🔍 *Details for `{deployment}` (Revision {revision}):*\n```{output}```", None

    elif action == "restart":
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"⚠️ Are you sure you want to rollout restart deployment *{deployment}* in namespace *{namespace}*?"}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Confirm Restart"},
                        "style": "danger",
                        "action_id": "confirm_restart_action",
                        "value": f"{namespace}|{deployment}"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Cancel"},
                        "style": "primary",
                        "action_id": "cancel_restart_action",
                        "value": f"{namespace}|{deployment}"
                    }
                ]
            }
        ]
        return None, blocks

    return f"Unknown action: `{action}`.", None


@app.command("/k8s")
def handle_kube_command(ack, body, respond, client, command):
    ack()
    text = command.get("text", "").strip().split()

    if len(text) == 0:
        channel_id = command["channel_id"]
        modal_view = build_modal_view(channel_id, selected_action="status", selected_namespace="default")
        client.views_open(trigger_id=body["trigger_id"], view=modal_view)
        return

    if text[0] == "help":
        help_text = (
            "🤖 *KubeOps Bot Manual*\n"
            "Just type `/k8s` and press *Enter* to open the Interactive Menu, OR use the CLI format:\n"
            "`/k8s <action> <namespace> <deployment_name> [args]`\n\n"
            "*🛠️ Available Actions:*\n"
            "• `status` : Get the current state and replicas of a deployment.\n"
            "• `health` : 🏥 View deployment availability and check pods for `CrashLoopBackOff` or high restarts.\n"
            "• `logs` : 📋 Fetch the last 50 lines of logs from all containers in the deployment.\n"
            "• `history` : 🕒 View the rollout revision history.\n"
            "• `detail-rev` : 🔍 Inspect a specific revision. *(Requires a 4th argument: revision number)*.\n"
            "• `restart` : 🔄 Safely trigger a rollout restart for a deployment. *(Comes with a Confirm/Cancel button!)*"
        )
        respond(help_text)
        return

    if len(text) < 3:
        respond("⚠️ Invalid command format. Type `/k8s` for interactive mode or `/k8s help`.")
        return

    action, namespace, deployment = text[0], text[1], text[2]
    revision = text[3] if len(text) > 3 else None

    msg_text, msg_blocks = execute_k8s_logic(action, namespace, deployment, revision)
    if msg_blocks:
        respond(blocks=msg_blocks, response_type="in_channel")
    else:
        respond(msg_text, response_type="in_channel")


@app.action("namespace_select")
def handle_namespace_change(ack, body, client):
    ack()
    
    selected_namespace = body["actions"][0]["selected_option"]["value"]

    state_values = body["view"]["state"]["values"]
    selected_action = "status"
    if "action_block" in state_values and "action_select" in state_values["action_block"]:
        if "selected_option" in state_values["action_block"]["action_select"]:
            if state_values["action_block"]["action_select"]["selected_option"]:
                selected_action = state_values["action_block"]["action_select"]["selected_option"]["value"]

    channel_id = body["view"]["private_metadata"]
    new_view = build_modal_view(channel_id, selected_action, selected_namespace)
    client.views_update(view_id=body["view"]["id"], view=new_view)


@app.view("k8s_modal_submit")
def handle_modal_submission(ack, body, client, view):
    values = view["state"]["values"]
    action = values["action_block"]["action_select"]["selected_option"]["value"]
    namespace = values["namespace_block"]["namespace_select"]["selected_option"]["value"]
    deployment = values["deployment_block"]["deployment_input"]["selected_option"]["value"]
    revision = values["revision_block"]["revision_input"].get("value")
    channel_id = view["private_metadata"]

    if deployment == "none":
        ack()
        client.chat_postMessage(channel=channel_id, text=f"⚠️ <@{body['user']['id']}>, no valid deployment selected in `{namespace}`.")
        return

    ack()
    msg_text, msg_blocks = execute_k8s_logic(action, namespace, deployment, revision)

    if msg_blocks:
        client.chat_postMessage(channel=channel_id, blocks=msg_blocks)
    else:
        client.chat_postMessage(channel=channel_id, text=msg_text)


@app.action("confirm_restart_action")
def handle_confirm_restart(ack, body, respond, say):
    ack()
    user_id = body["user"]["id"]
    value = body["actions"][0]["value"]
    namespace, deployment = value.split("|")

    respond(f"✅ Rollout restart for `{deployment}` in `{namespace}` was *confirmed by <@{user_id}>*.\nRestarting pods, please wait...")
    run_kubectl(f"-n {namespace} rollout restart deployment/{deployment}")
    status_output = run_kubectl(f"-n {namespace} rollout status deployment/{deployment}")
    say(f"🎉 Rollout complete for `{deployment}` in `{namespace}`!\nStatus:\n```{status_output.strip()}```")


@app.action("cancel_restart_action")
def handle_cancel_restart(ack, body, respond):
    ack()
    user_id = body["user"]["id"]
    value = body["actions"][0]["value"]
    namespace, deployment = value.split("|")
    respond(f"❌ Rollout restart for `{deployment}` in `{namespace}` was *cancelled by <@{user_id}>*.")


if __name__ == "__main__":
    print("⚡️ KubeOps Bot is running with Dynamic Modal Support!")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
