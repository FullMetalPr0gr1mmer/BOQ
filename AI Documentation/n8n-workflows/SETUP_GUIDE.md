# n8n Workflow Setup Guide - Automatic PDF Processing

## Overview
This workflow automatically processes uploaded PDFs by:
1. Receiving a webhook trigger when a document is uploaded
2. Calling the backend to extract text and generate embeddings
3. AI-generating tags based on document content
4. Updating the document status to "completed"
5. Sending a success/failure response

## Prerequisites
- n8n running on `http://localhost:5678` (already running in Docker)
- Backend API running on `http://localhost:8000`
- Ollama with llama3.1:8b model downloaded

## Step 1: Access n8n

1. Open your browser and go to: `http://localhost:5678`
2. **First time setup**: You'll be asked to create an account
   - Enter your email (e.g., `admin@boq.local`)
   - Set a password (e.g., `admin123`)
   - Complete the setup wizard
3. **Subsequent logins**: Use the email and password you created

## Step 2: Import the Workflow

1. In n8n, click **"Workflows"** in the left sidebar
2. Click **"Add workflow"** (+ button)
3. Click the **"..."** menu (top right) → **"Import from File"**
4. Select the file: `C:\WORK\BOQ\n8n-workflows\pdf-auto-processing.json`
5. Click **"Save"** (top right)

## Step 3: Configure the Workflow

### Node 1: Webhook - Document Upload
- **Already configured** with path: `boq-document-upload`
- **Webhook URL**: `http://localhost:5678/webhook/boq-document-upload`
- This receives POST requests with:
  ```json
  {
    "document_id": 123,
    "token": "JWT_TOKEN"
  }
  ```

### Node 2: Process Document
- **HTTP Request** to: `http://host.docker.internal:8000/ai/documents/process/{document_id}`
- Extracts text, creates embeddings, generates tags
- Timeout: 5 minutes (300000ms)

### Node 3: Update Document Tags
- **HTTP Request** to update tags in database
- Uses tags returned from processing step

### Node 4: Mark as Completed
- **HTTP Request** to set status to "completed"

### Node 5: Respond - Success
- Sends success response back to backend

### Error Handling:
- If processing fails, status set to "failed"
- Error response sent back

## Step 4: Activate the Workflow

1. In the workflow editor, toggle the **"Active"** switch (top right) to **ON**
2. You should see: **"Workflow activated successfully"**

## Step 5: Enable n8n Processing in Backend

Add this to your `.env` file (or set as environment variable):

```env
USE_N8N_PROCESSING=true
N8N_WEBHOOK_URL=http://localhost:5678/webhook/boq-document-upload
```

Restart your backend:
```bash
cd C:\WORK\BOQ\be
python main.py
```

## Step 6: Test the Workflow

### Method 1: Upload via Frontend
1. Go to AI Assistant in your BOQ app
2. Upload a PDF file
3. Watch the n8n dashboard for workflow execution
4. Check document status updates in real-time

### Method 2: Test via API (Postman/curl)
```bash
curl -X POST http://localhost:8000/ai/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@path/to/your/document.pdf" \
  -F "auto_process=true" \
  -F "extract_tags=true"
```

### Method 3: Manual Webhook Test in n8n
1. Go to the workflow in n8n
2. Click **"Webhook - Document Upload"** node
3. Click **"Listen for Test Event"**
4. Send a test request:
```bash
curl -X POST http://localhost:5678/webhook/boq-document-upload \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "token": "YOUR_JWT_TOKEN"
  }'
```

## Monitoring

### View Workflow Executions
1. In n8n, click **"Executions"** in left sidebar
2. See all workflow runs with success/failure status
3. Click any execution to see detailed logs

### View Processing Status
- Check backend logs for processing messages
- Query document status via API:
```bash
GET http://localhost:8000/ai/documents/{document_id}
```

## Troubleshooting

### Issue: Webhook not receiving requests
**Solution**:
- Verify n8n is running: `docker ps | findstr n8n`
- Check workflow is activated (green toggle)
- Verify `N8N_WEBHOOK_URL` in backend .env

### Issue: Processing takes too long / times out
**Solution**:
- Check Ollama is running: `ollama list`
- Verify model downloaded: `llama3.1:8b` should appear
- Increase timeout in "Process Document" node (currently 5 min)

### Issue: "host.docker.internal not found"
**Solution**:
- On Windows with Docker Desktop, this should work automatically
- Alternative: Replace `host.docker.internal` with your machine's IP address

### Issue: Authentication errors
**Solution**:
- Verify JWT token is valid and not expired
- Check Authorization header format: `Bearer YOUR_TOKEN`
- Ensure user has permissions to upload documents

## Switching Between n8n and Direct Processing

### Use n8n (Recommended for production):
```env
USE_N8N_PROCESSING=true
```
**Pros**: Better monitoring, retry logic, workflow visibility, async processing

### Use Direct Processing:
```env
USE_N8N_PROCESSING=false
```
**Pros**: Simpler, no n8n dependency, faster for small documents

## Advanced: Extending the Workflow

You can enhance this workflow by adding nodes for:
- **Email notifications** when processing completes
- **Slack/Teams** alerts for failed processing
- **Scheduled cleanup** of old documents
- **Webhook notifications** to frontend via WebSockets
- **Custom tag categorization** rules
- **Integration with external APIs** (Dropbox, Google Drive, etc.)

To add nodes:
1. Click the **"+"** button between nodes
2. Search for the node type (Email, Slack, HTTP Request, etc.)
3. Configure the node
4. Connect it to the workflow
5. Save and test

## Next Steps

Once the basic workflow is working, you can:
1. Create additional workflows for scheduled tasks
2. Add notifications when documents are processed
3. Build approval workflows for sensitive documents
4. Integrate with external storage (S3, Azure Blob, etc.)
5. Create document classification pipelines

---

**Need help?** Check n8n logs: `docker logs boq-n8n -f`
