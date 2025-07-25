# ERP Device Processor

A highly reliable web application for processing device data from Excel files through the ERP system. This application automates the process of checking device certificates, payment status, and categorizing devices into appropriate groups.

## Features

- **Sequential Processing**: Processes devices one by one following the exact workflow specified
- **Smart Error Handling**: Robust error handling with retries and fallback mechanisms
- **Real-time Progress**: Live progress updates and logging through WebSocket connections
- **Multiple Payment Sources**: Checks certificates, payment logs, and receipts for payment verification
- **Automatic Categorization**: Organizes devices into 5 categories:
  - Valid Paid Devices
  - Valid Not Paid Devices
  - Expired Devices
  - No Certificate Devices
  - Not Found Devices
- **File Management**: Download individual files or all results as a ZIP archive
- **Credentials Management**: Secure storage and update of ERP credentials

## Installation

1. **Clone or download the application files**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

4. **Create environment file (optional):**
   Create a `.env` file in the project root:
   ```
   ERP_USERNAME=your_erp_username
   ERP_PASSWORD=your_erp_password
   ```

## Usage

1. **Start the application:**
   ```bash
   python app.py
   ```

2. **Access the web interface:**
   Open your browser and go to `http://localhost:5000`

3. **Login:**
   - Enter your ERP credentials when prompted
   - Credentials can also be updated from the sidebar

4. **Upload Excel file:**
   - The Excel file should contain device registration numbers
   - Supported columns: "Reg No", "Number Plate", "Device Name", "Registration", "Device"
   - Optionally include customer/client information

5. **Start processing:**
   - Click "Start Processing" after uploading
   - Monitor progress through the real-time logs and progress bar
   - Do not close the browser during processing

6. **Download results:**
   - Individual Excel files for each category
   - Complete log file
   - ZIP archive with all files

## Processing Workflow

The application follows this exact sequence for each device:

1. **Navigate to Tracker Summary**
2. **Search for Device** using cleaned registration number
3. **Check if Device Exists** in the system
4. **Extract Device Information** (Client Name, Phone, Device Number)
5. **Check for Certificate** in expiry date field
6. **Open Certification Details** if certificate exists
7. **Access Certificate Page** to get expiry date
8. **Determine Status** based on expiry date:
   - If expired → Save to "Expired Devices"
   - If valid → Check payment sources
9. **Check Payment Sources** in order:
   - Certificate paid amount
   - Payment logs by device number
   - Receipts by client name
10. **Categorize Device** based on findings

## Output Files

The application creates Excel files in the `~/Desktop/ERP DATA/` directory:

- `Valid_paid_devices.xlsx` - Devices with valid certificates and payment found
- `Valid_not_paid.xlsx` - Devices with valid certificates but no payment found
- `Expired_devices.xlsx` - Devices with expired certificates
- `No_cert_devices.xlsx` - Devices without certificates
- `Not_found_devices.xlsx` - Devices not found in the system
- `device_processing.log` - Complete processing log

## Error Handling

- **Network Issues**: Automatic retries with exponential backoff
- **Element Not Found**: Multiple fallback selectors and wait strategies
- **Browser Crashes**: Automatic browser restart and session recovery
- **Data Validation**: Input validation and sanitization
- **File Conflicts**: Smart Excel file merging with column alignment

## System Requirements

- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large files)
- Stable internet connection
- Chrome/Chromium browser (installed automatically by Playwright)

## Troubleshooting

### Common Issues

1. **Login Fails:**
   - Verify ERP credentials
   - Check internet connection
   - Ensure ERP system is accessible

2. **Processing Stops:**
   - Check browser console for errors
   - Verify Excel file format
   - Ensure sufficient disk space

3. **Files Not Found:**
   - Check `~/Desktop/ERP DATA/` directory
   - Verify write permissions
   - Look for error messages in logs

### Performance Tips

- Process files with 100-500 devices at a time for optimal performance
- Close other browser instances during processing
- Ensure stable network connection
- Monitor system resources during large batch processing

## Security Features

- Session-based authentication
- Secure credential storage
- Path traversal protection
- File type validation
- Input sanitization

## Development Notes

The application is built with:
- **Backend**: Flask with SocketIO for real-time communication
- **Frontend**: Modern HTML5/CSS3/JavaScript with real-time updates
- **Automation**: Playwright for browser automation
- **Data Processing**: Pandas for Excel file handling

## Support

For issues or questions:
1. Check the real-time logs in the application
2. Review the processing log file
3. Verify system requirements
4. Check network connectivity

---

**Note**: This application requires access to the ERP system and valid credentials. Ensure you have the necessary permissions before running the processor.