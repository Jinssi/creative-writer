#!/bin/sh
set -e

echo "Exporting azd environment values to .env ..."
azd env get-values > .env

if [ -n "$WEB_SERVICE_ACA_URI" ]; then
  azd env set REACT_APP_API_BASE_URL "$WEB_SERVICE_ACA_URI"
fi

echo "--- OK | Post-provisioning complete. Reusing existing Foundry AI resources. ---"
echo "Product search needs the 'contoso-products' index in $AZURE_SEARCH_ENDPOINT."
echo "Populate it with: jupyter nbconvert --execute --to python data/create-azure-search.ipynb"
