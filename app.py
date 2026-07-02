import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
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

# Enhanced schema context with window function examples
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

IMPORTANT PATTERNS:

When the question asks for "top N by X per Y" or "top N X by state/region/category":
Use window functions with ROW_NUMBER() and PARTITION BY.

Example: "Top 3 products by revenue per state"
SELECT state, product_name, total_revenue
FROM (
  SELECT 
    c.state, 
    s.product_name, 
    SUM(s.total_price) AS total_revenue,
    ROW_NUMBER() OVER (PARTITION BY c.state ORDER BY SUM(s.total_price) DESC) as rank
  FROM databricks_simulated_retail_customer_data.v01.sales s
  JOIN databricks_simulated_retail_customer_data.v01.customers c ON s.customer_id = c.customer_id
  GROUP BY c.state, s.product_name
)
WHERE rank <= 3

DO NOT use LIMIT at the end for "per X" queries - use window functions instead.

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

def detect_per_pattern(question):
    """Detect if question asks for top N per category"""
    q = question.lower()
    
    patterns = [
        r'top \d+ .+ (by|per) (state|region|category|customer|product)',
        r'best .+ (by|per|for each) (state|region|category)',
        r'.+ (by|per|for each) (state|region|category|customer)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, q):
            return True
    
    return False

def validate_and_fix_sql(sql, question):
    """Check if SQL needs window function for 'per X' questions"""
    needs_window = detect_per_pattern(question)
    has_limit = 'LIMIT' in sql.upper()
    has_window = 'ROW_NUMBER()' in sql.upper() or 'RANK()' in sql.upper()
    
    if needs_window and has_limit and not has_window:
        return False, """
⚠️ **SQL may be incorrect for 'per X' query**

Your question asks for results **per state/region/category**, but the generated SQL uses LIMIT,
which will only return N rows total, not N rows per category.

**Suggested approach:**
* Use window functions with `ROW_NUMBER() OVER (PARTITION BY ...)`
* Remove the `LIMIT` clause

Would you like me to regenerate the SQL with this pattern?
"""
    
    return True, None

def generate_sql(question):
    """Generate SQL using LLM with enhanced prompt"""
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

def create_visualization(df, viz_type="auto"):
    """Create smart visualizations with multiple options"""
    
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
    
    # Two columns: category + value
    if len(df.columns) == 2 and len(numeric_cols) == 1 and len(categorical_cols) == 1:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        
        if viz_type == "bar":
            fig = px.bar(
                df.sort_values(num_col, ascending=False),
                x=cat_col,
                y=num_col,
                title=f"{num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                color=num_col,
                color_continuous_scale='Blues',
                text=num_col
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=500, showlegend=False)
            
        elif viz_type == "horizontal":
            fig = px.bar(
                df.sort_values(num_col, ascending=True).tail(20),
                y=cat_col,
                x=num_col,
                title=f"Top 20: {num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                color=num_col,
                color_continuous_scale='Viridis',
                text=num_col,
                orientation='h'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=600, showlegend=False)
            
        elif viz_type == "pie":
            top_n = df.nlargest(10, num_col)
            fig = px.pie(
                top_n,
                names=cat_col,
                values=num_col,
                title=f"Top 10: {num_col.replace('_', ' ').title()} Distribution"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=500)
        
        else:  # auto
            fig = px.bar(
                df.sort_values(num_col, ascending=False).head(15),
                x=cat_col,
                y=num_col,
                title=f"Top 15: {num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                color=num_col,
                color_continuous_scale='Blues',
                text=num_col
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=500, showlegend=False)
        
        st.plotly_chart(fig, use_container_width=True)
        return
    
    # Three columns: 2 categorical + 1 numeric
    if len(df.columns) == 3 and len(numeric_cols) == 1 and len(categorical_cols) == 2:
        group_col = categorical_cols[0]
        category_col = categorical_cols[1]
        value_col = numeric_cols[0]
        
        if viz_type == "grouped_bar":
            # Standard grouped bar chart
            fig = px.bar(
                df,
                x=category_col,
                y=value_col,
                color=group_col,
                title=f"{value_col.replace('_', ' ').title()} by {category_col.replace('_', ' ').title()} and {group_col.replace('_', ' ').title()}",
                barmode='group',
                text=value_col
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
        elif viz_type == "faceted":
            # Small multiples - one chart per group
            groups = sorted(df[group_col].unique())
            n_groups = len(groups)
            
            # Create subplots
            cols = 3
            rows = (n_groups + cols - 1) // cols
            
            fig = make_subplots(
                rows=rows, cols=cols,
                subplot_titles=[f"{group_col.title()}: {g}" for g in groups],
                vertical_spacing=0.12,
                horizontal_spacing=0.1
            )
            
            colors = px.colors.qualitative.Set2
            
            for idx, group in enumerate(groups):
                row = idx // cols + 1
                col = idx % cols + 1
                
                group_data = df[df[group_col] == group].sort_values(value_col, ascending=False)
                
                fig.add_trace(
                    go.Bar(
                        x=group_data[category_col],
                        y=group_data[value_col],
                        name=str(group),
                        marker_color=colors[idx % len(colors)],
                        text=group_data[value_col],
                        texttemplate='%{text:,.0f}',
                        textposition='outside',
                        showlegend=False
                    ),
                    row=row, col=col
                )
            
            fig.update_layout(
                title_text=f"{value_col.replace('_', ' ').title()} by {category_col.replace('_', ' ').title()} (Per {group_col.replace('_', ' ').title()})",
                height=300 * rows,
                showlegend=False
            )
            
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
        elif viz_type == "heatmap":
            # Pivot for heatmap
            pivot = df.pivot(index=group_col, columns=category_col, values=value_col)
            
            fig = px.imshow(
                pivot,
                labels=dict(x=category_col.replace('_', ' ').title(), 
                           y=group_col.replace('_', ' ').title(), 
                           color=value_col.replace('_', ' ').title()),
                title=f"{value_col.replace('_', ' ').title()} Heatmap",
                color_continuous_scale='Blues',
                text_auto='.0f'
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
        elif viz_type == "treemap":
            # Hierarchical treemap
            fig = px.treemap(
                df,
                path=[group_col, category_col],
                values=value_col,
                title=f"{value_col.replace('_', ' ').title()} Distribution",
                color=value_col,
                color_continuous_scale='Viridis'
            )
            fig.update_traces(textinfo="label+value+percent parent")
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
        elif viz_type == "sunburst":
            # Sunburst chart
            fig = px.sunburst(
                df,
                path=[group_col, category_col],
                values=value_col,
                title=f"{value_col.replace('_', ' ').title()} Hierarchy",
                color=value_col,
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
        else:  # auto - use faceted for better readability
            # Default to faceted view for multi-dimensional data
            groups = sorted(df[group_col].unique())
            n_groups = min(len(groups), 12)  # Limit to 12
            groups = groups[:n_groups]
            
            cols = 3
            rows = (n_groups + cols - 1) // cols
            
            fig = make_subplots(
                rows=rows, cols=cols,
                subplot_titles=[f"{g}" for g in groups],
                vertical_spacing=0.15,
                horizontal_spacing=0.1
            )
            
            colors = px.colors.qualitative.Set2
            
            for idx, group in enumerate(groups):
                row = idx // cols + 1
                col = idx % cols + 1
                
                group_data = df[df[group_col] == group].sort_values(value_col, ascending=False)
                
                fig.add_trace(
                    go.Bar(
                        x=group_data[category_col],
                        y=group_data[value_col],
                        marker_color=colors[idx % len(colors)],
                        text=group_data[value_col],
                        texttemplate='%{text:,.0f}',
                        textposition='outside',
                        showlegend=False
                    ),
                    row=row, col=col
                )
            
            fig.update_layout(
                title_text=f"{value_col.replace('_', ' ').title()} per {group_col.replace('_', ' ').title()}",
                height=300 * rows,
                showlegend=False
            )
            
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        return
    
    # Default: show data table
    st.dataframe(df, use_container_width=True, height=400)

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
        * Show me top 5 products **per state**
        * Which customers have the highest loyalty segment?
        * What's the total revenue by product category?
        """)
    with col2:
        st.markdown("""
        * How many orders per state?
        * What's the average order value?
        * Top 3 products by revenue **per region**
        * Best selling product **per category**
        """)

st.markdown("---")

# Question input
question = st.text_input(
    "💬 Ask a question about your retail data:",
    placeholder="e.g., What are the top three products per state?",
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
                # Validate SQL for "per X" patterns
                is_valid_sql, warning = validate_and_fix_sql(sql, question)
                
                with st.expander("📄 Generated SQL", expanded=not is_valid_sql):
                    st.code(sql, language="sql")
                    
                    if not is_valid_sql:
                        st.warning(warning)
                        if st.button("🔄 Regenerate with window function hint"):
                            hint_prompt = f"""
{SCHEMA_CONTEXT}

User question: {question}

CRITICAL: This question asks for results PER category. You MUST use window functions:
- Use ROW_NUMBER() OVER (PARTITION BY ...) 
- DO NOT use LIMIT

Generate SQL query:"""
                            
                            response = get_databricks_client().serving_endpoints.query(
                                name="databricks-meta-llama-3-3-70b-instruct",
                                messages=[ChatMessage(role=ChatMessageRole.USER, content=hint_prompt)],
                                temperature=0.1,
                                max_tokens=500
                            )
                            
                            sql = response.choices[0].message.content.strip()
                            if "```sql" in sql:
                                sql = sql.split("```sql")[1].split("```")[0].strip()
                            elif "```" in sql:
                                sql = sql.split("```")[1].split("```")[0].strip()
                            sql = sql.strip().rstrip(';')
                            
                            st.code(sql, language="sql")
                            st.success("✅ Regenerated with window function pattern!")
                            st.rerun()
                
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
                        # Visualization type selector for multi-dimensional data
                        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
                        categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
                        
                        if len(df.columns) == 3 and len(numeric_cols) == 1 and len(categorical_cols) == 2:
                            st.markdown("### 🎨 Choose Visualization Type")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if st.button("📊 Faceted (Recommended)", use_container_width=True):
                                    st.session_state.viz_type = "faceted"
                                if st.button("🟦 Heatmap", use_container_width=True):
                                    st.session_state.viz_type = "heatmap"
                            
                            with col2:
                                if st.button("📈 Grouped Bars", use_container_width=True):
                                    st.session_state.viz_type = "grouped_bar"
                                if st.button("🌳 Treemap", use_container_width=True):
                                    st.session_state.viz_type = "treemap"
                            
                            with col3:
                                if st.button("🌅 Sunburst", use_container_width=True):
                                    st.session_state.viz_type = "sunburst"
                            
                            # Get current viz type
                            viz_type = st.session_state.get('viz_type', 'auto')
                            
                            st.markdown("---")
                            create_visualization(df, viz_type)
                            
                        elif len(df.columns) == 2 and len(numeric_cols) == 1 and len(categorical_cols) == 1:
                            st.markdown("### 🎨 Choose Visualization Type")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if st.button("📊 Bar Chart", use_container_width=True):
                                    st.session_state.viz_type = "bar"
                            with col2:
                                if st.button("↔️ Horizontal Bars", use_container_width=True):
                                    st.session_state.viz_type = "horizontal"
                            with col3:
                                if st.button("🥧 Pie Chart", use_container_width=True):
                                    st.session_state.viz_type = "pie"
                            
                            viz_type = st.session_state.get('viz_type', 'auto')
                            
                            st.markdown("---")
                            create_visualization(df, viz_type)
                        else:
                            create_visualization(df)
                    
                    with tab2:
                        st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
### 🎯 How It Works

1. **Domain Validation** → Ensures questions are about retail analytics
2. **SQL Generation** → Llama 3.3 70B converts natural language to SQL with window function support
3. **Smart Detection** → Detects "per X" patterns and validates SQL correctness
4. **Query Execution** → Runs against Unity Catalog serverless SQL
5. **Multiple Visualizations** → Choose from 5+ chart types for your data

### 🎨 Visualization Options

* **Faceted (Small Multiples)** → Best for "per state/region" queries - one chart per category
* **Heatmap** → Great for comparing values across two dimensions
* **Grouped Bars** → Traditional side-by-side comparison
* **Treemap** → Hierarchical proportional view
* **Sunburst** → Interactive radial hierarchy

### 🔐 Security

* Uses Databricks authentication
* Queries run with your user permissions
* No data leaves your workspace

**Production Ready** | LLM-Powered | Multiple Viz Options | v5.0
""")
