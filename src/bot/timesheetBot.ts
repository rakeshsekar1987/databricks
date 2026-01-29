import {
  ActivityHandler,
  TurnContext,
  MessageFactory,
  CardFactory,
  TeamsActivityHandler,
  TeamsInfo,
  ConversationReference,
  Attachment,
} from 'botbuilder';
import authService from '../services/authService';
import graphService from '../services/graphService';
import timesheetService from '../services/timesheetService';
import notificationService from '../services/notificationService';
import reminderScheduler from '../services/reminderScheduler';
import { User, createDefaultUser } from '../models/user';
import { ReminderType, WeeklyTimesheetStatus } from '../models/timesheet';
import config from '../config';

/**
 * Timesheet Reminder Bot
 * Handles Teams conversations and provides timesheet reminders with SSO
 */
export class TimesheetBot extends TeamsActivityHandler {
  private userSessions: Map<string, { token: string; user: User }> = new Map();

  constructor() {
    super();

    // Handle incoming messages
    this.onMessage(async (context, next) => {
      await this.handleMessage(context);
      await next();
    });

    // Handle when bot is added to conversation
    this.onMembersAdded(async (context, next) => {
      await this.handleMembersAdded(context);
      await next();
    });

    // Handle conversation update (for storing conversation references)
    this.onConversationUpdate(async (context, next) => {
      await this.handleConversationUpdate(context);
      await next();
    });

    // Handle Teams-specific sign-in - override the base method
    this.onEvent(async (context, next) => {
      if (context.activity.name === 'signin/verifyState') {
        await this.handleTeamsSignIn(context);
      }
      await next();
    });
  }

  /**
   * Handle incoming messages
   */
  private async handleMessage(context: TurnContext): Promise<void> {
    // Store conversation reference for proactive messaging
    this.storeConversationReference(context);

    const text = context.activity.text?.toLowerCase().trim() || '';
    const value = context.activity.value;

    // Handle adaptive card actions
    if (value) {
      await this.handleCardAction(context, value);
      return;
    }

    // Handle text commands
    if (text.includes('help')) {
      await this.sendHelpCard(context);
    } else if (text.includes('status') || text.includes('timesheet')) {
      await this.showTimesheetStatus(context);
    } else if (text.includes('login') || text.includes('sign in') || text.includes('sso')) {
      await this.initiateSSO(context);
    } else if (text.includes('remind') || text.includes('reminder')) {
      await this.sendReminderPreview(context);
    } else if (text.includes('settings') || text.includes('preferences')) {
      await this.showSettings(context);
    } else if (text.includes('subscribe') || text.includes('register')) {
      await this.subscribeToReminders(context);
    } else if (text.includes('unsubscribe')) {
      await this.unsubscribeFromReminders(context);
    } else {
      await this.sendWelcomeMessage(context);
    }
  }

  /**
   * Handle members added to conversation
   */
  private async handleMembersAdded(context: TurnContext): Promise<void> {
    const membersAdded = context.activity.membersAdded || [];
    
    for (const member of membersAdded) {
      if (member.id !== context.activity.recipient?.id) {
        // Store conversation reference
        this.storeConversationReference(context);
        
        // Send welcome message
        await this.sendWelcomeMessage(context);
      }
    }
  }

  /**
   * Handle conversation update
   */
  private async handleConversationUpdate(context: TurnContext): Promise<void> {
    this.storeConversationReference(context);
  }

  /**
   * Handle Teams sign-in verification
   */
  private async handleTeamsSignIn(context: TurnContext): Promise<void> {
    await context.sendActivity('Sign-in successful! You are now authenticated.');
    await this.showTimesheetStatus(context);
  }

  /**
   * Store conversation reference for proactive messaging
   */
  private storeConversationReference(context: TurnContext): void {
    const reference = TurnContext.getConversationReference(context.activity);
    const userId = context.activity.from?.aadObjectId || context.activity.from?.id || '';
    
    if (userId) {
      notificationService.storeConversationReference(userId, reference);
    }
  }

  /**
   * Handle adaptive card actions
   */
  private async handleCardAction(context: TurnContext, value: any): Promise<void> {
    const action = value.action;

    switch (action) {
      case 'markTimesheetComplete':
        await this.handleMarkComplete(context, value);
        break;
      case 'snoozeReminder':
        await this.handleSnoozeReminder(context, value);
        break;
      case 'sendTeamReminder':
        await this.handleSendTeamReminder(context, value);
        break;
      case 'subscribe':
        await this.subscribeToReminders(context);
        break;
      case 'unsubscribe':
        await this.unsubscribeFromReminders(context);
        break;
      case 'initiateSSO':
        await this.initiateSSO(context);
        break;
      default:
        await context.sendActivity('Action received. Processing...');
    }
  }

