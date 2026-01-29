import restify from 'restify';
import {
  CloudAdapter,
  ConfigurationBotFrameworkAuthentication,
  ConfigurationBotFrameworkAuthenticationOptions,
  TurnContext,
  ConversationState,
  MemoryStorage,
  UserState,
} from 'botbuilder';
import { TimesheetBot } from './bot/timesheetBot';
import config, { validateConfig } from './config';
import reminderScheduler from './services/reminderScheduler';

// Validate configuration on startup
validateConfig();

// Create HTTP server
const server = restify.createServer({
  name: 'teams-timesheet-reminder-bot',
});

server.use(restify.plugins.bodyParser());
server.use(restify.plugins.queryParser());

// Configure bot framework authentication
const botFrameworkAuthConfig: ConfigurationBotFrameworkAuthenticationOptions = {
  MicrosoftAppId: config.microsoftAppId,
  MicrosoftAppPassword: config.microsoftAppPassword,
  MicrosoftAppTenantId: config.microsoftAppTenantId,
  MicrosoftAppType: 'MultiTenant',
};

const botFrameworkAuth = new ConfigurationBotFrameworkAuthentication(botFrameworkAuthConfig);

// Create the Cloud Adapter
const adapter = new CloudAdapter(botFrameworkAuth);

// Set up storage
const memoryStorage = new MemoryStorage();
const conversationState = new ConversationState(memoryStorage);
const userState = new UserState(memoryStorage);

// Error handling
adapter.onTurnError = async (context: TurnContext, error: Error) => {
  console.error(`[onTurnError] Unhandled error: ${error}`);
  console.error(error.stack);

  // Send a message to the user
  await context.sendActivity('Sorry, it looks like something went wrong. Please try again.');

  // Clear out state
  await conversationState.clear(context);
};

// Create the bot
const bot = new TimesheetBot();

// Initialize the reminder scheduler with the adapter
reminderScheduler.initialize(adapter as any);

// Start the scheduled reminders
reminderScheduler.startDefaultSchedule();

// Bot messaging endpoint
server.post('/api/messages', async (req, res) => {
  await adapter.process(req, res, async (context) => {
    await bot.run(context);
  });
});

// Health check endpoint
server.get('/health', (req, res, next) => {
  res.send(200, { status: 'healthy', timestamp: new Date().toISOString() });
  return next();
});

// Auth endpoints for SSO flow
server.get('/auth/start', (req, res, next) => {
  // Redirect to Microsoft login
  const authUrl = `https://login.microsoftonline.com/${config.azureAdTenantId}/oauth2/v2.0/authorize?` +
    `client_id=${config.azureAdClientId}` +
    `&response_type=code` +
    `&redirect_uri=${encodeURIComponent(config.botDomain + '/auth/callback')}` +
    `&response_mode=query` +
    `&scope=${encodeURIComponent(config.graphApiScopes.join(' '))}` +
    `&state=${req.query.state || 'default'}`;

  res.redirect(authUrl, next);
});

server.get('/auth/callback', async (req, res, next) => {
  try {
    const code = req.query.code;
    const state = req.query.state;

    if (code) {
      // In a real implementation, exchange the code for tokens
      res.send(200, {
        message: 'Authentication successful!',
        state: state,
      });
    } else {
      res.send(400, { error: 'No authorization code received' });
    }
  } catch (error) {
    console.error('Auth callback error:', error);
    res.send(500, { error: 'Authentication failed' });
  }
  return next();
});

// API endpoint to manually trigger reminders (for testing)
server.post('/api/trigger-reminders', async (req, res, next) => {
  try {
    const { userId } = req.body;
    await reminderScheduler.triggerManualReminder(userId);
    res.send(200, { message: 'Reminders triggered successfully' });
  } catch (error) {
    console.error('Error triggering reminders:', error);
    res.send(500, { error: 'Failed to trigger reminders' });
  }
  return next();
});

// API endpoint to get registered users
server.get('/api/users', (req, res, next) => {
  const users = reminderScheduler.getRegisteredUsers();
  res.send(200, { users });
  return next();
});

// Start the server
server.listen(config.port, () => {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Teams Timesheet Reminder Bot`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Server running at http://localhost:${config.port}`);
  console.log(`Bot endpoint: http://localhost:${config.port}/api/messages`);
  console.log(`Health check: http://localhost:${config.port}/health`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Reminder schedule: ${config.reminderCronSchedule}`);
  console.log(`Include manager: ${config.includeManagerInReminder}`);
  console.log(`${'='.repeat(60)}\n`);
});

// Handle graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  reminderScheduler.stopAllSchedules();
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully...');
  reminderScheduler.stopAllSchedules();
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export { adapter, bot };
