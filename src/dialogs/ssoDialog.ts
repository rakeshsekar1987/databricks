import {
  ComponentDialog,
  DialogContext,
  DialogTurnResult,
  OAuthPrompt,
  OAuthPromptSettings,
  WaterfallDialog,
  WaterfallStepContext,
} from 'botbuilder-dialogs';
import { TokenResponse, TurnContext } from 'botbuilder';
import authService from '../services/authService';
import graphService from '../services/graphService';
import config from '../config';

const OAUTH_PROMPT = 'OAuthPrompt';
const SSO_DIALOG = 'SsoDialog';
const WATERFALL_DIALOG = 'WaterfallDialog';

/**
 * SSO Dialog for Teams authentication
 * Handles the OAuth flow for Microsoft Teams Single Sign-On
 */
export class SsoDialog extends ComponentDialog {
  constructor() {
    super(SSO_DIALOG);

    // OAuth prompt settings for Teams SSO
    const oauthPromptSettings: OAuthPromptSettings = {
      connectionName: process.env.OAUTH_CONNECTION_NAME || 'TeamsSSO',
      text: 'Please sign in to access your timesheet.',
      title: 'Sign In',
      timeout: 300000, // 5 minutes
      endOnInvalidMessage: true,
    };

    this.addDialog(new OAuthPrompt(OAUTH_PROMPT, oauthPromptSettings));

    this.addDialog(
      new WaterfallDialog(WATERFALL_DIALOG, [
        this.promptStep.bind(this),
        this.loginStep.bind(this),
        this.fetchUserProfileStep.bind(this),
      ])
    );

    this.initialDialogId = WATERFALL_DIALOG;
  }

  /**
   * Prompt the user to sign in
   */
  private async promptStep(stepContext: WaterfallStepContext): Promise<DialogTurnResult> {
    return await stepContext.beginDialog(OAUTH_PROMPT);
  }

  /**
   * Process the login result
   */
  private async loginStep(stepContext: WaterfallStepContext): Promise<DialogTurnResult> {
    const tokenResponse = stepContext.result as TokenResponse;

    if (tokenResponse && tokenResponse.token) {
      // Store the token for later use
      (stepContext.values as Record<string, unknown>)['token'] = tokenResponse.token;
      
      await stepContext.context.sendActivity('✅ Sign-in successful!');
      return await stepContext.next(tokenResponse);
    }

    await stepContext.context.sendActivity(
      '❌ Sign-in was unsuccessful. Please try again.'
    );
    return await stepContext.endDialog();
  }

  /**
   * Fetch user profile after successful authentication
   */
  private async fetchUserProfileStep(stepContext: WaterfallStepContext): Promise<DialogTurnResult> {
    const tokenResponse = stepContext.result as TokenResponse;

    if (tokenResponse && tokenResponse.token) {
      try {
        // Exchange the token for Graph API access
        const authResult = await authService.exchangeSsoToken(
          tokenResponse.token,
          config.graphApiScopes
        );

        if (authResult && authResult.accessToken) {
          // Get user profile from Graph API
          const userProfile = await graphService.getUserProfile(authResult.accessToken);

          if (userProfile) {
            await stepContext.context.sendActivity(
              `Welcome, ${userProfile.displayName}! Your email is ${userProfile.email}.`
            );

            // Try to get manager info
            const manager = await graphService.getUserManager(authResult.accessToken);
            if (manager) {
              await stepContext.context.sendActivity(
                `Your manager is ${manager.displayName}.`
              );
            }

            return await stepContext.endDialog({
              token: authResult.accessToken,
              user: userProfile,
              manager: manager,
            });
          }
        }

        await stepContext.context.sendActivity(
          'Could not retrieve your profile. Please try again.'
        );
      } catch (error) {
        console.error('Error fetching user profile:', error);
        await stepContext.context.sendActivity(
          'An error occurred while fetching your profile.'
        );
      }
    }

    return await stepContext.endDialog();
  }

  /**
   * Called when the dialog is started and not resumed
   */
  async run(context: TurnContext, accessor: any): Promise<void> {
    const dialogSet = new (await import('botbuilder-dialogs')).DialogSet(accessor);
    dialogSet.add(this);

    const dialogContext = await dialogSet.createContext(context);
    const results = await dialogContext.continueDialog();

    if (results.status === (await import('botbuilder-dialogs')).DialogTurnStatus.empty) {
      await dialogContext.beginDialog(this.id);
    }
  }
}

export default SsoDialog;
