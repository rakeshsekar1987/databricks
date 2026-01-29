/**
 * User model for timesheet reminder system
 */
export interface User {
  id: string;
  displayName: string;
  email: string;
  teamsUserId: string;
  conversationReference?: ConversationReferenceData;
  managerId?: string;
  managerEmail?: string;
  managerDisplayName?: string;
  department?: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Conversation reference for proactive messaging
 */
export interface ConversationReferenceData {
  activityId?: string;
  user?: {
    id: string;
    name?: string;
    aadObjectId?: string;
  };
  bot?: {
    id: string;
    name?: string;
  };
  conversation?: {
    id: string;
    conversationType?: string;
    tenantId?: string;
    isGroup?: boolean;
  };
  channelId?: string;
  locale?: string;
  serviceUrl?: string;
}

/**
 * User preferences for reminders
 */
export interface UserPreferences {
  userId: string;
  reminderEnabled: boolean;
  reminderDays: number[]; // 0 = Sunday, 1 = Monday, etc.
  reminderTime: string; // HH:mm format
  includeManager: boolean;
  timezone: string;
}

/**
 * Manager information
 */
export interface Manager {
  id: string;
  displayName: string;
  email: string;
  teamsUserId?: string;
  directReports: string[]; // Array of user IDs
}

/**
 * Create a new user with default values
 */
export function createDefaultUser(partial: Partial<User>): User {
  return {
    id: partial.id || '',
    displayName: partial.displayName || '',
    email: partial.email || '',
    teamsUserId: partial.teamsUserId || '',
    conversationReference: partial.conversationReference,
    managerId: partial.managerId,
    managerEmail: partial.managerEmail,
    managerDisplayName: partial.managerDisplayName,
    department: partial.department,
    isActive: partial.isActive ?? true,
    createdAt: partial.createdAt || new Date(),
    updatedAt: partial.updatedAt || new Date(),
  };
}

/**
 * Create default user preferences
 */
export function createDefaultPreferences(userId: string): UserPreferences {
  return {
    userId,
    reminderEnabled: true,
    reminderDays: [5], // Friday by default
    reminderTime: '15:00',
    includeManager: true,
    timezone: 'UTC',
  };
}
