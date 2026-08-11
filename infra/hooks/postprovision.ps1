#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

Write-Output "Exporting azd environment values to .env ..."
azd env get-values > .env

if ($env:WEB_SERVICE_ACA_URI) {
    azd env set REACT_APP_API_BASE_URL $env:WEB_SERVICE_ACA_URI
}

Write-Host "--- OK | Post-provisioning complete. Reusing existing Foundry AI resources. ---"
Write-Host "Product search needs the 'contoso-products' index in $($env:AZURE_SEARCH_ENDPOINT)."
Write-Host "Populate it with: jupyter nbconvert --execute --to python data/create-azure-search.ipynb"
