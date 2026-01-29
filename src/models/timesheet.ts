/**
 * Timesheet entry model
 */
export interface TimesheetEntry {
  id: string;
  userId: string;
  date: Date;
  hours: number;
  projectCode?: string;
  projectName?: string;
  taskDescription?: string;
  status: TimesheetStatus;
  submittedAt?: Date;
  approvedAt?: Date;
  approvedBy?: string;
}

/**
 * Timesheet status enumeration
 */
export enum TimesheetStatus {
  DRAFT = 'DRAFT',
  SUBMITTED = 'SUBMITTED',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  PENDING = 'PENDING',
}

/**
 * Weekly timesheet summary
 */
export interface WeeklyTimesheetSummary {
  userId: string;
  weekStartDate: Date;
  weekEndDate: Date;
  totalHours: number;
  expectedHours: number;
  entries: TimesheetEntry[];
  status: WeeklyTimesheetStatus;
  isComplete: boolean;
  submissionDeadline: Date;
  daysRemaining: number;
}

/**
 * Weekly timesheet status
 */
export enum WeeklyTimesheetStatus {
  NOT_STARTED = 'NOT_STARTED',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETE = 'COMPLETE',
  OVERDUE = 'OVERDUE',
  SUBMITTED = 'SUBMITTED',
  APPROVED = 'APPROVED',
}

/**
 * Timesheet reminder data
 */
export interface TimesheetReminderData {
  user: {
    id: string;
    displayName: string;
    email: string;
  };
  weekSummary: WeeklyTimesheetSummary;
  timesheetUrl: string;
  reminderType: ReminderType;
  sentAt: Date;
  manager?: {
    id: string;
    displayName: string;
    email: string;
  };
}

/**
 * Types of reminders
 */
export enum ReminderType {
  WEEKLY_REMINDER = 'WEEKLY_REMINDER',
  DEADLINE_APPROACHING = 'DEADLINE_APPROACHING',
  OVERDUE = 'OVERDUE',
  MANAGER_NOTIFICATION = 'MANAGER_NOTIFICATION',
}

/**
 * Calculate the current week's date range
 */
export function getCurrentWeekDateRange(): { start: Date; end: Date } {
  const now = new Date();
  const dayOfWeek = now.getDay();
  
  // Calculate start of week (Monday)
  const start = new Date(now);
  start.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  start.setHours(0, 0, 0, 0);
  
  // Calculate end of week (Sunday)
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  end.setHours(23, 59, 59, 999);
  
  return { start, end };
}

/**
 * Check if timesheet is overdue
 */
export function isTimesheetOverdue(deadline: Date): boolean {
  return new Date() > deadline;
}

/**
 * Calculate days remaining until deadline
 */
export function getDaysUntilDeadline(deadline: Date): number {
  const now = new Date();
  const diffTime = deadline.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
}
