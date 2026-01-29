# Teams Timesheet Reminder Bot

A Microsoft Teams bot that sends automated timesheet reminders to users and their managers. Features SSO authentication with Microsoft Azure AD for seamless integration with your timesheet system.

## Features

- **Weekly Reminders**: Automatically sends reminders to complete timesheets on a configurable schedule
- **SSO Authentication**: Uses Microsoft Teams Single Sign-On to authenticate users with your timesheet system
- **Manager Notifications**: Notifies managers about team members with incomplete timesheets
- **Interactive Cards**: Rich adaptive cards with timesheet status, direct links, and action buttons
- **Proactive Messaging**: Sends notifications even when users aren't actively using the bot
- **Configurable Schedule**: Customize reminder days, times, and frequency using cron expressions

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Microsoft      │     │  Bot Framework  │     │  Timesheet      │
│  Teams          │◄───►│  Bot Service    │◄───►│  API            │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Microsoft      │
                        │  Graph API      │
                        └─────────────────┘
```

## Prerequisites

1. **Azure Subscription** with the following resources:
   - Azure Bot Service
   - Azure App Service (or Azure Functions)
   - Azure AD App Registration

2. **Microsoft 365 Tenant** with Teams

3. **Node.js 18+** installed locally for development

4. **Timesheet Application** with REST API support

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd teams-timesheet-reminder-bot
npm install
```

### 2. Configure Environment

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Bot Framework Configuration
MICROSOFT_APP_ID=your-bot-app-id
MICROSOFT_APP_PASSWORD=your-bot-app-password
MICROSOFT_APP_TENANT_ID=your-tenant-id

# Azure AD SSO Configuration
AZURE_AD_CLIENT_ID=your-azure-ad-client-id
AZURE_AD_CLIENT_SECRET=your-azure-ad-client-secret
AZURE_AD_TENANT_ID=your-azure-ad-tenant-id

# Timesheet Application
TIMESHEET_API_BASE_URL=https://your-timesheet-app.com/api
TIMESHEET_API_KEY=your-api-key

# Bot Settings
BOT_DOMAIN=https://your-bot.azurewebsites.net
PORT=3978

# Reminder Schedule (Cron format - default: Friday 3 PM)
REMINDER_CRON_SCHEDULE=0 15 * * 5
INCLUDE_MANAGER_IN_REMINDER=true
```

### 3. Build and Run

```bash
# Build TypeScript
npm run build

# Start the bot
npm start

# Or run in development mode
npm run dev
```

## Azure AD App Registration

### Step 1: Create App Registration

1. Go to [Azure Portal](https://portal.azure.com) > Azure Active Directory > App registrations
2. Click "New registration"
3. Enter name: "Timesheet Reminder Bot"
4. Select: "Accounts in this organizational directory only"
5. Click "Register"

### Step 2: Configure API Permissions

Add the following Microsoft Graph permissions:

| Permission | Type | Description |
|------------|------|-------------|
| User.Read | Delegated | Read user profile |
| User.ReadBasic.All | Delegated | Read basic user info |
| Mail.Send | Delegated | Send emails |
| User.Read.All | Application | Read all users (for manager lookup) |

### Step 3: Configure Authentication

1. Add redirect URI: `https://your-bot.azurewebsites.net/auth/callback`
2. Enable "ID tokens" under Implicit grant
3. Create a client secret and save it

### Step 4: Expose an API (for SSO)

1. Set Application ID URI: `api://your-bot.azurewebsites.net/{client-id}`
2. Add scope: `access_as_user`
3. Add authorized client applications:
   - `1fec8e78-bce4-4aaf-ab1b-5451cc387264` (Teams desktop/mobile)
   - `5e3ce6c0-2b1f-4285-8d4b-75ee78787346` (Teams web)

## Bot Framework Setup

### Step 1: Create Bot Service

1. Go to Azure Portal > Create a resource > Azure Bot
2. Fill in the details:
   - Bot handle: `timesheet-reminder-bot`
   - Subscription: Your subscription
   - Resource group: Create new or select existing
   - Pricing tier: Standard
   - Microsoft App ID: Create new or use existing

### Step 2: Configure Messaging Endpoint

Set the messaging endpoint to: `https://your-bot.azurewebsites.net/api/messages`

### Step 3: Enable Teams Channel

1. Go to your Bot Service > Channels
2. Click on Microsoft Teams icon
3. Accept the terms and save

## Teams App Package

### Create the App Package

1. Navigate to the `appPackage` folder
2. Replace placeholder values in `manifest.json`:
   - `{{BOT_ID}}`: Your Bot's Microsoft App ID
   - `{{BOT_DOMAIN}}`: Your bot's domain (without https://)
   - `{{AAD_APP_CLIENT_ID}}`: Your Azure AD App Client ID

