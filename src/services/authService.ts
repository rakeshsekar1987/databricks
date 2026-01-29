import { ConfidentialClientApplication, Configuration, AuthenticationResult } from '@azure/msal-node';
import { Client } from '@microsoft/microsoft-graph-client';
import 'isomorphic-fetch';
import config from '../config';

/**
 * Authentication Service for Teams SSO and Graph API integration
 */
export class AuthService {
  private msalClient: ConfidentialClientApplication;
  private static instance: AuthService;

  private constructor() {
    const msalConfig: Configuration = {
      auth: {
        clientId: config.azureAdClientId,
        clientSecret: config.azureAdClientSecret,
        authority: `https://login.microsoftonline.com/${config.azureAdTenantId}`,
      },
      system: {
        loggerOptions: {
          loggerCallback: (level, message, containsPii) => {
            if (!containsPii) {
              console.log(`MSAL: ${message}`);
            }
          },
          piiLoggingEnabled: false,
        },
      },
    };

    this.msalClient = new ConfidentialClientApplication(msalConfig);
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  /**
   * Exchange SSO token from Teams for an access token
   * This is the On-Behalf-Of (OBO) flow
   */
  public async exchangeSsoToken(ssoToken: string, scopes: string[]): Promise<AuthenticationResult | null> {
    try {
      const oboRequest = {
        oboAssertion: ssoToken,
        scopes: scopes,
      };

      const response = await this.msalClient.acquireTokenOnBehalfOf(oboRequest);
      return response;
    } catch (error) {
      console.error('Error exchanging SSO token:', error);
      return null;
    }
  }

  /**
   * Get access token for application (client credentials flow)
   * Used for background operations like scheduled reminders
   */
  public async getAppAccessToken(scopes: string[] = ['https://graph.microsoft.com/.default']): Promise<string | null> {
    try {
      const clientCredentialRequest = {
        scopes: scopes,
      };

      const response = await this.msalClient.acquireTokenByClientCredential(clientCredentialRequest);
      return response?.accessToken || null;
    } catch (error) {
      console.error('Error getting app access token:', error);
      return null;
    }
  }

  /**
   * Create a Microsoft Graph client with user token
   */
  public createGraphClientWithToken(accessToken: string): Client {
    return Client.init({
      authProvider: (done) => {
        done(null, accessToken);
      },
    });
  }

  /**
   * Create a Microsoft Graph client with app token
   */
  public async createAppGraphClient(): Promise<Client | null> {
    const accessToken = await this.getAppAccessToken();
    if (!accessToken) {
      return null;
    }

    return this.createGraphClientWithToken(accessToken);
  }

  /**
   * Validate the SSO token from Teams
   */
  public validateSsoToken(token: string): boolean {
    try {
      // Basic validation - in production, you should verify the token signature
      const parts = token.split('.');
      if (parts.length !== 3) {
        return false;
      }

      const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
      
      // Check token expiration
      if (payload.exp && Date.now() >= payload.exp * 1000) {
        console.log('Token has expired');
        return false;
      }

      // Verify audience
      if (payload.aud && payload.aud !== config.azureAdClientId) {
        console.log('Invalid audience');
        return false;
      }

      return true;
    } catch (error) {
      console.error('Error validating SSO token:', error);
      return false;
    }
  }

  /**
   * Get user info from SSO token
   */
  public getUserInfoFromToken(token: string): { oid: string; name: string; email: string } | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        return null;
      }

      const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
      
      return {
        oid: payload.oid,
        name: payload.name || payload.preferred_username,
        email: payload.email || payload.preferred_username || payload.upn,
      };
    } catch (error) {
      console.error('Error parsing token:', error);
      return null;
    }
  }
}

export default AuthService.getInstance();
