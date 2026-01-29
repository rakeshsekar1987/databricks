import cron from 'node-cron';
import { BotFrameworkAdapter } from 'botbuilder';
import config from '../config';
import notificationService from './notificationService';
import timesheetService from './timesheetService';
import graphService from './graphService';
import { User } from '../models/user';
import { ReminderType, getCurrentWeekDateRange } from '../models/timesheet';

/**
 * Reminder Scheduler Service
 * Handles scheduled timesheet reminders using cron jobs
 */
export class ReminderScheduler {
  private static instance: ReminderScheduler;
  private adapter: BotFrameworkAdapter | null = null;
  private scheduledJobs: Map<string, cron.ScheduledTask> = new Map();
  private registeredUsers: Map<string, User> = new Map();

  private constructor() {}

  public static getInstance(): ReminderScheduler {
    if (!ReminderScheduler.instance) {
      ReminderScheduler.instance = new ReminderScheduler();
    }
    return ReminderScheduler.instance;
  }

  /**
   * Initialize the scheduler with the bot adapter
   */
  public initialize(adapter: BotFrameworkAdapter): void {
    this.adapter = adapter;
    console.log('Reminder scheduler initialized');
  }

  /**
   * Register a user for reminders
   */
  public registerUser(user: User): void {
    this.registeredUsers.set(user.teamsUserId, user);
    console.log(`User registered for reminders: ${user.displayName}`);
  }

  /**
   * Unregister a user from reminders
   */
  public unregisterUser(userId: string): void {
    this.registeredUsers.delete(userId);
    console.log(`User unregistered from reminders: ${userId}`);
  }

  /**
   * Get all registered users
   */
  public getRegisteredUsers(): User[] {
    return Array.from(this.registeredUsers.values());
  }

  /**
   * Start the default reminder schedule
   */
  public startDefaultSchedule(): void {
    const cronSchedule = config.reminderCronSchedule;
    console.log(`Starting reminder scheduler with cron schedule: ${cronSchedule}`);

    // Validate cron expression
    if (!cron.validate(cronSchedule)) {
      console.error(`Invalid cron expression: ${cronSchedule}`);
      return;
    }

    // Main weekly reminder job
    const weeklyJob = cron.schedule(cronSchedule, async () => {
      console.log('Running weekly timesheet reminder job...');
      await this.sendWeeklyReminders();
    });

    this.scheduledJobs.set('weekly-reminder', weeklyJob);

    // Daily deadline check (runs every weekday at 9 AM)
    const deadlineJob = cron.schedule('0 9 * * 1-5', async () => {
      console.log('Running deadline check job...');
      await this.sendDeadlineReminders();
    });

    this.scheduledJobs.set('deadline-check', deadlineJob);

    // Manager notification job (runs every Friday at 4 PM)
    if (config.includeManagerInReminder) {
      const managerJob = cron.schedule('0 16 * * 5', async () => {
        console.log('Running manager notification job...');
        await this.sendManagerNotifications();
      });

      this.scheduledJobs.set('manager-notification', managerJob);
    }

    console.log('All scheduled jobs started successfully');
  }

  /**
   * Stop all scheduled jobs
   */
  public stopAllSchedules(): void {
    this.scheduledJobs.forEach((job, name) => {
      job.stop();
      console.log(`Stopped scheduled job: ${name}`);
    });
    this.scheduledJobs.clear();
  }

  /**
   * Send weekly reminders to all registered users
   */
  public async sendWeeklyReminders(): Promise<void> {
    if (!this.adapter) {
      console.error('Bot adapter not initialized');
      return;
    }

    const users = this.getRegisteredUsers();
    console.log(`Sending weekly reminders to ${users.length} users`);

    for (const user of users) {
      try {
        // Get timesheet summary for the user
        const sessionToken = await timesheetService.authenticateWithSsoToken('', user.email);
        if (!sessionToken) {
          console.log(`Could not authenticate user: ${user.displayName}`);
          continue;
        }

        const summary = await timesheetService.getWeeklyTimesheetSummary(sessionToken, user.id);

        // Only send reminder if timesheet is not complete
        if (!summary.isComplete) {
          await notificationService.sendTimesheetReminder(
            this.adapter,
            user,
            summary,
            ReminderType.WEEKLY_REMINDER
          );
        } else {
          console.log(`Skipping reminder for ${user.displayName} - timesheet complete`);
        }
      } catch (error) {
        console.error(`Error sending reminder to ${user.displayName}:`, error);
      }
    }
  }

