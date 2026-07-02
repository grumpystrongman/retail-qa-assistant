# 🚀 Streamlit Cloud Deployment with Databricks

## Step-by-Step Guide

### Step 1: Get Databricks Credentials

You need three values from your Databricks workspace:

#### 1. DATABRICKS_HOST
Your workspace URL:
```
https://dbc-7f44c466-4486.cloud.databricks.com
```

#### 2. DATABRICKS_TOKEN
Create a personal access token:
1. Go to: User Settings → Developer → Access tokens
2. Click "Manage" or "Generate new token"
3. Enter a comment (e.g., "Streamlit Cloud App")
4. Set lifetime (90 days recommended)
5. Click "Generate"
6. **COPY THE TOKEN** (you won't see it again!)

#### 3. DATABRICKS_WAREHOUSE_ID
Get your SQL Warehouse ID:
1. Go to: SQL Warehouses in Databricks
2. Click on your warehouse
3. Copy the ID from the URL or "Connection details"
   Example: `abc123def456`

---

### Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   → https://share.streamlit.io/

2. **Sign in with GitHub**
   → Use your grumpystrongman account

3. **Click "New app"**

4. **Configure:**
   * Repository: `grumpystrongman/retail-qa-assistant`
   * Branch: `main`
   * Main file path: `app.py`

5. **Click "Advanced settings"** (IMPORTANT!)

6. **Add Secrets** - Copy and paste this, replacing with your values:
```toml
DATABRICKS_HOST = "https://dbc-7f44c466-4486.cloud.databricks.com"
DATABRICKS_TOKEN = "dapi1234567890abcdef"
DATABRICKS_WAREHOUSE_ID = "your-warehouse-id"
```

7. **Click "Deploy"**

⏱️ Deployment takes 3-5 minutes

---

### Step 3: Test Your App

Once deployed, try these questions:

* "What are the top 3 products by revenue?"
* "Show me sales by region"
* "Which customers have the highest loyalty segment?"

You should see:
1. ✅ Domain validation
2. 🤖 SQL generation (visible)
3. ⚡ Query execution
4. 📊 Results visualization

---

## Troubleshooting

### "Credentials not configured"
* Check secrets are saved in Streamlit Cloud
* Restart the app after adding secrets
* Verify no extra spaces in secret values

### "Authentication failed"
* Token expired → Generate new token in Databricks
* Token invalid → Check you copied it completely
* No warehouse access → Verify warehouse permissions

### "Table not found"
* Check you have READ access to:
  * `databricks_simulated_retail_customer_data.v01.sales`
  * `databricks_simulated_retail_customer_data.v01.customers`
  * `databricks_simulated_retail_customer_data.v01.sales_orders`

### SQL generation issues
* LLM endpoint `databricks-meta-llama-3-3-70b-instruct` must be available
* Check workspace has access to Foundation Models

---

## Demo Mode

If secrets are not configured, the app runs in **Demo Mode**:
* ✅ Domain validation works
* ❌ No SQL generation
* ❌ No data queries
* Shows what would happen in production

This lets you test the interface before adding credentials!

---

## Security Best Practices

* 🔐 Use token with READ-ONLY access
* ⏱️ Set token expiration (90 days max)
* 🔄 Rotate tokens regularly
* 🚫 Never commit tokens to Git
* 👥 Use service principal for production (optional)

---

## Updating the App

Any push to GitHub automatically redeploys:
```bash
# Make changes in Databricks Git folder
git commit -m "Update feature X"
git push

# Streamlit Cloud auto-redeploys in 1-2 minutes
```

---

## Need Help?

* Databricks tokens: https://docs.databricks.com/en/dev-tools/auth.html
* Streamlit secrets: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management
* SQL Warehouse setup: https://docs.databricks.com/en/compute/sql-warehouse/index.html
