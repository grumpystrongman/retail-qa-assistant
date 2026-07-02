import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
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
   - customer_id (bigint), customer_name (string), product_name (string)
   - order_date (date), product_category (string), product (string), total_price (bigint)

2. customers table:
   - customer_id (bigint), customer_name (string), state (string), city (string)
   - region (string), district (string), loyalty_segment (bigint), units_purchased (bigint)

3. sales_orders table:
   - customer_id (bigint), customer_name (string), order_number (string)
   - order_datetime (timestamp), number_of_line_items (bigint)

Generate ONLY the SQL query, no explanation. Use fully qualified table names.
"""

def validate_question(question):
    """Quick domain validation"""
    q = question.lower()
    retail_kw = ['sales', 'customer', 'product', 'order', 'revenue', 'region', 
                 'price', 'purchase', 'category', 'state', 'loyalty', 'top', 'best']
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
            messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
            temperature=0.1,
            max_tokens=500
        )
        
        sql = response.choices[0].message.content.strip()
        
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()
        
        sql = sql.strip().rstrip(';')
        
        return sql, None
    except Exception as e:
        return None, f"SQL generation failed: {str(e)}"

def execute_sql(sql):
    """Execute SQL query"""
    try:
        w = get_databricks_client()
        
        statement = w.statement_execution.execute_statement(
            warehouse_id=os.environ.get("DATABRICKS_WAREHOUSE_ID"),
            statement=sql,
            wait_timeout="50s"
        )
        
        if statement.status.state != StatementState.SUCCEEDED:
            return None, None, f"Query failed: {statement.status.state}"
        
        if statement.result and statement.result.data_array:
            columns = [col.name for col in statement.manifest.schema.columns]
            rows = statement.result.data_array
            return columns, rows, None
        else:
            return None, None, "No results returned"
            
    except Exception as e:
        return None, None, f"Execution failed: {str(e)}"

def create_visualization(df):
    """Create smart visualizations based on data structure"""
    
    if df.empty:
        st.info("No data to visualize")
        return
    
    # Identify numeric and categorical columns
    numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    # Single value result
    if len(df) == 1 and len(numeric_cols) == 1:
        col1, col2, col3 = st.columns(3)
        with col2:
            st.metric(
                label=numeric_cols[0].replace('_', ' ').title(),
                value=f"{df[numeric_cols[0]].iloc[0]:,.0f}"
            )
        return
    
    # Two columns: category + value (simple bar chart)
    if len(df.columns) == 2 and len(numeric_cols) == 1 and len(categorical_cols) == 1:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        
        fig = px.bar(
            df,
            x=cat_col,
            y=num_col,
            title=f"{num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
            color=num_col,
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            xaxis_title=cat_col.replace('_', ' ').title(),
            yaxis_title=num_col.replace('_', ' ').title(),
            showlegend=False,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        return
    
    # Three columns: 2 categorical + 1 numeric (grouped bar chart)
    if len(df.columns) == 3 and len(numeric_cols) == 1 and len(categorical_cols) == 2:
        group_col = categorical_cols[0]
        category_col = categorical_cols[1]
        value_col = numeric_cols[0]
        
        fig = px.bar(
            df,
            x=category_col,
            y=value_col,
            color=group_col,
            title=f"{value_col.replace('_', ' ').title()} by {category_col.replace('_', ' ').title()} and {group_col.replace('_', ' ').title()}",
            barmode='group'
        )
        fig.update_layout(
            xaxis_title=category_col.replace('_', ' ').title(),
            yaxis_title=value_col.replace('_', ' ').title(),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        return
    
    # Multiple numeric columns: show multiple metrics or charts
    if len(numeric_cols) > 1 and len(categorical_cols) >= 1:
        # Create subplots for each numeric column
        cat_col = categorical_cols[0]
        
        for num_col in numeric_cols:
            fig = px.bar(
                df,
                x=cat_col,
                y=num_col,
                title=f"{num_col.replace('_', ' ').title()}",
                color=num_col,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        return
    
    # Default: show data table with highlighting
    st.dataframe(
        df.style.background_gradient(cmap='Blues', subset=numeric_cols if numeric_cols else None),
        use_container_width=True,
        height=400
    )

# Header
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; color: white; margin-bottom: 30px;">
    <h1 style="margin: 0; font-size: 2.5em;">🛒 Retail Q&A Assistant</h1>
    <p style="font-size: 1.2em; margin: 10px 0 0 0; opacity: 0.9;">Production: LLM-Powered SQL Generation & Live Data</p>
</div>
""", unsafe_allow_html=True)

# Check credentials
if not os.environ.get("DATABRICKS_HOST") or not os.environ.get("DATABRICKS_TOKEN"):
    st.error("""
    ⚠️ **Databricks credentials not configured**
    
    Configure secrets in Streamlit Cloud App Settings to enable live queries!
    """)
    demo_mode = True
else:
    demo_mode = False
    st.success("✅ Connected to Databricks")

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
        * Show me top 5 products by state
        * Which regions generate the most revenue?
        """)

st.markdown("---")

# Question input
question = st.text_input(
    "💬 Ask a question about your retail data:",
    placeholder="e.g., What are the top three products by region?",
    key="question"
)

if question:
    # Validate
    with st.spinner("🔍 Validating question..."):
        is_valid, message = validate_question(question)
    
    if not is_valid:
        st.error(f"❌ **OUT OF SCOPE**: {message}")
        st.info("Please ask about sales, customers, products, or orders.")
    else:
        st.success(f"✅ **IN SCOPE**: {message}")
        
        if demo_mode:
            st.info("""
            **Demo Mode**: Configure secrets to enable live queries!
            """)
        else:
            # Generate SQL
            with st.spinner("🤖 Generating SQL with LLM..."):
                sql, error = generate_sql(question)
            
            if error:
                st.error(f"❌ {error}")
            else:
                with st.expander("📄 Generated SQL", expanded=False):
                    st.code(sql, language="sql")
                
                # Execute
                with st.spinner("⚡ Executing query..."):
                    columns, rows, error = execute_sql(sql)
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.success(f"✅ Query returned {len(rows)} rows")
                    
                    # Create dataframe
                    df = pd.DataFrame(rows, columns=columns)
                    
                    # Convert numeric strings to numbers
                    for col in df.columns:
                        try:
                            df[col] = pd.to_numeric(df[col])
                        except:
                            pass
                    
                    # Tabs
                    tab1, tab2 = st.tabs(["📊 Visualization", "📋 Data Table"])
                    
                    with tab1:
                        create_visualization(df)
                    
                    with tab2:
                        # Show styled dataframe
                        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
                        if numeric_cols:
                            st.dataframe(
                                df.style.background_gradient(cmap='Blues', subset=numeric_cols),
                                use_container_width=True
                            )
                        else:
                            st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
### 🎯 How It Works

1. **Domain Validation** → Ensures questions are about retail analytics
2. **SQL Generation** → Llama 3.3 70B converts natural language to SQL
3. **Query Execution** → Runs against Unity Catalog serverless SQL
4. **Smart Visualization** → Automatically creates appropriate charts with Plotly

### 🔐 Security

* Uses Databricks authentication
* Queries run with your user permissions
* No data leaves your workspace

**Production Ready** | LLM-Powered | Built with Streamlit + Plotly | v3.0
""")
