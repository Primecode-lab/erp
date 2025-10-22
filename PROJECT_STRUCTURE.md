# ERP Device Processor - Project Structure

## 📁 **Complete File Structure**

```
ERP-Device-Processor/
├── 📄 app.py                    # Main Flask application
├── 📄 requirements.txt          # Python dependencies
├── 📄 README.md                 # Comprehensive documentation
├── 📄 PROJECT_STRUCTURE.md      # This file
├── 📄 test_setup.py            # Setup verification script
├── 📄 start_app.py             # Quick start launcher
├── 📄 create_sample_excel.py   # Sample data generator
├── 📄 .env                     # Environment variables (optional)
├── 📄 hello.txt                # Example file
└── 📁 templates/
    └── 📄 index.html           # Web interface
```

## 🚀 **Quick Start Options**

### Option 1: Automated Setup & Launch
```bash
python start_app.py
```
This script will:
- ✅ Check and install all dependencies
- ✅ Install Playwright browser
- ✅ Create output directories
- ✅ Launch the application

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install browser
playwright install chromium

# 3. Run application
python app.py
```

### Option 3: Test Setup First
```bash
# Verify everything is working
python test_setup.py

# Then start the app
python app.py
```

## 📊 **Testing & Sample Data**

### Create Sample Excel File
```bash
python create_sample_excel.py
```
This creates `~/Desktop/ERP DATA/sample_devices.xlsx` with test data.

## 🔧 **Configuration Options**

### Environment Variables (.env file)
```env
ERP_USERNAME=your_username
ERP_PASSWORD=your_password
```

### Application Settings
- **Port**: 5000 (configurable in app.py)
- **Output Directory**: `~/Desktop/ERP DATA/`
- **Max File Size**: 50MB
- **Browser**: Chromium (headless=False for visibility)

## 📋 **Application Features**

### ✅ **Core Processing**
- Sequential device processing
- Smart registration number cleaning
- Multiple payment source checking
- Automatic categorization into 5 groups

### ✅ **User Interface**
- Real-time progress tracking
- Live logging with WebSocket
- Drag & drop file upload
- Dark/Light theme toggle
- Responsive design

### ✅ **File Management**
- Individual Excel downloads
- Bulk ZIP download
- File deletion capability
- Automatic file organization

### ✅ **Error Handling**
- Network retry mechanisms
- Element detection fallbacks
- Browser crash recovery
- Data validation
- Comprehensive logging

## 🎯 **Processing Workflow**

Each device goes through these exact steps:

1. **🔍 Search Device** → Check tracker summary table
2. **📂 Open Details** → Double-click to access device info
3. **📝 Extract Info** → Get client name, phone, device number
4. **🏆 Check Certificate** → Look for expiry date field
5. **📅 Verify Expiry** → Compare with current date
6. **💰 Check Payments** → Certificate → Logs → Receipts
7. **📊 Categorize** → Save to appropriate Excel file

## 📁 **Output Files**

Generated in `~/Desktop/ERP DATA/`:

| File | Description |
|------|-------------|
| `Valid_paid_devices.xlsx` | ✅ Valid certificates + payment found |
| `Valid_not_paid.xlsx` | ⚠️ Valid certificates + no payment |
| `Expired_devices.xlsx` | ❌ Expired certificates |
| `No_cert_devices.xlsx` | 📋 No certificate found |
| `Not_found_devices.xlsx` | 🔍 Device not in system |
| `device_processing.log` | 📜 Complete processing log |

## 🛠 **Troubleshooting**

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **Login fails** | Verify ERP credentials, check connection |
| **Browser doesn't start** | Run `playwright install chromium` |
| **Files not saving** | Check desktop permissions, disk space |
| **Processing stops** | Check network, restart browser |
| **Dependencies missing** | Run `pip install -r requirements.txt` |

### Debug Mode
To enable detailed debugging:
```python
# In app.py, change:
socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

## 🔒 **Security Features**

- ✅ Session-based authentication
- ✅ Secure credential storage
- ✅ Path traversal protection
- ✅ File type validation
- ✅ Input sanitization
- ✅ CSRF protection

## 📈 **Performance Tips**

### Optimal Settings
- **Batch Size**: 100-500 devices per run
- **Network**: Stable broadband connection
- **Memory**: 8GB RAM recommended for large files
- **Browser**: Close other instances during processing

### Monitoring
- Watch real-time logs for progress
- Monitor system resources
- Check network stability
- Verify ERP system responsiveness

## 🔄 **Maintenance**

### Regular Updates
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update Playwright
playwright install chromium --force
```

### Log Management
- Logs auto-rotate at 100 entries
- Manual log clearing via UI
- Log files saved in output directory

## 🎉 **Success Indicators**

Application is working correctly when you see:

- ✅ All dependencies installed
- ✅ Browser launches successfully
- ✅ ERP login successful
- ✅ Real-time logs updating
- ✅ Progress bar advancing
- ✅ Excel files being created
- ✅ Processing completes without errors

## 📞 **Support Workflow**

1. **Check Logs** → Review real-time and file logs
2. **Run Tests** → Execute `python test_setup.py`
3. **Verify Files** → Ensure all required files present
4. **Check Network** → Confirm ERP system access
5. **Review Output** → Examine generated Excel files

---

**🎯 Ready to Process Devices!**

The application is now fully set up and ready for production use with your ERP system.