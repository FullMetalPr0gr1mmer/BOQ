# CSV Template Downloader Utility

## Overview

The `csvTemplateDownloader.js` utility provides reusable functions to generate and download CSV template files with predefined headers for various upload functionalities across the application.

## Features

- ✅ Generate CSV files with custom headers
- ✅ Include sample rows in templates
- ✅ Pre-configured templates for common uploads (Sites, Inventory)
- ✅ Fully reusable across the application
- ✅ Browser-compatible download mechanism

## Installation

The utility is located at `fe/src/utils/csvTemplateDownloader.js`. Import the functions you need:

```javascript
import {
  downloadSiteUploadTemplate,
  downloadInventoryUploadTemplate,
  downloadCustomCSVTemplate
} from '../utils/csvTemplateDownloader';
```

## Usage

### Pre-configured Templates

#### 1. Site Upload Template

Downloads a CSV template for uploading sites with link data.

**Headers:** `LinkID, InterfaceName, SiteIPA, SiteIPB`

```javascript
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';

// In your component
<button onClick={downloadSiteUploadTemplate}>
  Download Site Template
</button>
```

**Generated file:** `site_upload_template.csv`

**Sample rows included:**
```csv
LinkID,InterfaceName,SiteIPA,SiteIPB
JIZ0243-JIZ0169,eth0,10.0.0.1,10.0.0.2
ABC1234-XYZ5678,eth1,192.168.1.1,192.168.1.2
```

---

#### 2. Inventory Upload Template

Downloads a CSV template for uploading inventory data.

**Headers:** 18 inventory-related fields including Site Id, Site Name, Slot Id, etc.

```javascript
import { downloadInventoryUploadTemplate } from '../utils/csvTemplateDownloader';

// In your component
<button onClick={downloadInventoryUploadTemplate}>
  Download Inventory Template
</button>
```

**Generated file:** `inventory_upload_template.csv`

---

### Custom Templates

Create your own CSV template with custom headers and sample data.

```javascript
import { downloadCustomCSVTemplate } from '../utils/csvTemplateDownloader';

// Define your headers
const headers = ['Name', 'Email', 'Phone', 'Department'];

// Define sample rows (optional)
const sampleRows = [
  ['John Doe', 'john@example.com', '555-1234', 'Engineering'],
  ['Jane Smith', 'jane@example.com', '555-5678', 'Sales']
];

// Download the template
downloadCustomCSVTemplate(headers, 'employee_template', sampleRows);
```

**Generated file:** `employee_template.csv`

---

### Low-Level API

Use the core `downloadCSVTemplate` function for maximum flexibility:

```javascript
import { downloadCSVTemplate } from '../utils/csvTemplateDownloader';

downloadCSVTemplate(
  ['Column1', 'Column2', 'Column3'],  // headers
  'my_template',                       // filename (without .csv)
  [['value1', 'value2', 'value3']]    // sample rows (optional)
);
```

---

## Complete Example

Here's a complete example of integrating the CSV template downloader into a help modal:

```javascript
import React from 'react';
import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
import '../css/shared/DownloadButton.css';

function SiteHelp() {
  return (
    <div>
      <h3>CSV Upload Guidelines</h3>
      <p>Your CSV file must have these columns:</p>
      <ul>
        <li>LinkID</li>
        <li>InterfaceName</li>
        <li>SiteIPA</li>
        <li>SiteIPB</li>
      </ul>

      <button
        className="btn-download-template"
        onClick={downloadSiteUploadTemplate}
      >
        📥 Download CSV Template
      </button>

      <p>Example: JIZ0243-JIZ0169, eth0, 10.0.0.1, 10.0.0.2</p>
    </div>
  );
}
```

---

## API Reference

### `downloadSiteUploadTemplate()`

Pre-configured template for site uploads.

- **Parameters:** None
- **Returns:** void (triggers download)
- **Filename:** `site_upload_template.csv`
- **Headers:** LinkID, InterfaceName, SiteIPA, SiteIPB

