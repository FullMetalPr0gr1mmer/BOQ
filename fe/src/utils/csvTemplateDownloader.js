/**
 * Reusable CSV Template Downloader Utility
 *
 * This utility provides functions to generate and download CSV template files
 * with predefined headers for various upload functionalities across the application.
 */

/**
 * Downloads a CSV file with the specified headers
 *
 * @param {Array<string>} headers - Array of column headers for the CSV
 * @param {string} filename - Name of the file to download (without .csv extension)
 * @param {Array<Array<string>>} sampleRows - Optional sample rows to include in the template
 */
export function downloadCSVTemplate(headers, filename = 'template', sampleRows = []) {
  // Create CSV content
  let csvContent = headers.join(',') + '\n';

  // Add sample rows if provided
  if (sampleRows && sampleRows.length > 0) {
    sampleRows.forEach(row => {
      csvContent += row.join(',') + '\n';
    });
  }

  // Create blob
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

  // Create download link
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  link.style.visibility = 'hidden';

  // Trigger download
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up
  URL.revokeObjectURL(url);
}

/**
 * Site Upload CSV Template
 * Headers: LinkID, InterfaceName, SiteIPA, SiteIPB
 */
export function downloadSiteUploadTemplate() {
  const headers = ['LinkID', 'InterfaceName', 'SiteIPA', 'SiteIPB'];
  const sampleRows = [
    ['JIZ0243-JIZ0169', 'eth0', '10.0.0.1', '10.0.0.2'],
    ['ABC1234-XYZ5678', 'eth1', '192.168.1.1', '192.168.1.2']
  ];

  downloadCSVTemplate(headers, 'site_upload_template', sampleRows);
}

/**
 * Inventory Upload CSV Template
 * Headers: All inventory-related fields
 */
export function downloadInventoryUploadTemplate() {
  const headers = [
    'Site Id',
    'Site Name',
    'Slot Id',
    'Port Id',
    'Status',
    'Company ID',
    'Mnemonic',
    'CLEI Code',
    'Part No',
    'Software Part No',
    'Factory ID',
    'Serial No',
    'Date ID',
    'Manufactured Date',
    'Customer Field',
    'License Points Consumed',
    'Alarm Status',
    'Aggregated Alarm Status'
  ];

  const sampleRows = [
    ['SITE001', 'Main Site', '1', '1', 'Active', 'COMP001', 'MNE001', 'CLEI001', 'PN001', 'SWN001', 'FAC001', 'SER001', 'DATE001', '2024-01-01', 'Custom', '100', 'OK', 'OK']
  ];

  downloadCSVTemplate(headers, 'inventory_upload_template', sampleRows);
}

/**
 * BOQ Reference Upload CSV Template
 * Headers: linkid, InterfaceName, SiteIPA, SiteIPB
 */
export function downloadBOQReferenceUploadTemplate() {
  const headers = ['linkid', 'InterfaceName', 'SiteIPA', 'SiteIPB'];
  const sampleRows = [
    ['JIZ0243-JIZ0169', 'eth0', '10.0.0.1', '10.0.0.2'],
    ['ABC1234-XYZ5678', 'eth1', '192.168.1.1', '192.168.1.2']
  ];

  downloadCSVTemplate(headers, 'boq_reference_upload_template', sampleRows);
}

/**
 * Dismantling Upload CSV Template
 * Headers: nokia_link_id, nec_dismantling_link_id, no_of_dismantling, comments
 */
export function downloadDismantlingUploadTemplate() {
  const headers = ['nokia_link_id', 'nec_dismantling_link_id', 'no_of_dismantling', 'comments'];
  const sampleRows = [
    ['NOKIA001', 'NEC001', '5', 'Sample dismantling record'],
    ['NOKIA002', 'NEC002', '3', 'Another example']
  ];

  downloadCSVTemplate(headers, 'dismantling_upload_template', sampleRows);
}

/**
 * LLD Upload CSV Template
 * Headers: All LLD-related fields
 */
