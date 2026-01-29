import { Client } from '@microsoft/microsoft-graph-client';
import authService from './authService';
import { User, Manager } from '../models/user';

/**
 * Microsoft Graph Service for user and organization data
 */
export class GraphService {
  private static instance: GraphService;

  private constructor() {}

  public static getInstance(): GraphService {
    if (!GraphService.instance) {
      GraphService.instance = new GraphService();
    }
    return GraphService.instance;
  }

  /**
   * Get current user's profile using SSO token
   */
  public async getUserProfile(accessToken: string): Promise<User | null> {
    try {
      const client = authService.createGraphClientWithToken(accessToken);
      
      const graphUser = await client.api('/me')
        .select('id,displayName,mail,userPrincipalName,department')
        .get();

      return {
        id: graphUser.id,
        displayName: graphUser.displayName,
        email: graphUser.mail || graphUser.userPrincipalName,
        teamsUserId: graphUser.id,
        department: graphUser.department,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      };
    } catch (error) {
      console.error('Error getting user profile:', error);
      return null;
    }
  }

  /**
   * Get user's manager information
   */
  public async getUserManager(accessToken: string): Promise<Manager | null> {
    try {
      const client = authService.createGraphClientWithToken(accessToken);
      
      const manager = await client.api('/me/manager')
        .select('id,displayName,mail,userPrincipalName')
        .get();

      return {
        id: manager.id,
        displayName: manager.displayName,
        email: manager.mail || manager.userPrincipalName,
        directReports: [],
      };
    } catch (error) {
      console.error('Error getting manager:', error);
      return null;
    }
  }

  /**
   * Get user by ID using app permissions
   */
  public async getUserById(userId: string): Promise<User | null> {
    try {
      const client = await authService.createAppGraphClient();
      if (!client) {
        throw new Error('Failed to create Graph client');
      }

      const graphUser = await client.api(`/users/${userId}`)
        .select('id,displayName,mail,userPrincipalName,department')
        .get();

      return {
        id: graphUser.id,
        displayName: graphUser.displayName,
        email: graphUser.mail || graphUser.userPrincipalName,
        teamsUserId: graphUser.id,
        department: graphUser.department,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      };
    } catch (error) {
      console.error('Error getting user by ID:', error);
      return null;
    }
  }

  /**
   * Get manager's direct reports
   */
  public async getDirectReports(managerId: string): Promise<User[]> {
    try {
      const client = await authService.createAppGraphClient();
      if (!client) {
        throw new Error('Failed to create Graph client');
      }

      const response = await client.api(`/users/${managerId}/directReports`)
        .select('id,displayName,mail,userPrincipalName,department')
        .get();

      return response.value.map((user: any) => ({
        id: user.id,
        displayName: user.displayName,
        email: user.mail || user.userPrincipalName,
        teamsUserId: user.id,
        department: user.department,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      }));
    } catch (error) {
      console.error('Error getting direct reports:', error);
      return [];
    }
  }

  /**
   * Send an email notification via Graph API
   */
  public async sendEmailNotification(
    accessToken: string,
    to: string[],
    subject: string,
    body: string,
    cc?: string[]
  ): Promise<boolean> {
    try {
      const client = authService.createGraphClientWithToken(accessToken);

      const message = {
        subject: subject,
        body: {
          contentType: 'HTML',
          content: body,
        },
        toRecipients: to.map((email) => ({
          emailAddress: { address: email },
        })),
        ccRecipients: cc?.map((email) => ({
          emailAddress: { address: email },
        })) || [],
      };

      await client.api('/me/sendMail').post({ message });
      return true;
    } catch (error) {
      console.error('Error sending email:', error);
      return false;
    }
  }

  /**
   * Get user's Teams chat ID for proactive messaging
   */
  public async getTeamsChatId(userId: string): Promise<string | null> {
    try {
      const client = await authService.createAppGraphClient();
      if (!client) {
        throw new Error('Failed to create Graph client');
      }

      // Get the chat with the user
      const response = await client.api(`/users/${userId}/chats`)
        .filter("chatType eq 'oneOnOne'")
        .select('id')
        .top(1)
        .get();

      if (response.value && response.value.length > 0) {
        return response.value[0].id;
      }

      return null;
    } catch (error) {
      console.error('Error getting Teams chat ID:', error);
      return null;
    }
  }

  /**
   * Send a Teams chat message to a user
   */
  public async sendTeamsMessage(chatId: string, message: string): Promise<boolean> {
    try {
      const client = await authService.createAppGraphClient();
      if (!client) {
        throw new Error('Failed to create Graph client');
      }

      await client.api(`/chats/${chatId}/messages`).post({
        body: {
          contentType: 'html',
          content: message,
        },
      });

      return true;
    } catch (error) {
      console.error('Error sending Teams message:', error);
      return false;
    }
  }
}

export default GraphService.getInstance();