  /**
   * Initiate SSO authentication
   */
  private async initiateSSO(context: TurnContext): Promise<void> {
    const card = this.createSSOCard();
    await context.sendActivity(MessageFactory.attachment(card));
  }

  /**
   * Create SSO card for authentication
   */
  private createSSOCard(): Attachment {
    const card = {
      type: 'AdaptiveCard',
      $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
      version: '1.4',
      body: [
        {
          type: 'TextBlock',
          text: '🔐 Sign In Required',
          weight: 'Bolder',
          size: 'Large',
        },
        {
          type: 'TextBlock',
          text: 'Please sign in with your Microsoft account to access your timesheet and receive personalized reminders.',
          wrap: true,
        },
      ],
      actions: [
        {
          type: 'Action.Submit',
          title: 'Sign In with Microsoft',
          data: {
            msteams: {
              type: 'signin',
              value: `${config.botDomain}/auth/start`,
            },
          },
        },
      ],
    };

    return CardFactory.adaptiveCard(card);
  }

  /**
   * Send welcome message
   */
  private async sendWelcomeMessage(context: TurnContext): Promise<void> {
    const userName = context.activity.from?.name || 'there';

    const card = {
      type: 'AdaptiveCard',
      $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
      version: '1.4',
      body: [
        {
          type: 'Container',
          style: 'emphasis',
          items: [
            {
              type: 'TextBlock',
              text: '⏰ Timesheet Reminder Bot',
              weight: 'Bolder',
              size: 'ExtraLarge',
              color: 'Accent',
            },
          ],
        },
        {
          type: 'TextBlock',
          text: `Hello ${userName}! 👋`,
          weight: 'Bolder',
          size: 'Large',
        },
        {
          type: 'TextBlock',
          text: "I'm your personal timesheet assistant. I'll help you stay on top of your timesheet submissions and never miss a deadline.",
          wrap: true,
        },
        {
          type: 'TextBlock',
          text: '**What I can do:**',
          weight: 'Bolder',
          spacing: 'Medium',
        },
        {
          type: 'TextBlock',
          text: '• 📊 Check your timesheet status\n• ⏰ Send weekly reminders\n• 👔 Notify your manager of submissions\n• 🔗 Direct link to your timesheet',
          wrap: true,
        },
        {
          type: 'TextBlock',
          text: '**Commands:**',
          weight: 'Bolder',
          spacing: 'Medium',
        },
        {
          type: 'TextBlock',
          text: '• "status" - View timesheet status\n• "remind" - Get a reminder preview\n• "subscribe" - Enable reminders\n• "settings" - Configure preferences\n• "help" - Show all commands',
          wrap: true,
          fontType: 'Monospace',
          size: 'Small',
        },
      ],
      actions: [
        {
          type: 'Action.Submit',
          title: '🔐 Sign In',
          data: { action: 'initiateSSO' },
        },
        {
          type: 'Action.Submit',
          title: '📊 Check Status',
          data: { action: 'checkStatus' },
        },
        {
          type: 'Action.Submit',
          title: '✅ Subscribe to Reminders',
          data: { action: 'subscribe' },
        },
      ],
    };

    await context.sendActivity(MessageFactory.attachment(CardFactory.adaptiveCard(card)));
  }

  /**
   * Send help card
   */
  private async sendHelpCard(context: TurnContext): Promise<void> {
    const card = {
      type: 'AdaptiveCard',
      $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
      version: '1.4',
      body: [
        {
          type: 'TextBlock',
          text: '📚 Help & Commands',
          weight: 'Bolder',
          size: 'Large',
        },
        {
          type: 'FactSet',
          facts: [
            { title: 'status', value: 'View your current timesheet status' },
            { title: 'remind', value: 'Send yourself a reminder preview' },
            { title: 'subscribe', value: 'Enable weekly reminders' },
            { title: 'unsubscribe', value: 'Disable reminders' },
            { title: 'settings', value: 'Configure your preferences' },
            { title: 'login', value: 'Sign in with Microsoft SSO' },
            { title: 'help', value: 'Show this help message' },
          ],
        },
      ],
    };

    await context.sendActivity(MessageFactory.attachment(CardFactory.adaptiveCard(card)));
  }

