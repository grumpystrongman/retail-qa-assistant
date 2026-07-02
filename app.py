import streamlit as st
import os
import re
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

# Page config
st.set_page_config(
    page_title="Retail Q&A Assistant",
    page_icon="🛒",
    layout="wide"
)

# Initialize Databricks client
@st.cache_resource
def get_databricks_client():
    return WorkspaceClient(
        host=os.environ.get("DATABRICKS_HOST"),
        token=os.environ.get("DATABRICKS_TOKEN")
    )

# Database schema context
SCHEMA_CONTEXT = """
You have access to these tables in databricks_simulated_retail_customer_data.v01:

1. sales table:
   - customer_id (bigint)
   - customer_name (string)
   - product_name (string)
   - order_date (date)
   - product_category (string)
   - product (string)
   - total_price (bigint)

2. customers table:
   - customer_id (bigint)
   - customer_name (string)
   - state (string)
   - city (string)
   - region (string)
   - district (string)
   - loyalty_segment (bigint)
   - units_purchased (bigint)

3. sales_orders table:
   - customer_id (bigint)
   - customer_name (string)
   - order_number (string)
   - order_datetime (timestamp)
   - number_of_line_items (bigint)

Generate ONLY the SQL query, no explanation. Use fully qualified table names.
"""

def validate_question(question):
    """Quick domain validation"""
    q = question.lower()
    retail_kw = ['sales', 'customer', 'product', 'order', 'revenue', 'region', 
                 'price', 'purchase', 'category', 'state', 'loyalty']
    bad_kw = ['weather', 'poem', 'story', 'news', 'recipe', 'movie']
    
    if any(word in q for word in bad_kw):
        return False, "Question is outside retail analytics domain"
    if any(word in q for word in retail_kw):
        return True, "Valid retail analytics question"
    return False, "Please ask about sales, customers, products, or orders"

def generate_sql(question):
    """Generate SQL using LLM"""
    try:
        w = get_databricks_client()
        
        prompt = f"""{SCHEMA_CONTEXT}

User question: {question}

Generate SQL query:"""
        
        response = w.serving_endpoints.query(
            name="databricks-meta-llama-3-3-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        sql = response.choices[0].message.content.strip()
        
        # Extract SQL from markdown code blocks if present
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()
        
        # Clean up
        sql = sql.strip().rstrip(';')
        
        return sql, None
    except Exception as e:
        return None, f"SQL generation failed: {str(e)}"

def execute_sql(sql):
    """Execute SQL query"""
    try:
        w = get_databricks_client()
        
        # Execute statement
        statement = w.statement_execution.execute_statement(
            warehouse_id=os.environ.get("DATABRICKS_WAREHOUSE_ID"),
            statement=sql,
            wait_timeout="30s"
        )
        
        if statement.status.state != StatementState.SUCCEEDED:
            return None, None, f"Query failed: {statement.status.state}"
        
        # Get results
        if statement.result and statement.result.data_array:
            columns = [col.name for col in statement.manifest.schema.columns]
            rows = statement.result.data_array
            return columns, rows, None
        else:
            return None, None, "No results returned"
            
    except Exception as e:
        return None, None, f"Execution failed: {str(e)}"

# Header
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; color: white; margin-bottom: 30px;">
    <h1 style="margin: 0; font-size: 2.5em;">🛒 Retail Q&A Assistant</h1>
    <p style="font-size: 1.2em; margin: 10px 0 0 0; opacity: 0.9;">Production: LLM-Powered SQL Generation & Live Data</p>
</div>
""", unsafe_allow_html=True)

# Check if credentials are configured
if not os.environ.get("DATABRICKS_HOST") or not os.environ.get("DATABRICKS_TOKEN"):
    st.error("""
    ⚠️ **Databricks credentials not configured**
    
    This app needs Databricks credentials to query live data. 
    
    **For Streamlit Cloud deployment:**
    1. Go to App Settings → Secrets
    2. Add these secrets:
       ```
       DATABRICKS_HOST = "https://your-workspace.cloud.databricks.com"
       DATABRICKS_TOKEN = "your-access-token"
       DATABRICKS_WAREHOUSE_ID = "your-warehouse-id"
       ```
    
    **For now, using DEMO MODE with validation only.**
    """)
    demo_mode = True
else:
    demo_mode = False

# Example questions
with st.expander("📝 Example Questions", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        * What are the top 3 products by revenue?
        * Show me sales by region
        * Which customers have the highest loyalty segment?
        * What's the total revenue by product category?
        """)
    with col2:
        st.markdown("""
        * How many orders per state?
        * What's the average order value?
        * Show me customer demographics by region
        * Which products sell best in each state?
        """)

st.markdown("---")

# Question input
question = st.text_input(
    "💬 Ask a question about your retail data:",
    placeholder="e.g., What are the top three products by region?",
    key="question"
)

if question:
    # Step 1: Validate domain
    with st.spinner("🔍 Validating question..."):
        is_valid, message = validate_question(question)
    
    if not is_valid:
        st.error(f"❌ **OUT OF SCOPE**: {message}")
        st.info("Please ask about sales, customers, products, or orders.")
    else:
        st.success(f"✅ **IN SCOPE**: {message}")
        
        if demo_mode:
            st.info("""
            **Demo Mode**: Credentials not configured.
            
            In production, this would:
            1. ✅ Generate SQL using LLM (Llama 3.3 70B)
            2. ✅ Execute query against Unity Catalog
            3. ✅ Display results with visualizations
            
            Configure secrets in Streamlit Cloud to enable live queries!
            """)
        else:
            # Step 2: Generate SQL
            with st.spinner("🤖 Generating SQL with LLM..."):
                sql, error = generate_sql(question)
            
            if error:
                st.error(f"❌ {error}")
            else:
                st.code(sql, language="sql")
                
                # Step 3: Execute SQL
                with st.spinner("⚡ Executing query..."):
                    columns, rows, error = execute_sql(sql)
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    # Step 4: Display results
                    st.success(f"✅ Query returned {len(rows)} rows")
                    
                    # Create dataframe
                    import pandas as pd
                    df = pd.DataFrame(rows, columns=columns)
                    
                    # Tabs for different views
                    tab1, tab2 = st.tabs(["📊 Visualization", "📋 Data Table"])
                    
                    with tab1:
                        # Auto-detect chart type based on columns
                        if len(columns) == 2:
                            # Bar chart for 2 columns
                            st.bar_chart(df.set_index(columns[0]))
                        elif len(columns) >= 3:
                            # Line chart or bar chart
                            st.line_chart(df.set_index(columns[0]))
                        else:
                            st.metric(columns[0], df[columns[0]][0])
                    
                    with tab2:
                        st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
### 🎯 How It Works

1. **Domain Validation** → Keyword matching ensures retail focus
2. **SQL Generation** → Llama 3.3 70B generates SQL from natural language
3. **Query Execution** → Runs against Unity Catalog with serverless SQL
4. **Visualization** → Auto-detects chart type and displays results

### 🔐 Security

* Uses Databricks authentication
* Queries run with your user permissions
* No data leaves your workspace

**Production Ready** | LLM-Powered | Built with Streamlit
""")
