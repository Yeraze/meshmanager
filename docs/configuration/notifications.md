# Notifications Configuration

MeshManager uses [Apprise](https://github.com/caronc/apprise) for notifications, supporting 90+ notification services.

## Overview

Notifications can be sent for:

- **Scheduled Solar Reports** - Daily battery risk analysis
- **Test Notifications** - Verify your configuration

## Setting Up Notifications

1. Navigate to **Settings > Solar Schedule**
2. Enable **Scheduled Notifications**
3. Add notification times (HH:MM format, 24-hour)
4. Enter one or more Apprise URLs
5. Click **Save**

## Apprise URL Format

Each notification service has its own URL format. Here are common examples:

### Discord

```
discord://webhook_id/webhook_token
```

To get your webhook URL:
1. Server Settings > Integrations > Webhooks
2. Create or copy webhook URL
3. Extract the ID and token from the URL

### Slack

```
slack://token_a/token_b/token_c
```

Use an [Incoming Webhook](https://api.slack.com/messaging/webhooks).

### Telegram

```
tgram://bot_token/chat_id
```

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)

### Pushover

```
pover://user_key@api_token
```

Get credentials from [pushover.net](https://pushover.net).

### Email (SMTP)

```
mailto://user:password@smtp.example.com?to=recipient@example.com
```

### Gotify

```
gotify://hostname/token
```

### ntfy

```
ntfy://topic
```

Or with a self-hosted server:
```
ntfy://user:password@hostname/topic
```

### Matrix

```
matrix://user:password@hostname/#room
```

## Multiple Destinations

Add multiple Apprise URLs to send to multiple services simultaneously. Each URL should be on a separate line or comma-separated.

Example:
```
discord://webhook_id/webhook_token
tgram://bot_token/chat_id
pover://user_key@api_token
```

## Testing Notifications

Before relying on scheduled notifications:

1. Configure your Apprise URL(s)
2. Click **Send Test**
3. Verify you receive the test message
4. Check for any error messages

## Notification Timing

### Scheduled Times

Add times in 24-hour HH:MM format:

- `07:00` - Morning report
- `18:00` - Evening report
- `12:00` - Midday check

Multiple times can be configured for more frequent updates.

### Timezone

Notification times use the server's timezone. Ensure your Docker container has the correct timezone set:

```yaml
environment:
  - TZ=America/New_York
```

## Notification Content

### Solar Report Format

```
☀️ Solar Analysis (7-day lookback)

📊 Forecast vs Historical:
• Today: 4,123Wh (88% of avg) ⚠️

⚠️ Low Output Warning
Forecast output is below 75% of your 7-day average.

🔋 Nodes at Risk (4):
• AlephNull: Current 65% → Min 6% 🔴
• Lana Truck: Current 72% → Min 16% 🔴
• Trash Panda: Current 78% → Min 20% 🟡
• Wynwood Solar: Current 82% → Min 25% 🟡
```

### Chart Attachment

When supported by the notification service, a chart image is attached showing:

- Solar production forecast
- Historical comparison
- Node battery simulations

## Troubleshooting

### Notifications Not Sending

- Verify the Apprise URL format is correct
- Test the notification manually
- Check application logs for errors
- Ensure scheduled times are in the future

### Wrong Time for Notifications

- Check the server timezone setting
- Verify times are in 24-hour format
- Restart the container after timezone changes

### Missing Chart Images

- Some services don't support image attachments
- Discord, Slack, and Telegram support images
- Email will include images inline

## Supported Services

For a complete list of supported services and their URL formats, see the [Apprise Wiki](https://github.com/caronc/apprise/wiki).

Popular services include:

| Service | URL Prefix |
|---------|------------|
| Discord | `discord://` |
| Slack | `slack://` |
| Telegram | `tgram://` |
| Pushover | `pover://` |
| Email | `mailto://` |
| Gotify | `gotify://` |
| ntfy | `ntfy://` |
| Matrix | `matrix://` |
| Microsoft Teams | `msteams://` |
| Pushbullet | `pbul://` |
