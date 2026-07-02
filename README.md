# 🛒 Retail Q&A Assistant - Production

**LLM-powered natural language to SQL with live data queries and visualizations**

## Features

* 🤖 **LLM SQL Generation** - Uses Databricks Foundation Models (Llama 3.3 70B)
* 📊 **Live Data Queries** - Executes against Unity Catalog tables
* 📈 **Auto Visualizations** - Automatically creates charts from results
* ✅ **Domain Validation** - Ensures questions are about retail analytics
* 🔐 **Secure** - Uses Databricks authentication

## Data Sources

* `databricks_simulated_retail_customer_data.v01.sales`
* `databricks_simulated_retail_customer_data.v01.customers`
* `databricks_simulated_retail_customer_data.v01.sales_orders`

## Example Questions

* What are the top 3 products by revenue?
* Show me sales by region
* Which customers have the highest loyalty segment?
* How many orders per state?

## Local Development

```bash
# Set environment variables
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token"
export DATABRICKS_WAREHOUSE_ID="your-warehouse-id"

# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

## Streamlit Cloud Deployment

1. Deploy from this GitHub repo
2. Add secrets in App Settings → Secrets:
```toml
DATABRICKS_HOST = "https://your-workspace.cloud.databricks.com"
DATABRICKS_TOKEN = "your-access-token"
DATABRICKS_WAREHOUSE_ID = "your-warehouse-id"
```

## Architecture

```
User Question
     ↓
Domain Validation (keyword matching)
     ↓
LLM SQL Generation (Llama 3.3 70B)
     ↓
Query Execution (Unity Catalog)
     ↓
Visualization (Streamlit charts)
```

## Tech Stack

* **Frontend**: Streamlit
* **LLM**: Databricks Foundation Models
* **Data**: Unity Catalog (Databricks)
* **Compute**: Serverless SQL Warehouse
