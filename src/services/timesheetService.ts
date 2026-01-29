import axios, { AxiosInstance, AxiosError } from 'axios';
import config from '../config';
import {
  TimesheetEntry,
  TimesheetStatus,
  WeeklyTimesheetSummary,
  WeeklyTimesheetStatus,
  getCurrentWeekDateRange,
  getDaysUntilDeadline,
} from '../models/timesheet';

/**
 * Timesheet API Service
 * Handles communication with the timesheet application's REST API
 */
export class TimesheetService {
  private static instance: TimesheetService;
  private httpClient: AxiosInstance;

  private constructor() {
    this.httpClient = axios.create({
      baseURL: config.timesheetApiBaseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.timesheetApiKey,
      },
    });

    // Add request interceptor for logging
    this.httpClient.interceptors.request.use(
      (requestConfig) => {
        console.log(`Timesheet API Request: ${requestConfig.method?.toUpperCase()} ${requestConfig.url}`);
        return requestConfig;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.httpClient.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('Timesheet API Error:', error.message);
        return Promise.reject(error);
      }
    );
  }

  public static getInstance(): TimesheetService {
    if (!TimesheetService.instance) {
      TimesheetService.instance = new TimesheetService();
    }
    return TimesheetService.instance;
  }

  /**
   * Authenticate user with SSO token and get API session
   * Uses the Teams SSO token to authenticate with the timesheet system
   */
  public async authenticateWithSsoToken(ssoToken: string, userEmail: string): Promise<string | null> {
    try {
      const response = await this.httpClient.post('/auth/sso', {
        ssoToken: ssoToken,
        email: userEmail,
        provider: 'microsoft',
      });

      if (response.data?.sessionToken) {
        return response.data.sessionToken;
      }
      return null;
    } catch (error) {
      console.error('Error authenticating with SSO:', error);
      // For demo purposes, return a mock session token
      return this.mockAuthenticate(userEmail);
    }
  }

  /**
   * Mock authentication for development/demo
   */
  private mockAuthenticate(userEmail: string): string {
    console.log(`Mock authentication for: ${userEmail}`);
    return `mock-session-${Buffer.from(userEmail).toString('base64')}`;
  }

  /**
   * Get user's timesheet entries for a specific date range
   */
  public async getTimesheetEntries(
    sessionToken: string,
    userId: string,
    startDate: Date,
    endDate: Date
  ): Promise<TimesheetEntry[]> {
    try {
      const response = await this.httpClient.get('/timesheets', {
        headers: { Authorization: `Bearer ${sessionToken}` },
        params: {
          userId,
          startDate: startDate.toISOString().split('T')[0],
          endDate: endDate.toISOString().split('T')[0],
        },
      });

      return response.data?.entries || [];
    } catch (error) {
      console.error('Error fetching timesheet entries:', error);
      // Return mock data for development
      return this.getMockTimesheetEntries(userId, startDate, endDate);
    }
  }

  /**
   * Get weekly timesheet summary for a user
   */
  public async getWeeklyTimesheetSummary(
    sessionToken: string,
    userId: string,
    weekStartDate?: Date
  ): Promise<WeeklyTimesheetSummary> {
    try {
      const { start, end } = weekStartDate
        ? { start: weekStartDate, end: new Date(weekStartDate.getTime() + 6 * 24 * 60 * 60 * 1000) }
        : getCurrentWeekDateRange();

      const response = await this.httpClient.get('/timesheets/weekly-summary', {
        headers: { Authorization: `Bearer ${sessionToken}` },
        params: {
          userId,
          weekStartDate: start.toISOString().split('T')[0],
        },
      });

      if (response.data) {
        return response.data;
      }

      throw new Error('No data received');
    } catch (error) {
      console.error('Error fetching weekly summary:', error);
      // Return mock summary for development
      return this.getMockWeeklySummary(userId);
    }
  }

  /**
   * Check if user has submitted timesheet for the current week
   */
  public async isTimesheetSubmitted(sessionToken: string, userId: string): Promise<boolean> {
    try {
      const summary = await this.getWeeklyTimesheetSummary(sessionToken, userId);
      return (
        summary.status === WeeklyTimesheetStatus.SUBMITTED ||
        summary.status === WeeklyTimesheetStatus.APPROVED
      );
    } catch (error) {
      console.error('Error checking timesheet status:', error);
      return false;
    }
  }

  /**
   * Get timesheet URL for the user
   */
  public getTimesheetUrl(userId?: string): string {
    const baseUrl = config.timesheetApiBaseUrl.replace('/api', '');
    if (userId) {
      return `${baseUrl}/timesheet?user=${userId}`;
    }
    return `${baseUrl}/timesheet`;
  }

  /**
   * Get users with incomplete timesheets
   */
  public async getUsersWithIncompleteTimesheets(sessionToken: string): Promise<string[]> {
    try {
      const response = await this.httpClient.get('/timesheets/incomplete', {
        headers: { Authorization: `Bearer ${sessionToken}` },
      });

      return response.data?.userIds || [];
    } catch (error) {
      console.error('Error fetching incomplete timesheets:', error);
      return [];
    }
  }

  /**
   * Submit timesheet entry
   */
  public async submitTimesheet(
    sessionToken: string,
    userId: string,
    weekStartDate: Date
  ): Promise<boolean> {
    try {
      const response = await this.httpClient.post(
        '/timesheets/submit',
        {
          userId,
          weekStartDate: weekStartDate.toISOString().split('T')[0],
        },
        {
          headers: { Authorization: `Bearer ${sessionToken}` },
        }
      );

      return response.status === 200;
    } catch (error) {
      console.error('Error submitting timesheet:', error);
      return false;
    }
  }

  /**
   * Generate mock timesheet entries for development/demo
   */
  private getMockTimesheetEntries(userId: string, startDate: Date, endDate: Date): TimesheetEntry[] {
    const entries: TimesheetEntry[] = [];
    const currentDate = new Date(startDate);

    while (currentDate <= endDate) {
      // Skip weekends
      if (currentDate.getDay() !== 0 && currentDate.getDay() !== 6) {
        // Randomly generate entries (some days may be incomplete)
        const shouldHaveEntry = Math.random() > 0.3;

        if (shouldHaveEntry) {
          entries.push({
            id: `entry-${currentDate.toISOString().split('T')[0]}`,
            userId,
            date: new Date(currentDate),
            hours: 8,
            projectCode: 'PROJ-001',
            projectName: 'Main Project',
            taskDescription: 'Development work',
            status: TimesheetStatus.DRAFT,
          });
        }
      }
      currentDate.setDate(currentDate.getDate() + 1);
    }

    return entries;
  }

  /**
   * Generate mock weekly summary for development/demo
   */
  private getMockWeeklySummary(userId: string): WeeklyTimesheetSummary {
    const { start, end } = getCurrentWeekDateRange();
    const entries = this.getMockTimesheetEntries(userId, start, end);
    const totalHours = entries.reduce((sum, entry) => sum + entry.hours, 0);
    const expectedHours = 40;

    // Set deadline to Friday 5 PM
    const deadline = new Date(end);
    deadline.setDate(start.getDate() + 4); // Friday
    deadline.setHours(17, 0, 0, 0);

    const isComplete = totalHours >= expectedHours;
    let status: WeeklyTimesheetStatus;

    if (isComplete) {
      status = WeeklyTimesheetStatus.COMPLETE;
    } else if (totalHours > 0) {
      status = WeeklyTimesheetStatus.IN_PROGRESS;
    } else {
      status = WeeklyTimesheetStatus.NOT_STARTED;
    }

    return {
      userId,
      weekStartDate: start,
      weekEndDate: end,
      totalHours,
      expectedHours,
      entries,
      status,
      isComplete,
      submissionDeadline: deadline,
      daysRemaining: getDaysUntilDeadline(deadline),
    };
  }
}

export default TimesheetService.getInstance();
