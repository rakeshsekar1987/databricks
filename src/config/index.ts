import dotenv from 'dotenv';
import path from 'path';

// Load environment variables
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

export interface Config {
  // Bot Configuration
  microsoftAppId: string;
  microsoftAppPassword: string;
  microsoftAppTenantId: string;

  // Azure AD SSO Configuration
  azureAdClientId: string;
  azureAdClientSecret: string;
  azureAdTenantId: string;

  // Timesheet API Configuration
  timesheetApiBaseUrl: string;
  timesheetApiKey: string;

  // Bot Settings
  botDomain: string;
  port: number;

  // Reminder Configuration
  reminderCronSchedule: string;
  includeManagerInReminder: boolean;

  // Graph API Scopes
  graphApiScopes: string[];
}

const config: Config = {
  // Bot Configuration
  microsoftAppId: process.env.MICROSOFT_APP_ID || '',
  microsoftAppPassword: process.env.MICROSOFT_APP_PASSWORD || '',
  microsoftAppTenantId: process.env.MICROSOFT_APP_TENANT_ID || '',

  // Azure AD SSO Configuration
  azureAdClientId: process.env.AZURE_AD_CLIENT_ID || '',
  azureAdClientSecret: process.env.AZURE_AD_CLIENT_SECRET || '',
  azureAdTenantId: process.env.AZURE_AD_TENANT_ID || '',

  // Timesheet API Configuration
  timesheetApiBaseUrl: process.env.TIMESHEET_API_BASE_URL || 'https://your-timesheet-app.com/api',
  timesheetApiKey: process.env.TIMESHEET_API_KEY || '',

  // Bot Settings
  botDomain: process.env.BOT_DOMAIN || 'https://localhost:3978',
  port: parseInt(process.env.PORT || '3978', 10),

  // Reminder Configuration
  reminderCronSchedule: process.env.REMINDER_CRON_SCHEDULE || '0 15 * * 5', // Friday 3 PM
  includeManagerInReminder: process.env.INCLUDE_MANAGER_IN_REMINDER === 'true',

  // Graph API Scopes
  graphApiScopes: (process.env.GRAPH_API_SCOPES || 'User.Read,User.ReadBasic.All').split(','),
};

export default config;

// Validate required configuration
export function validateConfig(): void {
  const requiredFields: (keyof Config)[] = [
    'microsoftAppId',
    'microsoftAppPassword',
    'azureAdClientId',
    'azureAdClientSecret',
    'azureAdTenantId',
  ];

  const missingFields = requiredFields.filter((field) => !config[field]);

  if (missingFields.length > 0) {
    console.warn(`Warning: Missing required configuration fields: ${missingFields.join(', ')}`);
    console.warn('The bot may not function correctly without these settings.');
  }
}
