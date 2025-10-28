# Quick Start: n8n Automatic PDF Processing

## What This Does

When you upload a PDF to your BOQ application, the system will:
1. ✅ Save the file to disk
2. ✅ Trigger n8n workflow via webhook
3. ✅ Extract all text from the PDF
4. ✅ Split text into searchable chunks
5. ✅ Generate AI embeddings and store in vector database
6. ✅ Use AI to auto-generate tags (e.g., "construction", "electrical", "specifications")
7. ✅ Update document status to "completed"
8. ✅ Make document searchable via chat and document search

## Setup (5 minutes)

### Step 1: Open n8n
```
http://localhost:5678
```
**First time?** Create an account with any email (e.g., `admin@boq.local`) and password.
**Already setup?** Login with your email and password.

### Step 2: Import Workflow
1. Click **"Workflows"** → **"Add workflow"** (+ button)
2. Click **"..."** menu → **"Import from File"**
3. Select: `C:\WORK\BOQ\n8n-workflows\pdf-auto-processing.json`
4. Click **"Save"**

### Step 3: Activate Workflow
Toggle the **"Active"** switch to **ON** (top right corner)

### Step 4: Enable n8n in Backend
Add to `C:\WORK\BOQ\be\.env`:
```env
USE_N8N_PROCESSING=true
N8N_WEBHOOK_URL=http://localhost:5678/webhook/boq-document-upload
```

### Step 5: Restart Backend
```bash
cd C:\WORK\BOQ\be
python main.py
```

## That's It!

Now when you upload PDFs through the AI Assistant, they'll be automatically processed via n8n.

## Test It

1. Open your BOQ app and login as senior_admin
2. Click **"AI Assistant"** in sidebar
3. Upload a PDF file
4. Watch n8n dashboard to see the workflow execute
5. Once complete, ask the AI chat: "What did I just upload?"

## Monitoring

### View Workflow Runs
Go to n8n → **"Executions"** to see all processing runs with success/failure status

### View Document Status
In AI chat, ask: "Show me all my documents"

## Troubleshooting

**Issue**: Workflow not triggering
- Check n8n is running: `docker ps | findstr n8n`
- Verify workflow is **Active** (green toggle in n8n)

**Issue**: Processing slow
- First run downloads the AI model (takes 5-10 min)
- After that, processing is 10-30 seconds per document

## Next Steps

Once working, you can:
- Add email notifications when processing completes
- Schedule cleanup of old documents
- Integrate with cloud storage (Dropbox, Google Drive)
- Create custom tag categorization rules

See `SETUP_GUIDE.md` for advanced configuration.