3. Add icon files:
   - `color.png`: 192x192 pixel color icon
   - `outline.png`: 32x32 pixel outline icon

4. Create a ZIP file containing:
   - `manifest.json`
   - `color.png`
   - `outline.png`

### Install in Teams

1. Go to Teams Admin Center or use Teams Developer Portal
2. Upload the app package (ZIP file)
3. Approve the app for your organization
4. Install the app in Teams

## Bot Commands

| Command | Description |
|---------|-------------|
| `status` | View your current timesheet status |
| `remind` | Send yourself a reminder preview |
| `subscribe` | Enable weekly reminders |
| `unsubscribe` | Disable reminders |
| `settings` | Configure your preferences |
| `help` | Show available commands |

## Reminder Schedule

The bot uses cron expressions for scheduling. Default schedule:

| Job | Schedule | Description |
|-----|----------|-------------|
| Weekly Reminder | `0 15 * * 5` | Every Friday at 3:00 PM |
| Deadline Check | `0 9 * * 1-5` | Weekdays at 9:00 AM |
| Manager Notification | `0 16 * * 5` | Every Friday at 4:00 PM |

### Cron Expression Format

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 7) (Sunday=0 or 7)
│ │ │ │ │
* * * * *
```

## Timesheet API Integration

The bot expects your timesheet API to support the following endpoints:

### Authentication

```
POST /auth/sso
Content-Type: application/json

{
  "ssoToken": "microsoft-sso-token",
  "email": "user@company.com",
  "provider": "microsoft"
}

Response:
{
  "sessionToken": "your-session-token"
}
```

### Get Weekly Summary

```
GET /timesheets/weekly-summary?userId={userId}&weekStartDate={date}
Authorization: Bearer {sessionToken}

Response:
{
  "userId": "user-id",
  "weekStartDate": "2024-01-22",
  "weekEndDate": "2024-01-28",
  "totalHours": 32,
  "expectedHours": 40,
  "status": "IN_PROGRESS",
  "isComplete": false,
  "submissionDeadline": "2024-01-26T17:00:00Z",
  "entries": [...]
}
```

## Deployment

### Option 1: Azure App Service

```bash
# Deploy using Azure CLI
az webapp up --name timesheet-reminder-bot --resource-group your-rg --runtime "NODE:18-lts"
```

### Option 2: Docker

```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Option 3: Azure Bicep

```bash
# Deploy infrastructure
az deployment group create \
  --resource-group your-rg \
  --template-file infra/azure.bicep \
  --parameters microsoftAppId=your-app-id microsoftAppPassword=your-password
```

## Development

### Local Testing

1. Install [Bot Framework Emulator](https://github.com/microsoft/BotFramework-Emulator)
2. Run `npm run dev`
3. Connect emulator to `http://localhost:3978/api/messages`

### Testing with ngrok

1. Install ngrok: `npm install -g ngrok`
2. Start tunnel: `ngrok http 3978`
3. Update bot messaging endpoint with ngrok URL

## Troubleshooting

### Bot not responding

1. Check the messaging endpoint is correctly configured
2. Verify Microsoft App ID and Password
3. Check bot service logs in Azure Portal

### SSO not working

1. Verify Azure AD app registration settings
2. Check authorized client applications include Teams client IDs
3. Ensure API permissions are granted admin consent

### Reminders not sending

1. Check cron schedule configuration
2. Verify users have subscribed to reminders
3. Check conversation references are stored correctly

## Project Structure

```
teams-timesheet-reminder-bot/
├── src/
│   ├── bot/
│   │   └── timesheetBot.ts       # Main bot logic
│   ├── config/
│   │   └── index.ts              # Configuration management
│   ├── dialogs/
│   │   └── ssoDialog.ts          # SSO authentication dialog
│   ├── models/
│   │   ├── timesheet.ts          # Timesheet data models
│   │   └── user.ts               # User data models
│   ├── services/
│   │   ├── authService.ts        # Authentication service
│   │   ├── graphService.ts       # Microsoft Graph integration
│   │   ├── notificationService.ts # Teams notifications
│   │   ├── reminderScheduler.ts  # Cron job scheduler
│   │   └── timesheetService.ts   # Timesheet API integration
│   └── index.ts                  # Application entry point
├── appPackage/
│   └── manifest.json             # Teams app manifest
├── infra/
│   └── azure.bicep               # Azure deployment template
├── Dockerfile                    # Docker configuration
├── docker-compose.yml            # Docker Compose configuration
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript configuration
└── README.md                     # This file
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please create an issue in the repository.
