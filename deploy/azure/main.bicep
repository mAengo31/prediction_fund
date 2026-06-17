targetScope = 'resourceGroup'

@description('Azure region for staging resources.')
param location string = resourceGroup().location

@description('Base name used for Azure resources.')
param namePrefix string = 'prediction-desk-staging'

@description('Azure Container Registry name. Must be globally unique, alphanumeric, 5-50 chars.')
param acrName string

@description('Container image repository name inside ACR.')
param imageName string = 'prediction-desk'

@description('Container image tag to deploy.')
param imageTag string = 'latest'

@description('Whether to deploy/update the API Container App. Set false for first infra pass before image push.')
param deployContainerApp bool = true

@description('Whether to create the optional fixture-only scheduled DataOps validation job.')
param deployFixtureDataOpsJob bool = false

@description('Cron expression for the optional fixture-only DataOps job.')
param fixtureDataOpsCron string = '17 */6 * * *'

@description('Container App name for the FastAPI API.')
param containerAppName string = '${namePrefix}-api'

@description('Container Apps Environment name.')
param containerAppsEnvironmentName string = '${namePrefix}-cae'

@description('Log Analytics workspace name.')
param logAnalyticsWorkspaceName string = '${namePrefix}-law'

@description('User-assigned identity used by Container Apps to pull from ACR.')
param containerPullIdentityName string = '${namePrefix}-pull-identity'

@description('PostgreSQL Flexible Server name. Must be globally unique.')
param postgresServerName string

@description('PostgreSQL database name.')
param postgresDatabaseName string = 'prediction_desk'

@description('PostgreSQL admin username.')
param postgresAdminUser string = 'predictiondeskadmin'

@secure()
@description('PostgreSQL admin password. Do not commit real values.')
param postgresAdminPassword string

@secure()
@description('Optional full SQLAlchemy DATABASE_URL. Use this when the password needs URL encoding.')
param databaseUrlOverride string = ''

@secure()
@description('Bearer token required by the staging API. Do not commit real values.')
param predictionDeskApiToken string

@description('PostgreSQL major version.')
param postgresVersion string = '16'

@description('Small staging-safe PostgreSQL SKU.')
param postgresSkuName string = 'Standard_B1ms'

@description('PostgreSQL SKU tier.')
param postgresSkuTier string = 'Burstable'

@description('PostgreSQL storage size in GiB.')
param postgresStorageSizeGB int = 32

@description('PostgreSQL backup retention days.')
param postgresBackupRetentionDays int = 7

@description('Create the Azure-services firewall rule for first-pass staging. Prefer private networking for serious staging.')
param enableAzureServicesPostgresFirewall bool = true

@description('Container App minimum replicas. Keep 0 or 1 for staging cost control.')
param minReplicas int = 0

@description('Container App maximum replicas. Keep small for staging cost control.')
param maxReplicas int = 1

@description('Optional release metadata.')
param appVersion string = ''

@description('Optional git commit metadata.')
param gitCommit string = ''

param tags object = {
  app: 'prediction-desk'
  environment: 'staging'
  managedBy: 'bicep'
}

var imageRef = '${acr.properties.loginServer}/${imageName}:${imageTag}'
var appEnvName = 'staging'
var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var generatedDatabaseUrl = 'postgresql+psycopg://${postgresAdminUser}:${postgresAdminPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/${postgresDatabaseName}?sslmode=require'
var appDatabaseUrl = empty(databaseUrlOverride) ? generatedDatabaseUrl : databaseUrlOverride

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
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

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource containerPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: containerPullIdentityName
  location: location
  tags: tags
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerPullIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    principalId: containerPullIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: location
  tags: tags
  sku: {
    name: postgresSkuName
    tier: postgresSkuTier
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: postgresVersion
    createMode: 'Default'
    storage: {
      storageSizeGB: postgresStorageSizeGB
    }
    backup: {
      backupRetentionDays: postgresBackupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgresServer
  name: postgresDatabaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource allowAzureServicesFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = if (enableAzureServicesPostgresFirewall) {
  parent: postgresServer
  name: 'allow-azure-services'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource apiApp 'Microsoft.App/containerApps@2024-10-02-preview' = if (deployContainerApp) {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${containerPullIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: containerPullIdentity.id
        }
      ]
      secrets: [
        {
          name: 'prediction-desk-api-token'
          value: predictionDeskApiToken
        }
        {
          name: 'prediction-desk-database-url'
          value: appDatabaseUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'prediction-desk-api'
          image: imageRef
          command: [
            'uvicorn'
          ]
          args: [
            'prediction_desk.api.app:create_app'
            '--factory'
            '--host'
            '0.0.0.0'
            '--port'
            '8000'
          ]
          env: [
            {
              name: 'APP_ENV'
              value: appEnvName
            }
            {
              name: 'REQUIRE_API_TOKEN'
              value: 'true'
            }
            {
              name: 'ENABLE_OPENAPI_DOCS'
              value: 'false'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'prediction-desk-database-url'
            }
            {
              name: 'PREDICTION_DESK_API_TOKEN'
              secretRef: 'prediction-desk-api-token'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
            {
              name: 'APP_VERSION'
              value: appVersion
            }
            {
              name: 'GIT_COMMIT'
              value: gitCommit
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 30
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
  dependsOn: [
    acrPull
    postgresDatabase
  ]
}

resource fixtureDataOpsJob 'Microsoft.App/jobs@2024-10-02-preview' = if (deployContainerApp && deployFixtureDataOpsJob) {
  name: '${namePrefix}-fixture-dataops'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${containerPullIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerEnv.id
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 1800
      replicaRetryLimit: 1
      scheduleTriggerConfig: {
        cronExpression: fixtureDataOpsCron
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: containerPullIdentity.id
        }
      ]
      secrets: [
        {
          name: 'prediction-desk-database-url'
          value: appDatabaseUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'prediction-desk-fixture-dataops'
          image: imageRef
          command: [
            'prediction-desk'
          ]
          args: [
            'dataops-cycle'
            '--mode'
            'FIXTURE'
          ]
          env: [
            {
              name: 'APP_ENV'
              value: appEnvName
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'prediction-desk-database-url'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
  dependsOn: [
    acrPull
    postgresDatabase
  ]
}

output acrLoginServer string = acr.properties.loginServer
output postgresServerFqdn string = postgresServer.properties.fullyQualifiedDomainName
output containerAppName string = containerAppName
output containerAppFqdn string = apiApp.?properties.?configuration.?ingress.?fqdn ?? ''
output fixtureDataOpsJobName string = fixtureDataOpsJob.?name ?? ''
