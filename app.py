import streamlit as st

# Page config
st.set_page_config(
    page_title="Retail Q&A Assistant",
    page_icon="🛒",
    layout="wide"
)

# Header
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; color: white; margin-bottom: 30px;">
    <h1 style="margin: 0; font-size: 2.5em;">🛒 Retail Q&A Assistant</h1>
    <p style="font-size: 1.2em; margin: 10px 0 0 0; opacity: 0.9;">Domain-Constrained Q&A for Retail Analytics</p>
</div>
""", unsafe_allow_html=True)

# Overview
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background: #10b981; padding: 25px; border-radius: 10px; text-align: center; color: white;">
        <div style="font-size: 3em; font-weight: bold;">6</div>
        <div style="font-size: 1.2em; margin-top: 10px;">Valid Topics</div>
        <div style="opacity: 0.8; margin-top: 5px;">✅ Sales, Customers, Products</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: #ef4444; padding: 25px; border-radius: 10px; text-align: center; color: white;">
        <div style="font-size: 3em; font-weight: bold;">6</div>
        <div style="font-size: 1.2em; margin-top: 10px;">Blocked Topics</div>
        <div style="opacity: 0.8; margin-top: 5px;">❌ Weather, Poems, News</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: #3b82f6; padding: 25px; border-radius: 10px; text-align: center; color: white;">
        <div style="font-size: 3em; font-weight: bold;">3</div>
        <div style="font-size: 1.2em; margin-top: 10px;">Data Sources</div>
        <div style="opacity: 0.8; margin-top: 5px;">📊 Customers, Sales, Orders</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Example questions
col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✅ Valid Questions (In Scope)")
    st.markdown("""
    * What are total sales by region?
    * Show me customer demographics
    * Which products perform best?
    * How many orders per state?
    * What's the average basket size?
    """)

with col2:
    st.markdown("### ❌ Invalid Questions (Out of Scope)")
    st.markdown("""
    * What's the weather today? - *Not retail data*
    * Write a poem - *Creative content*
    * Tell me about history - *General knowledge*
    * Latest news headlines? - *Out of domain*
    * How do I make cookies? - *Not business data*
    """)

st.markdown("---")

# Validation function
def validate_question(question):
    """Validate if question is in retail domain"""
    if not question:
        return None
    
    q = question.lower()
    
    # Retail keywords
    retail_kw = ['sales', 'customer', 'product', 'order', 'revenue', 'region', 
                 'loyalty', 'purchase', 'price', 'quantity', 'category', 'basket',
                 'segment', 'demographic', 'transaction', 'sku', 'state']
    
    # Out-of-scope keywords
    bad_kw = ['weather', 'climate', 'poem', 'story', 'recipe', 'news', 'movie',
              'music', 'history', 'capital', 'celebrity', 'politics', 'sports']
    
    # Check for out-of-scope
    if any(word in q for word in bad_kw):
        return {
            "in_scope": False,
            "reason": "This question is outside the retail analytics domain. Please ask about sales, customers, orders, or product data."
        }
    
    # Check for retail keywords
    if any(word in q for word in retail_kw):
        return {
            "in_scope": True,
            "reason": "Question appears to be about retail data."
        }
    
    # Unclear/ambiguous
    return {
        "in_scope": False,
        "reason": "Please ask a specific question about retail sales, customers, orders, or products."
    }

# Interactive section
st.markdown("## 💬 Try It Out")

question = st.text_input(
    "Your Question",
    placeholder="Type your question here...",
    key="question_input"
)

if question:
    result = validate_question(question)
    
    if result:
        if result["in_scope"]:
            st.success(f"✅ **IN SCOPE** - {result['reason']}")
            st.info("""
            **Next Steps (Production):**
            1. Generate SQL query from natural language
            2. Execute query against Unity Catalog tables
            3. Format and display results with charts
            
            *This is a domain validation demo. Full Q&A pipeline coming soon!*
            """)
        else:
            st.error(f"❌ **OUT OF SCOPE** - {result['reason']}")
            st.warning("""
            **Try asking about:**
            * Sales and revenue metrics
            * Customer demographics and segments
            * Product performance and categories
            * Regional analysis
            * Order patterns and basket analysis
            """)

# Footer
st.markdown("---")
st.markdown("""
### 🎯 How It Works

1. **Question arrives** → Extract keywords and analyze intent
2. **Domain check** → Match against retail business vocabulary
3. **Scope validation** → Accept or reject with clear reasoning
4. **Next step** → If accepted, generate SQL and query data (production)

### 🚀 Production Integration

This demo validates domain boundaries. In production, it would:
* Use LLMs for sophisticated validation (Foundation Models)
* Generate SQL queries from natural language
* Execute queries against Unity Catalog tables
* Format results with interactive visualizations
* Support multi-turn conversations with history

---

**Demo Mode** | Built with Streamlit | Deployed on Streamlit Cloud
""")
