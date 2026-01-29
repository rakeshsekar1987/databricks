// Azure Bicep template for Teams Timesheet Reminder Bot deployment
// This template creates the necessary Azure resources

@description('The name of the bot service')
param botServiceName string = 'timesheet-reminder-bot'

@description('The location for all resources')
param location string = resourceGroup().location

@description('The pricing tier of the App Service plan')
@allowed([
  'F1'
  'B1'
  'B2'
  'S1'
  'S2'
  'P1v2'
  'P2v2'
])
param appServicePlanSku string = 'B1'

@description('Microsoft App ID for the bot')
param microsoftAppId string

@description('Microsoft App Password for the bot')
@secure()
param microsoftAppPassword string

@description('Azure AD Tenant ID')
param azureAdTenantId string

@description('Azure AD Client ID for SSO')
param azureAdClientId string

@description('Azure AD Client Secret for SSO')
@secure()
param azureAdClientSecret string

@description('Timesheet API Base URL')
param timesheetApiBaseUrl string = 'https://your-timesheet-app.com/api'

@description('Timesheet API Key')
@secure()
param timesheetApiKey string = ''

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: '${botServiceName}-plan'
  location: location
  sku: {
    name: appServicePlanSku
    capacity: 1
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// App Service (Web App)
resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: botServiceName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'NODE|18-lts'
      alwaysOn: true
      appSettings: [
        {
          name: 'MICROSOFT_APP_ID'
          value: microsoftAppId
        }
        {
          name: 'MICROSOFT_APP_PASSWORD'
          value: microsoftAppPassword
        }
        {
          name: 'MICROSOFT_APP_TENANT_ID'
          value: azureAdTenantId
        }
        {
          name: 'AZURE_AD_CLIENT_ID'
          value: azureAdClientId
        }
        {
          name: 'AZURE_AD_CLIENT_SECRET'
          value: azureAdClientSecret
        }
        {
          name: 'AZURE_AD_TENANT_ID'
          value: azureAdTenantId
        }
        {
          name: 'TIMESHEET_API_BASE_URL'
          value: timesheetApiBaseUrl
        }
        {
          name: 'TIMESHEET_API_KEY'
          value: timesheetApiKey
        }
        {
          name: 'BOT_DOMAIN'
          value: 'https://${botServiceName}.azurewebsites.net'
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '18-lts'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
    }
    httpsOnly: true
  }
}

// Azure Bot Service
resource botService 'Microsoft.BotService/botServices@2022-09-15' = {
  name: botServiceName
  location: 'global'
  kind: 'azurebot'
  sku: {
    name: 'S1'
  }
  properties: {
    displayName: 'Timesheet Reminder Bot'
    description: 'Microsoft Teams bot for timesheet reminders with SSO authentication'
    endpoint: 'https://${webApp.properties.defaultHostName}/api/messages'
    msaAppId: microsoftAppId
    msaAppTenantId: azureAdTenantId
    msaAppType: 'MultiTenant'
  }
}

// Bot Service Teams Channel
resource teamsChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: botService
  name: 'MsTeamsChannel'
  location: 'global'
  properties: {
    channelName: 'MsTeamsChannel'
    properties: {
      enableCalling: false
      isEnabled: true
    }
  }
}

// Outputs
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output botEndpoint string = 'https://${webApp.properties.defaultHostName}/api/messages'
output botServiceId string = botService.id
