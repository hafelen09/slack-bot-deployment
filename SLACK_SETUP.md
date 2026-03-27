# Slack App Configuration Guide

This guide explains how to create your Slack App, obtain the necessary API tokens, and configure the required permissions for the KubeOps Manager bot.

## 1. Create a Slack App

1. Go to the [Slack API Apps page](https://api.slack.com/apps).
2. Click **Create New App**.
3. Select **From scratch**.
4. Enter an **App Name** (e.g., `KubeOps Manager`) and select the **workspace** where you want to develop the app.
5. Click **Create App**.

## 2. Enable Socket Mode

Because this bot runs locally (or on your own internal server) without needing a public HTTP endpoint, we use **Socket Mode**.

1. In the left sidebar, under **Settings**, click on **Socket Mode**.
2. Toggle **Enable Socket Mode** to **On**.
3. You will be prompted to generate an app-level token. Enter a token name (e.g., `KubeOps Socket Token`).
4. Copy the generated token starting with `xapp-`. This is your `SLACK_APP_TOKEN`. Keep it secret!

## 3. Configure Slash Commands

The bot relies on the `/k8s` command to trigger the interactive modal and handle direct inputs.

1. In the left sidebar, under **Features**, select **Slash Commands**.
2. Click **Create New Command**.
3. Fill in the details:
   - **Command:** `/k8s`
   - **Request URL:** *(Since Socket Mode is enabled, Slack does not require a Request URL. If forced, leave it blank or see on-screen instructions).*
   - **Short Description:** KubeOps Management Interface
   - **Usage Hint:** `[action] [namespace] [deployment]`
4. Click **Save**.

## 4. Set Bot Token Scopes

Scopes define what permissions your bot has within the workspace.

1. In the left sidebar, under **Features**, select **OAuth & Permissions**.
2. Scroll down to the **Scopes** section.
3. Under **Bot Token Scopes**, click **Add an OAuth Scope** and add the following:
   - `chat:write` (Allows the bot to send messages to the channel/user)
   - `commands` (Required to respond to Slash commands)
4. *If you plan to add more features later, you can add scopes as needed.*

## 5. Enable Interactivity (For Buttons & Modals)

To allow the bot to respond when users click buttons, select dropdowns, or submit modals:

1. In the left sidebar, select **Interactivity & Shortcuts**.
2. Toggle **Interactivity** to **On**.
3. *(Since Socket Mode is on, Slack routes interactive requests directly via the WebSocket instead of requiring a Request URL).*
4. Click **Save Changes**.

## 6. Install the App to Your Workspace

1. Still on the **OAuth & Permissions** page, scroll up to the top.
2. Click the **Install to Workspace** button.
3. Review the permissions requested by the bot and click **Allow**.
4. Once installed, you will see a **Bot User OAuth Token** starting with `xoxb-`. Copy this token. This is your `SLACK_BOT_TOKEN`.

## Summary of Tokens

- **`SLACK_APP_TOKEN`:** Found under Basic Information -> App-Level Tokens (starts with `xapp-`).
- **`SLACK_BOT_TOKEN`:** Found under OAuth & Permissions (starts with `xoxb-`).

Now, add these two tokens to your `.env` file!
