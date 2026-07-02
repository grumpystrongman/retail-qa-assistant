# 🚀 Streamlit Cloud Deployment Guide

## Quick Start (5 minutes)

### Step 1: Download Files

Download these three files from your Databricks workspace:
* `app.py` - Main Streamlit application
* `requirements.txt` - Python dependencies
* `README.md` - Project documentation

**Location:** `/Users/cmajeff@gmail.com/streamlit-retail-qa/`

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `retail-qa-assistant`
3. Description: "Domain-constrained Q&A for retail analytics"
4. Make it **Public** (required for free Streamlit Cloud)
5. Click "Create repository"

### Step 3: Push Code to GitHub

```bash
# On your local machine
git clone https://github.com/YOUR-USERNAME/retail-qa-assistant.git
cd retail-qa-assistant

# Copy the three files into this directory
# app.py, requirements.txt, README.md

git add .
git commit -m "Initial Streamlit app"
git push origin main
```

### Step 4: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click "New app"
3. Connect your GitHub account (if first time)
4. Select:
   * Repository: `YOUR-USERNAME/retail-qa-assistant`
   * Branch: `main`
   * Main file path: `app.py`
5. Click "Deploy!"

⏱️ Deployment takes 2-3 minutes

### Step 5: Get Your URL

Your app will be live at:
```
https://YOUR-USERNAME-retail-qa-assistant-app-HASH.streamlit.app
```

Share this URL with anyone!

---

## Alternative: Use Databricks Files

If you don't want to use GitHub:

1. Download files from Databricks workspace
2. Use Streamlit Cloud's drag-and-drop upload
3. Still requires Streamlit Cloud account (free)

---

## Troubleshooting

**Problem:** "Repository must be public"
* Solution: Change repo visibility in GitHub settings

**Problem:** "Module not found"
* Solution: Check `requirements.txt` includes all dependencies

**Problem:** "App won't start"
* Solution: Check Streamlit Cloud logs (click "Manage app" → "Logs")

---

## Next Steps

Once deployed:
* ✅ Test with various questions
* ✅ Share URL with stakeholders
* ✅ Monitor usage in Streamlit Cloud dashboard
* ✅ Update code by pushing to GitHub (auto-redeploys)

---

## Cost

**Streamlit Cloud Community Tier:**
* FREE forever
* 1 GB memory
* 2 CPU cores
* Perfect for demos and small apps

No credit card required!