  /**
   * Send deadline approaching reminders
   */
  public async sendDeadlineReminders(): Promise<void> {
    if (!this.adapter) {
      console.error('Bot adapter not initialized');
      return;
    }

    const users = this.getRegisteredUsers();
    const { end } = getCurrentWeekDateRange();
    
    // Calculate deadline (Friday 5 PM)
    const deadline = new Date(end);
    deadline.setDate(deadline.getDate() - 2); // Move to Friday
    deadline.setHours(17, 0, 0, 0);

    const now = new Date();
    const hoursUntilDeadline = (deadline.getTime() - now.getTime()) / (1000 * 60 * 60);

    // Only send if deadline is within 24 hours
    if (hoursUntilDeadline > 24 || hoursUntilDeadline < 0) {
      return;
    }

    console.log(`Deadline approaching! ${hoursUntilDeadline.toFixed(1)} hours remaining`);

    for (const user of users) {
      try {
        const sessionToken = await timesheetService.authenticateWithSsoToken('', user.email);
        if (!sessionToken) continue;

        const summary = await timesheetService.getWeeklyTimesheetSummary(sessionToken, user.id);

        if (!summary.isComplete) {
          await notificationService.sendTimesheetReminder(
            this.adapter,
            user,
            summary,
            ReminderType.DEADLINE_APPROACHING
          );
        }
      } catch (error) {
        console.error(`Error sending deadline reminder to ${user.displayName}:`, error);
      }
    }
  }

  /**
   * Send notifications to managers about team's incomplete timesheets
   */
  public async sendManagerNotifications(): Promise<void> {
    if (!this.adapter) {
      console.error('Bot adapter not initialized');
      return;
    }

    const users = this.getRegisteredUsers();
    const { start } = getCurrentWeekDateRange();

    // Group users by manager
    const managerGroups = new Map<string, User[]>();

    for (const user of users) {
      try {
        const sessionToken = await timesheetService.authenticateWithSsoToken('', user.email);
        if (!sessionToken) continue;

        const summary = await timesheetService.getWeeklyTimesheetSummary(sessionToken, user.id);

        if (!summary.isComplete && user.managerId) {
          const existing = managerGroups.get(user.managerId) || [];
          existing.push(user);
          managerGroups.set(user.managerId, existing);
        }
      } catch (error) {
        console.error(`Error checking timesheet for ${user.displayName}:`, error);
      }
    }

    // Send notifications to each manager
    for (const [managerId, incompleteUsers] of managerGroups) {
      try {
        const manager = await graphService.getUserById(managerId);
        if (manager) {
          await notificationService.sendManagerNotification(
            this.adapter,
            manager,
            incompleteUsers,
            start
          );
        }
      } catch (error) {
        console.error(`Error sending manager notification for ${managerId}:`, error);
      }
    }
  }

  /**
   * Schedule a one-time reminder for a specific user
   */
  public scheduleOneTimeReminder(
    userId: string,
    delayMinutes: number,
    reminderType: ReminderType = ReminderType.WEEKLY_REMINDER
  ): void {
    const user = this.registeredUsers.get(userId);
    if (!user || !this.adapter) {
      console.log('Cannot schedule one-time reminder: user not found or adapter not initialized');
      return;
    }

    const jobId = `onetime-${userId}-${Date.now()}`;

    setTimeout(async () => {
      try {
        const sessionToken = await timesheetService.authenticateWithSsoToken('', user.email);
        if (sessionToken) {
          const summary = await timesheetService.getWeeklyTimesheetSummary(sessionToken, user.id);
          await notificationService.sendTimesheetReminder(this.adapter!, user, summary, reminderType);
        }
      } catch (error) {
        console.error(`Error sending one-time reminder:`, error);
      }
    }, delayMinutes * 60 * 1000);

    console.log(`Scheduled one-time reminder for ${user.displayName} in ${delayMinutes} minutes`);
  }

  /**
   * Manually trigger reminders (for testing)
   */
  public async triggerManualReminder(userId?: string): Promise<void> {
    if (userId) {
      const user = this.registeredUsers.get(userId);
      if (user && this.adapter) {
        const sessionToken = await timesheetService.authenticateWithSsoToken('', user.email);
        if (sessionToken) {
          const summary = await timesheetService.getWeeklyTimesheetSummary(sessionToken, user.id);
          await notificationService.sendTimesheetReminder(
            this.adapter,
            user,
            summary,
            ReminderType.WEEKLY_REMINDER
          );
        }
      }
    } else {
      await this.sendWeeklyReminders();
    }
  }
}

export default ReminderScheduler.getInstance();
