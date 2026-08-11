targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param environmentName string

@description('Primary location for the compute resources')
param location string = 'swedencentral'

@description('Existing resource group that hosts the frontends/compute')
param resourceGroupName string

// ---- Shared, reused managed identity (Foundry roles already granted) ----
param managedIdentityId string
param managedIdentityClientId string
param managedIdentityPrincipalId string

// ---- Existing Foundry / AI resources (reused, not created) ----
param aiProjectEndpoint string
param openAiEndpoint string
param openAiName string
param openAiApiVersion string = '2025-04-01-preview'
param chatDeploymentName string = 'gpt-5.6-sol'
param evalDeploymentName string = 'gpt-5.6-sol-eval'
param embeddingDeploymentName string = 'text-embedding-3-large'
param bingConnectionName string
param searchEndpoint string
param aiResourceGroup string
param aiProjectName string
param aiLocation string = 'swedencentral'

param tags object = {}

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var defaultTags = union({ 'azd-env-name': environmentName }, tags)

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: resourceGroupName
}

module compute 'app/compute.bicep' = {
  name: 'compute'
  scope: rg
  params: {
    location: location
    tags: defaultTags
    resourceToken: resourceToken
    managedIdentityId: managedIdentityId
    managedIdentityClientId: managedIdentityClientId
    managedIdentityPrincipalId: managedIdentityPrincipalId
    aiProjectEndpoint: aiProjectEndpoint
    openAiEndpoint: openAiEndpoint
    openAiName: openAiName
    openAiApiVersion: openAiApiVersion
    chatDeploymentName: chatDeploymentName
    evalDeploymentName: evalDeploymentName
    embeddingDeploymentName: embeddingDeploymentName
    bingConnectionName: bingConnectionName
    searchEndpoint: searchEndpoint
    aiResourceGroup: aiResourceGroup
    aiProjectName: aiProjectName
    aiLocation: aiLocation
    subscriptionId: subscription().subscriptionId
  }
}

// ---- azd wiring ----
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = compute.outputs.containerRegistryEndpoint
output AZURE_CONTAINER_REGISTRY_NAME string = compute.outputs.containerRegistryName
output AZURE_CONTAINER_ENVIRONMENT_NAME string = compute.outputs.containerEnvironmentName

output API_SERVICE_ACA_NAME string = compute.outputs.apiName
output API_SERVICE_ACA_URI string = compute.outputs.apiUri
output WEB_SERVICE_ACA_NAME string = compute.outputs.webName
output WEB_SERVICE_ACA_URI string = compute.outputs.webUri
output SERVICE_WEB_URI string = compute.outputs.webUri

// ---- App configuration echoed into .env (reused AI resources) ----
output APPLICATIONINSIGHTS_CONNECTION_STRING string = compute.outputs.applicationInsightsConnectionString
output AZURE_AI_PROJECT_ENDPOINT string = aiProjectEndpoint
output AZURE_AI_PROJECT_NAME string = aiProjectName
output AZURE_OPENAI_ENDPOINT string = openAiEndpoint
output AZURE_OPENAI_NAME string = openAiName
output AZURE_OPENAI_API_VERSION string = openAiApiVersion
output AZURE_OPENAI_DEPLOYMENT_NAME string = chatDeploymentName
output AZURE_OPENAI_4_EVAL_DEPLOYMENT_NAME string = evalDeploymentName
output AZURE_EMBEDDING_NAME string = embeddingDeploymentName
output BING_CONNECTION_NAME string = bingConnectionName
output AZURE_SEARCH_ENDPOINT string = searchEndpoint
output OPENAI_TYPE string = 'azure'