export function downloadLLDUploadTemplate() {
  const headers = [
    'link ID',
    'Action',
    'FON',
    'configuration',
    'Distance',
    'Scope',
    'NE',
    'FE',
    'link catergory',
    'Link status',
    'COMMENTS',
    'Dismanting link ID',
    'Band',
    'T-band CS',
    'NE Ant size',
    'FE Ant Size',
    'SD NE',
    'SD FE',
    'ODU TYPE',
    'Updated SB',
    'Region',
    'LOSR approval',
    'initial LB',
    'FLB'
  ];

  const sampleRows = [
    ['LINK001', 'Install', 'FON123', 'Config1', '10km', 'Scope1', 'NE001', 'FE001', 'Category1', 'Active', 'Sample comment', 'DIS001', 'Band1', 'CS1', '0.6m', '0.6m', 'SD1', 'SD2', 'ODU1', 'SB1', 'Region1', 'Approved', 'LB1', 'FLB1']
  ];

  downloadCSVTemplate(headers, 'lld_upload_template', sampleRows);
}

/**
 * RAN LLD (RAN BOQ Generation) Upload CSV Template
 * Headers: Site ID, New Antennas, Total Antennas, Technical BoQ, Technical BoQ Key
 */
export function downloadRANLLDUploadTemplate() {
  const headers = ['Site ID', 'New Antennas', 'Total Antennas', 'Technical BoQ', 'Technical BoQ Key'];
  const sampleRows = [
    ['SITE001', '5', '10', 'Technical BOQ 1', 'KEY001'],
    ['SITE002', '3', '8', 'Technical BOQ 2', 'KEY002']
  ];

  downloadCSVTemplate(headers, 'ran_lld_upload_template', sampleRows);
}

/**
 * RAN Inventory Upload CSV Template
 * Headers: MRBTS, Site ID, identificationCode, userLabel, serialNumber, Duplicate, Duplicate remarks
 */
export function downloadRANInventoryUploadTemplate() {
  const headers = [
    'MRBTS',
    'Site ID',
    'identificationCode',
    'userLabel',
    'serialNumber',
    'Duplicate',
    'Duplicate remarks'
  ];

  const sampleRows = [
    ['MRBTS001', 'SITE001', 'ID001', 'Label 1', 'SN001', 'false', ''],
    ['MRBTS002', 'SITE002', 'ID002', 'Label 2', 'SN002', 'true', 'Duplicate found']
  ];

  downloadCSVTemplate(headers, 'ran_inventory_upload_template', sampleRows);
}

/**
 * RAN Antenna Serials Upload CSV Template
 * Headers: MRBTS, Antenna Model, Serial Number
 */
export function downloadRANAntennaSerialsUploadTemplate() {
  const headers = ['MRBTS', 'Antenna Model', 'Serial Number'];
  const sampleRows = [
    ['MRBTS001', 'Model A', 'ANT-SN-001'],
    ['MRBTS002', 'Model B', 'ANT-SN-002']
  ];

  downloadCSVTemplate(headers, 'ran_antenna_serials_upload_template', sampleRows);
}

/**
 * Generic CSV template downloader
 * Use this for custom templates with specific headers
 *
 * @example
 * downloadCustomCSVTemplate(
 *   ['Header1', 'Header2', 'Header3'],
 *   'my_custom_template',
 *   [['value1', 'value2', 'value3']]
 * );
 */
export function downloadCustomCSVTemplate(headers, filename, sampleRows = []) {
  downloadCSVTemplate(headers, filename, sampleRows);
}

// Export all template types for easy access
export const CSV_TEMPLATES = {
  SITE_UPLOAD: downloadSiteUploadTemplate,
  INVENTORY_UPLOAD: downloadInventoryUploadTemplate,
  BOQ_REFERENCE_UPLOAD: downloadBOQReferenceUploadTemplate,
  DISMANTLING_UPLOAD: downloadDismantlingUploadTemplate,
  LLD_UPLOAD: downloadLLDUploadTemplate,
  RAN_LLD_UPLOAD: downloadRANLLDUploadTemplate,
  RAN_INVENTORY_UPLOAD: downloadRANInventoryUploadTemplate,
  RAN_ANTENNA_SERIALS_UPLOAD: downloadRANAntennaSerialsUploadTemplate
};