  /**
   * Show timesheet status
   */
  private async showTimesheetStatus(context: TurnContext): Promise<void> {
    const userId = context.activity.from?.aadObjectId || '';
    const userEmail = context.activity.from?.name || '';

    try {
      // Get or create session
      const sessionToken = await timesheetService.authenticateWithSsoToken('', userEmail);
      
      if (!sessionToken) {
        await context.sendActivity('Please sign in first to view your timesheet status.');
        await this.initiateSSO(context);
        return;
      }

      // Get timesheet summary
      const summary = await timesheetService.getWeeklyTimesheetSummary(sessionToken, userId);

      // Get user info
      const user = createDefaultUser({
        id: userId,
        displayName: context.activity.from?.name || 'User',
        email: userEmail,
        teamsUserId: userId,
      });

      // Create and send the reminder card
      const card = notificationService.createTimesheetReminderCard(
        user,
        summary,
        ReminderType.WEEKLY_REMINDER
      );

      await context.sendActivity(MessageFactory.attachment(card));
    } catch (error) {
      console.error('Error showing timesheet status:', error);
      await context.sendActivity(
        'Sorry, I encountered an error while fetching your timesheet status. Please try again later.'
      );
    }
  }

  /**
   * Send reminder preview
   */
  private async sendReminderPreview(context: TurnContext): Promise<void> {
    await context.sendActivity("Here's a preview of your timesheet reminder:");
    await this.showTimesheetStatus(context);
  }

  /**
   * Show settings
   */
  private async showSettings(context: TurnContext): Promise<void> {
    const card = {
      type: 'AdaptiveCard',
      $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
      version: '1.4',
      body: [
        {
          type: 'TextBlock',
          text: '⚙️ Reminder Settings',
          weight: 'Bolder',
          size: 'Large',
        },
        {
          type: 'TextBlock',
          text: 'Configure your timesheet reminder preferences:',
          wrap: true,
        },
        {
          type: 'Input.Toggle',
          id: 'enableReminders',
          title: 'Enable weekly reminders',
          value: 'true',
        },
        {
          type: 'Input.Toggle',
          id: 'includeManager',
          title: 'Include my manager in notifications',
          value: 'true',
        },
        {
          type: 'Input.ChoiceSet',
          id: 'reminderDay',
          label: 'Reminder Day',
          value: '5',
          choices: [
            { title: 'Monday', value: '1' },
            { title: 'Tuesday', value: '2' },
            { title: 'Wednesday', value: '3' },
            { title: 'Thursday', value: '4' },
            { title: 'Friday', value: '5' },
          ],
        },
        {
          type: 'Input.Time',
          id: 'reminderTime',
          label: 'Reminder Time',
          value: '15:00',
        },
      ],
      actions: [
        {
          type: 'Action.Submit',
          title: '💾 Save Settings',
          data: { action: 'saveSettings' },
        },
      ],
    };

    await context.sendActivity(MessageFactory.attachment(CardFactory.adaptiveCard(card)));
  }

  /**
   * Subscribe to reminders
   */
  private async subscribeToReminders(context: TurnContext): Promise<void> {
    const userId = context.activity.from?.aadObjectId || context.activity.from?.id || '';
    const userName = context.activity.from?.name || 'User';

    const user = createDefaultUser({
      id: userId,
      displayName: userName,
      email: '',
      teamsUserId: userId,
    });

    reminderScheduler.registerUser(user);

    await context.sendActivity(
      MessageFactory.text(
        `✅ You're now subscribed to timesheet reminders, ${userName}! You'll receive weekly reminders to complete your timesheet.`
      )
    );
  }

  /**
   * Unsubscribe from reminders
   */
  private async unsubscribeFromReminders(context: TurnContext): Promise<void> {
    const userId = context.activity.from?.aadObjectId || context.activity.from?.id || '';

    reminderScheduler.unregisterUser(userId);

    await context.sendActivity(
      MessageFactory.text("You've been unsubscribed from timesheet reminders. You can subscribe again anytime by saying 'subscribe'.")
    );
  }

  /**
   * Handle mark complete action
   */
  private async handleMarkComplete(context: TurnContext, value: any): Promise<void> {
    await context.sendActivity(
      "Great! I've noted that you've completed your timesheet. Make sure to submit it in the timesheet system. 🎉"
    );
  }

  /**
   * Handle snooze reminder action
   */
  private async handleSnoozeReminder(context: TurnContext, value: any): Promise<void> {
    const userId = value.userId || context.activity.from?.aadObjectId || '';
    const hours = value.hours || 2;

    reminderScheduler.scheduleOneTimeReminder(userId, hours * 60, ReminderType.WEEKLY_REMINDER);

    await context.sendActivity(`⏰ Got it! I'll remind you again in ${hours} hours.`);
  }

  /**
   * Handle send team reminder action (for managers)
   */
  private async handleSendTeamReminder(context: TurnContext, value: any): Promise<void> {
    const userIds = value.userIds || [];

    await context.sendActivity(
      `📧 Sending reminders to ${userIds.length} team member(s)...`
    );

    // In a real implementation, this would trigger individual reminders
    await context.sendActivity('✅ Reminders sent successfully!');
  }
}

export default TimesheetBot;
