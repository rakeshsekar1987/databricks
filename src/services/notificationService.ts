import {
  TurnContext,
  ConversationReference,
  Activity,
  CardFactory,
  Attachment,
  MessageFactory,
} from 'botbuilder';
import { WeeklyTimesheetSummary, WeeklyTimesheetStatus, ReminderType } from '../models/timesheet';
import { User } from '../models/user';
import config from '../config';
import timesheetService from './timesheetService';

/**
 * Notification Service for sending Teams messages and reminders
 */
export class NotificationService {
  private static instance: NotificationService;
  private conversationReferences: Map<string, Partial<ConversationReference>>;

  private constructor() {
    this.conversationReferences = new Map();
  }

  public static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService();
    }
    return NotificationService.instance;
  }

  /**
   * Store conversation reference for proactive messaging
   */
  public storeConversationReference(userId: string, reference: Partial<ConversationReference>): void {
    this.conversationReferences.set(userId, reference);
    console.log(`Stored conversation reference for user: ${userId}`);
  }

  /**
   * Get stored conversation reference
   */
  public getConversationReference(userId: string): Partial<ConversationReference> | undefined {
    return this.conversationReferences.get(userId);
  }

  /**
   * Get all stored conversation references
   */
  public getAllConversationReferences(): Map<string, Partial<ConversationReference>> {
    return this.conversationReferences;
  }

  /**
   * Create timesheet reminder adaptive card
   */
  public createTimesheetReminderCard(
    user: User,
    summary: WeeklyTimesheetSummary,
    reminderType: ReminderType
  ): Attachment {
    const timesheetUrl = timesheetService.getTimesheetUrl(user.id);
    const statusColor = this.getStatusColor(summary.status);
    const statusText = this.getStatusText(summary.status);

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
              text: '⏰ Timesheet Reminder',
              weight: 'Bolder',
              size: 'Large',
              color: 'Accent',
            },
          ],
        },
        {
          type: 'Container',
          items: [
            {
              type: 'TextBlock',
              text: `Hi ${user.displayName}!`,
              weight: 'Bolder',
              size: 'Medium',
              wrap: true,
            },
            {
              type: 'TextBlock',
              text: this.getReminderMessage(reminderType, summary),
              wrap: true,
              spacing: 'Small',
            },
          ],
        },
        {
          type: 'FactSet',
          facts: [
            {
              title: 'Week:',
              value: `${this.formatDate(summary.weekStartDate)} - ${this.formatDate(summary.weekEndDate)}`,
            },
            {
              title: 'Hours Logged:',
              value: `${summary.totalHours} / ${summary.expectedHours} hours`,
            },
            {
              title: 'Status:',
              value: statusText,
            },
            {
              title: 'Deadline:',
              value: this.formatDate(summary.submissionDeadline),
            },
            {
              title: 'Days Remaining:',
              value: summary.daysRemaining > 0 ? `${summary.daysRemaining} day(s)` : 'Overdue!',
            },
          ],
        },
        {
          type: 'Container',
          style: statusColor === 'attention' ? 'attention' : 'default',
          items: [
            {
              type: 'TextBlock',
              text: summary.isComplete
                ? '✅ Your timesheet is complete! Please submit it.'
                : `⚠️ You need to log ${summary.expectedHours - summary.totalHours} more hours.`,
              wrap: true,
              color: summary.isComplete ? 'Good' : 'Warning',
            },
          ],
        },
      ],
      actions: [
        {
          type: 'Action.OpenUrl',
          title: '📝 Open Timesheet',
          url: timesheetUrl,
        },
        {
          type: 'Action.Submit',
          title: '✅ Mark as Done',
          data: {
            action: 'markTimesheetComplete',
            userId: user.id,
            weekStart: summary.weekStartDate.toISOString(),
          },
        },
        {
          type: 'Action.Submit',
          title: '⏰ Remind Me Later',
          data: {
            action: 'snoozeReminder',
            userId: user.id,
            hours: 2,
          },
        },
      ],
    };

    return CardFactory.adaptiveCard(card);
  }

  /**
   * Create manager notification card
   */
  public createManagerNotificationCard(
    manager: User,
    incompleteUsers: User[],
    weekStartDate: Date
  ): Attachment {
    const userList = incompleteUsers.map((user) => ({
      type: 'TextBlock',
      text: `• ${user.displayName} (${user.email})`,
      wrap: true,
    }));

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
              text: '📊 Team Timesheet Status Report',
              weight: 'Bolder',
              size: 'Large',
              color: 'Accent',
            },
          ],
        },
        {
          type: 'Container',
          items: [
            {
              type: 'TextBlock',
              text: `Hi ${manager.displayName},`,
              weight: 'Bolder',
              size: 'Medium',
            },
            {
              type: 'TextBlock',
              text: `The following team members have not yet completed their timesheets for the week of ${this.formatDate(weekStartDate)}:`,
              wrap: true,
              spacing: 'Small',
            },
          ],
        },
        {
          type: 'Container',
          style: 'warning',
          items: [
            {
              type: 'TextBlock',
              text: `⚠️ ${incompleteUsers.length} team member(s) with incomplete timesheets:`,
              weight: 'Bolder',
              wrap: true,
            },
            ...userList,
          ],
        },
      ],
      actions: [
        {
          type: 'Action.Submit',
          title: '📧 Send Reminder to All',
          data: {
            action: 'sendTeamReminder',
            managerId: manager.id,
            userIds: incompleteUsers.map((u) => u.id),
          },
        },
        {
          type: 'Action.OpenUrl',
          title: '📊 View Team Dashboard',
          url: `${config.timesheetApiBaseUrl.replace('/api', '')}/manager/dashboard`,
        },
      ],
    };

    return CardFactory.adaptiveCard(card);
  }

  /**
   * Send proactive message to user
   */
  public async sendProactiveMessage(
    adapter: any,
    conversationReference: Partial<ConversationReference>,
    activity: Partial<Activity>
  ): Promise<void> {
    await adapter.continueConversationAsync(
      config.microsoftAppId,
      conversationReference,
      async (context: TurnContext) => {
        await context.sendActivity(activity);
      }
    );
  }

  /**
   * Send timesheet reminder to user
   */
  public async sendTimesheetReminder(
    adapter: any,
    user: User,
    summary: WeeklyTimesheetSummary,
    reminderType: ReminderType = ReminderType.WEEKLY_REMINDER
  ): Promise<boolean> {
    const conversationReference = this.getConversationReference(user.teamsUserId);

    if (!conversationReference) {
      console.log(`No conversation reference found for user: ${user.displayName}`);
      return false;
    }

    try {
      const card = this.createTimesheetReminderCard(user, summary, reminderType);
      const activity = MessageFactory.attachment(card);

      await this.sendProactiveMessage(adapter, conversationReference, activity);
      console.log(`Sent timesheet reminder to: ${user.displayName}`);
      return true;
    } catch (error) {
      console.error(`Error sending reminder to ${user.displayName}:`, error);
      return false;
    }
  }

  /**
   * Send manager notification
   */
  public async sendManagerNotification(
    adapter: any,
    manager: User,
    incompleteUsers: User[],
    weekStartDate: Date
  ): Promise<boolean> {
    const conversationReference = this.getConversationReference(manager.teamsUserId);

    if (!conversationReference) {
      console.log(`No conversation reference found for manager: ${manager.displayName}`);
      return false;
    }

    try {
      const card = this.createManagerNotificationCard(manager, incompleteUsers, weekStartDate);
      const activity = MessageFactory.attachment(card);

      await this.sendProactiveMessage(adapter, conversationReference, activity);
      console.log(`Sent manager notification to: ${manager.displayName}`);
      return true;
    } catch (error) {
      console.error(`Error sending manager notification:`, error);
      return false;
    }
  }

  /**
   * Create a simple text notification
   */
  public createTextNotification(message: string): Partial<Activity> {
    return MessageFactory.text(message);
  }

  /**
   * Get status color for adaptive card
   */
  private getStatusColor(status: WeeklyTimesheetStatus): string {
    switch (status) {
      case WeeklyTimesheetStatus.APPROVED:
      case WeeklyTimesheetStatus.SUBMITTED:
      case WeeklyTimesheetStatus.COMPLETE:
        return 'good';
      case WeeklyTimesheetStatus.IN_PROGRESS:
        return 'warning';
      case WeeklyTimesheetStatus.OVERDUE:
        return 'attention';
      default:
        return 'default';
    }
  }

  /**
   * Get human-readable status text
   */
  private getStatusText(status: WeeklyTimesheetStatus): string {
    switch (status) {
      case WeeklyTimesheetStatus.APPROVED:
        return '✅ Approved';
      case WeeklyTimesheetStatus.SUBMITTED:
        return '📨 Submitted';
      case WeeklyTimesheetStatus.COMPLETE:
        return '✅ Complete';
      case WeeklyTimesheetStatus.IN_PROGRESS:
        return '🔄 In Progress';
      case WeeklyTimesheetStatus.OVERDUE:
        return '❌ Overdue';
      case WeeklyTimesheetStatus.NOT_STARTED:
        return '⚠️ Not Started';
      default:
        return 'Unknown';
    }
  }

  /**
   * Get reminder message based on type
   */
  private getReminderMessage(type: ReminderType, summary: WeeklyTimesheetSummary): string {
    switch (type) {
      case ReminderType.WEEKLY_REMINDER:
        return "This is your weekly reminder to complete and submit your timesheet.";
      case ReminderType.DEADLINE_APPROACHING:
        return `⚠️ Your timesheet deadline is approaching! Only ${summary.daysRemaining} day(s) remaining.`;
      case ReminderType.OVERDUE:
        return "🚨 Your timesheet is overdue! Please complete and submit it as soon as possible.";
      default:
        return "Please remember to complete your timesheet.";
    }
  }

  /**
   * Format date for display
   */
  private formatDate(date: Date): string {
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }
}

export default NotificationService.getInstance();
