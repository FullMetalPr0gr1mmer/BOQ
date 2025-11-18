# CSV Template Downloader - Usage Examples

Quick examples showing how to use the CSV template downloader in different parts of your application.

---

## Example 1: Simple Button in Any Component

```jsx
import React from 'react';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function MyComponent() {
  return (
    <button
      className="btn-download-template"
      onClick={downloadSiteUploadTemplate}
    >
      📥 Download CSV Template
    </button>
  );
}
```

---

## Example 2: Using the Reusable Button Component

```jsx
import React from 'react';
import CSVTemplateButton from './shared/CSVTemplateButton';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';

function MyComponent() {
  return (
    <CSVTemplateButton
      onDownload={downloadSiteUploadTemplate}
      label="Download Site Template"
    />
  );
}
```

---

## Example 3: In a Help Modal (Like Site.jsx)

```jsx
import React from 'react';
import HelpModal, { HelpText, CodeBlock } from './shared/HelpModal';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function MyComponent() {
  const helpSections = [
    {
      icon: '📁',
      title: 'CSV Upload Guidelines',
      content: (
        <>
          <HelpText>
            Your CSV file must contain the following columns:
          </HelpText>
          <CodeBlock items={['Column1', 'Column2', 'Column3']} />

          <div style={{ margin: '1rem 0' }}>
            <button
              className="btn-download-template"
              onClick={downloadSiteUploadTemplate}
              type="button"
            >
              📥 Download CSV Template
            </button>
          </div>

          <HelpText isNote>
            <strong>Note:</strong> Make sure to fill in all required fields.
          </HelpText>
        </>
      )
    }
  ];

  return <HelpModal sections={helpSections} />;
}
```

---

## Example 4: Creating a Custom Template

```jsx
import React from 'react';
import { downloadCustomCSVTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function EmployeeUpload() {
  const handleDownloadTemplate = () => {
    const headers = ['Name', 'Email', 'Phone', 'Department'];
    const sampleRows = [
      ['John Doe', 'john@example.com', '555-1234', 'Engineering'],
      ['Jane Smith', 'jane@example.com', '555-5678', 'Sales']
    ];

    downloadCustomCSVTemplate(headers, 'employee_template', sampleRows);
  };

  return (
    <button
      className="btn-download-template"
      onClick={handleDownloadTemplate}
    >
      📥 Download Employee Template
    </button>
  );
}
```

---

## Example 5: Multiple Template Options

```jsx
import React from 'react';
import { CSV_TEMPLATES } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function DownloadCenter() {
  return (
    <div>
      <h2>Download Templates</h2>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <button
          className="btn-download-template"
          onClick={CSV_TEMPLATES.SITE_UPLOAD}
        >
          📥 Site Upload Template
        </button>

        <button
          className="btn-download-template"
          onClick={CSV_TEMPLATES.INVENTORY_UPLOAD}
        >
          📥 Inventory Upload Template
        </button>
      </div>
    </div>
  );
}
```

---

## Example 6: With Success Message

```jsx
import React, { useState } from 'react';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function MyComponent() {
  const [message, setMessage] = useState('');

  const handleDownload = () => {
    downloadSiteUploadTemplate();
    setMessage('Template downloaded! Check your downloads folder.');
    setTimeout(() => setMessage(''), 3000);
  };

  return (
    <div>
      <button
        className="btn-download-template"
        onClick={handleDownload}
      >
        📥 Download Template
      </button>

      {message && (
        <div className="success-message">{message}</div>
      )}
    </div>
  );
}
```

---

## Example 7: Conditional Download Button

```jsx
import React from 'react';
import CSVTemplateButton from './shared/CSVTemplateButton';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';

function MyComponent({ userHasPermission }) {
  return (
    <div>
      {userHasPermission ? (
        <CSVTemplateButton
          onDownload={downloadSiteUploadTemplate}
          label="Download Template"
        />
      ) : (
        <p>You don't have permission to download templates.</p>
      )}
    </div>
  );
}
```

---

## Example 8: Inline Link Style

```jsx
import React from 'react';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';

function MyComponent() {
  return (
    <p>
      Need help? You can{' '}
      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          downloadSiteUploadTemplate();
        }}
        style={{ color: '#124191', textDecoration: 'underline', cursor: 'pointer' }}
      >
        download a CSV template
      </a>
      {' '}to see the required format.
    </p>
  );
}
```

---

## Example 9: Small Button Variant

```jsx
import React from 'react';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function CompactToolbar() {
  return (
    <button
      className="btn-download-template btn-small"
      onClick={downloadSiteUploadTemplate}
    >
      📥 Template
    </button>
  );
}
```

---

## Example 10: Success Variant (Green)

```jsx
import React from 'react';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function SuccessMessage() {
  return (
    <div>
      <h3>Upload Successful! ✅</h3>
      <p>Need to upload more? Download another template:</p>

      <button
        className="btn-download-template btn-success"
        onClick={downloadSiteUploadTemplate}
      >
        📥 Download Another Template
      </button>
    </div>
  );
}
```

---

## Quick Reference

### Available Template Functions
- `downloadSiteUploadTemplate()` - Site upload with link data
- `downloadInventoryUploadTemplate()` - Inventory upload
- `downloadCustomCSVTemplate(headers, filename, sampleRows)` - Custom template

### Available CSS Classes
- `btn-download-template` - Base class (required)
- `btn-small` - Smaller size variant
- `btn-success` - Green/success color variant

### Import Paths
```javascript
// Functions
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';

// Component
import CSVTemplateButton from './shared/CSVTemplateButton';

// Styles
import '../css/shared/DownloadButton.css';
```

---

## Need More Examples?

Check out these files in the codebase:
- `fe/src/Components/Site.jsx` - Real implementation in help modal
- `fe/src/utils/csvTemplateDownloader.md` - Full documentation
- `fe/src/Components/shared/CSVTemplateButton.jsx` - Reusable component
