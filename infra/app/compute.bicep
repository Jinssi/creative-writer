metadata description = 'Compute + monitoring for Contoso Creative Writer, reusing an existing Foundry.'

param location string = resourceGroup().location
param tags object = {}
param resourceToken string

// Shared, cross-RG user-assigned managed identity (Foundry roles already granted).
param managedIdentityId string
param managedIdentityClientId string
param managedIdentityPrincipalId string

// Existing Foundry / AI resource references (reused, not created).
param aiProjectEndpoint string
param openAiEndpoint string
param openAiName string
param openAiApiVersion string
param chatDeploymentName string
param evalDeploymentName string
param embeddingDeploymentName string
param bingConnectionName string
param searchEndpoint string
param aiResourceGroup string
param aiProjectName string
param aiLocation string
param subscriptionId string

var abbrs = loadJsonContent('../abbreviations.json')

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${abbrs.insightsComponents}${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${abbrs.containerRegistryRegistries}${resourceToken}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// AcrPull for the shared identity so the container apps can pull images.
var acrPullRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, managedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: acrPullRoleId
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'aca-env-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

var apiEnv = [
  { name: 'LOCAL_TRACING_ENABLED', value: 'false' }
  { name: 'OPENAI_TYPE', value: 'azure' }
  { name: 'AZURE_CLIENT_ID', value: managedIdentityClientId }
  { name: 'AZURE_AI_PROJECT_ENDPOINT', value: aiProjectEndpoint }
  { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
  { name: 'AZURE_OPENAI_NAME', value: openAiName }
  { name: 'AZURE_OPENAI_API_VERSION', value: openAiApiVersion }
  { name: 'AZURE_OPENAI_DEPLOYMENT_NAME', value: chatDeploymentName }
  { name: 'AZURE_OPENAI_4_EVAL_DEPLOYMENT_NAME', value: evalDeploymentName }
  { name: 'AZURE_EMBEDDING_NAME', value: embeddingDeploymentName }
  { name: 'BING_CONNECTION_NAME', value: bingConnectionName }
  { name: 'AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
  { name: 'AI_SEARCH_ENDPOINT', value: searchEndpoint }
  { name: 'AZURE_SUBSCRIPTION_ID', value: subscriptionId }
  { name: 'AZURE_RESOURCE_GROUP', value: aiResourceGroup }
  { name: 'AZURE_AI_PROJECT_NAME', value: aiProjectName }
  { name: 'AZURE_LOCATION', value: aiLocation }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
]

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'agent-api'
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  dependsOn: [ acrPull ]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentityId}': {} }
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: [ '*' ]
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'main'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: apiEnv
          resources: { cpu: json('1.0'), memory: '2.0Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
}

resource webApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'agent-web'
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  dependsOn: [ acrPull ]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentityId}': {} }
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'main'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            { name: 'AZURE_CLIENT_ID', value: managedIdentityClientId }
            { name: 'API_ENDPOINT', value: 'https://${apiApp.properties.configuration.ingress.fqdn}' }
          ]
          resources: { cpu: json('0.5'), memory: '1.0Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

output containerRegistryEndpoint string = containerRegistry.properties.loginServer
output containerRegistryName string = containerRegistry.name
output containerEnvironmentName string = containerEnv.name
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
output apiName string = apiApp.name
output apiUri string = 'https://${apiApp.properties.configuration.ingress.fqdn}'
output webName string = webApp.name
output webUri string = 'https://${webApp.properties.configuration.ingress.fqdn}'