---

### `downloadInventoryUploadTemplate()`

Pre-configured template for inventory uploads.

- **Parameters:** None
- **Returns:** void (triggers download)
- **Filename:** `inventory_upload_template.csv`
- **Headers:** 18 inventory fields

---

### `downloadCustomCSVTemplate(headers, filename, sampleRows)`

Create a custom CSV template.

- **Parameters:**
  - `headers` (Array<string>): Column headers
  - `filename` (string): File name without .csv extension
  - `sampleRows` (Array<Array<string>>, optional): Sample data rows
- **Returns:** void (triggers download)

---

### `downloadCSVTemplate(headers, filename, sampleRows)`

Low-level function for CSV generation.

- **Parameters:**
  - `headers` (Array<string>): Column headers
  - `filename` (string, default: 'template'): File name without .csv
  - `sampleRows` (Array<Array<string>>, optional): Sample data rows
- **Returns:** void (triggers download)

---

## Styling

Use the pre-built CSS classes from `css/shared/DownloadButton.css`:

```javascript
import '../css/shared/DownloadButton.css';

// Default style
<button className="btn-download-template" onClick={downloadTemplate}>
  📥 Download Template
</button>

// Small variant
<button className="btn-download-template btn-small" onClick={downloadTemplate}>
  📥 Download
</button>

// Success/green variant
<button className="btn-download-template btn-success" onClick={downloadTemplate}>
  📥 Download Template
</button>
```

---

## Adding New Templates

To add a new pre-configured template:

1. Open `csvTemplateDownloader.js`
2. Create a new function following the naming pattern:

```javascript
export function downloadYourFeatureUploadTemplate() {
  const headers = ['Header1', 'Header2', 'Header3'];
  const sampleRows = [
    ['Sample1', 'Sample2', 'Sample3']
  ];

  downloadCSVTemplate(headers, 'your_feature_template', sampleRows);
}
```

3. Export it in the `CSV_TEMPLATES` object:

```javascript
export const CSV_TEMPLATES = {
  SITE_UPLOAD: downloadSiteUploadTemplate,
  INVENTORY_UPLOAD: downloadInventoryUploadTemplate,
  YOUR_FEATURE: downloadYourFeatureUploadTemplate  // Add this
};
```

4. Import and use it in your component:

```javascript
import { CSV_TEMPLATES } from '../utils/csvTemplateDownloader';

<button onClick={CSV_TEMPLATES.YOUR_FEATURE}>
  Download Template
</button>
```

---

## Browser Compatibility

This utility uses:
- `Blob` API (supported in all modern browsers)
- `URL.createObjectURL()` (supported in all modern browsers)
- Dynamic `<a>` element download (supported in all modern browsers)

**Minimum browser versions:**
- Chrome 20+
- Firefox 20+
- Safari 6+
- Edge (all versions)
- IE 10+ (with polyfill)

---

## Best Practices

1. **Always include sample rows** - Helps users understand the expected format
2. **Use descriptive filenames** - Make it clear what the template is for
3. **Match backend expectations** - Ensure headers match your API's CSV parser
4. **Provide clear instructions** - Add help text explaining how to use the template
5. **Test the template** - Download and test uploading the generated CSV

---

## Troubleshooting

### Template downloads but is empty
- Check that headers array is not empty
- Verify sampleRows is properly formatted as Array<Array<string>>

### Wrong headers in generated CSV
- Ensure headers match your backend's CSV parser exactly (case-sensitive)
- Check for extra whitespace in header strings

### Download doesn't work
- Check browser console for errors
- Verify the function is being called (add console.log)
- Ensure user interaction triggered the download (browser security)

---

## Examples in the Codebase

See these files for real-world examples:
- `fe/src/Components/Site.jsx` - Site upload template integration
- `fe/src/css/shared/DownloadButton.css` - Button styling

---

## Support

For questions or issues, please contact the development team or create an issue in the project repository.
