# Notifications

MeshManager supports automated notifications via [Apprise](https://github.com/caronc/apprise), enabling delivery to 90+ notification services.

## Supported Services

Apprise supports a wide variety of notification services including:

- **Chat Platforms**: Discord, Slack, Microsoft Teams, Telegram
- **Push Notifications**: Pushover, Pushbullet, Gotify
- **Email**: SMTP, Gmail, AWS SES
- **And many more**

See the [Apprise documentation](https://github.com/caronc/apprise/wiki) for a full list.

## Configuration

### Setting Up Notifications

1. Navigate to **Settings > Solar Schedule**
2. Enable scheduled notifications
3. Add notification times (HH:MM format, 24-hour)
4. Enter Apprise URLs for your desired services

### Apprise URL Examples

**Discord Webhook:**
```
discord://webhook_id/webhook_token
```

**Slack Webhook:**
```
slack://token_a/token_b/token_c
```

**Telegram:**
```
tgram://bot_token/chat_id
```

**Pushover:**
```
pover://user_key/api_token
```

## Notification Content

### Solar Analysis Reports

Scheduled notifications include:

1. **Summary Header**
   - Analysis period (lookback days)

2. **Forecast Comparison**
   - Today's forecasted production
   - Percentage of historical average
   - Low output warning (if below 75%)

3. **Nodes at Risk**
   - List of nodes predicted to drop below 50% battery
   - Current battery level
   - Minimum simulated battery
   - Severity indicator (red/yellow)

4. **Chart Attachment**
   - Production chart (actual vs forecast)
   - Node simulation subplots
   - Solar background overlay

### Example Notification

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

## Test Notifications

Use the **Send Test** button to verify your notification configuration before scheduling.
