import os
import pandas as pd
import re
import time
import logging
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, session, send_file, send_from_directory, render_template
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv, set_key
import threading
import queue
import zipfile
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

socketio = SocketIO(app, cors_allowed_origins="*")

# Setup desktop output directory
desktop_path = Path.home() / "Desktop"
output_dir = desktop_path / "ERP DATA"
output_dir.mkdir(exist_ok=True)

# Setup logging with custom handler for real-time logs
class SocketIOHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        socketio.emit('log_message', {'message': log_entry}, namespace='/')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(output_dir / 'device_processing.log'),
        SocketIOHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables for processing state
processing_queue = queue.Queue()
is_processing = False
current_processor = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

class DeviceProcessor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.page = None
        self.browser = None
        self.playwright = None
        self.results = {
            'no_cert': [],
            'not_found': [],
            'expired': [],
            'valid_paid': [],
            'valid_not_paid': []
        }
        self.file_mapping = {
            'no_cert': 'No_cert_devices.xlsx',
            'not_found': 'Not_found_devices.xlsx',
            'expired': 'Expired_devices.xlsx',
            'valid_paid': 'Valid_paid_devices.xlsx',
            'valid_not_paid': 'Valid_not_paid.xlsx'
        }
        self.total_devices = 0
        self.processed_devices = 0
    
    def emit_progress(self, message, progress=None):
        """Emit progress updates to the frontend"""
        data = {'message': message}
        if progress is not None:
            data['progress'] = progress
        socketio.emit('processing_progress', data, namespace='/')
    
    def clean_reg_number(self, reg_no):
        """Clean registration number - optimized with single regex pattern"""
        if not reg_no:
            return ""
        
        original_reg_no = str(reg_no).upper().strip()
        logger.info(f"Processing: '{original_reg_no}'")
        
        pattern = r'^([A-Z]+)\s*(\d+)([A-Z]?).*?$'
        match = re.match(pattern, original_reg_no)
        
        if match:
            letters, numbers, final_letter = match.groups()
            result = f"{letters} {numbers}{final_letter}".strip()
            logger.info(f"Cleaned: '{original_reg_no}' -> '{result}'")
            return result
        
        logger.warning(f"Could not parse: '{original_reg_no}' - returning as is")
        return original_reg_no.strip()
    
    def safe_interact(self, selector, action="click", value="", timeout=5000, retries=3):
        """Unified safe interaction method with better error handling"""
        for attempt in range(retries):
            try:
                if action == "wait_for_element":
                    self.page.wait_for_selector(selector, timeout=timeout)
                    return True
                
                # Wait for element to exist first
                self.page.wait_for_selector(selector, timeout=timeout)
                
                if action == "click":
                    element = self.page.locator(selector)
                    element.click(timeout=timeout)
                elif action == "fill":
                    element = self.page.locator(selector)
                    element.clear()
                    if value:
                        element.fill(value)
                elif action == "dblclick":
                    element = self.page.locator(selector)
                    element.dblclick(timeout=timeout)
                elif action == "get_text":
                    element = self.page.locator(selector)
                    return element.text_content(timeout=timeout) or ""
                elif action == "get_value":
                    element = self.page.locator(selector)
                    return element.input_value(timeout=timeout) or ""
                elif action == "count":
                    return self.page.locator(selector).count()
                
                return True
                
            except PlaywrightTimeoutError as e:
                logger.warning(f"{action} attempt {attempt + 1} timeout for {selector}: {e}")
                if attempt < retries - 1:
                    time.sleep(1)
                else:
                    if action in ["get_text", "get_value"]:
                        return ""
                    elif action == "count":
                        return 0
                    return False
            except Exception as e:
                logger.warning(f"{action} attempt {attempt + 1} failed for {selector}: {e}")
                if attempt < retries - 1:
                    time.sleep(0.5)
                else:
                    if action in ["get_text", "get_value"]:
                        return ""
                    elif action == "count":
                        return 0
                    return False
        return False
    
    def find_column(self, df, possible_names):
        """Generic column finder"""
        for col in df.columns:
            if col.lower().strip() in possible_names:
                return col
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(name in col_lower for name in possible_names):
                return col
        return None
    
    def save_to_excel(self, filename, data_list):
        """Batch save to Excel with column alignment and output directory"""
        if not data_list:
            logger.info(f"No data to save for {filename}")
            return
        
        filename = output_dir / filename
        logger.info(f"Attempting to save {len(data_list)} records to {filename}")
        
        try:
            df_new = pd.DataFrame(data_list)
            
            try:
                df_existing = pd.read_excel(filename)
                # Align columns
                missing_cols = set(df_new.columns) - set(df_existing.columns)
                for col in missing_cols:
                    df_existing[col] = pd.NA
                missing_cols = set(df_existing.columns) - set(df_new.columns)
                for col in missing_cols:
                    df_new[col] = pd.NA
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            except FileNotFoundError:
                df_combined = df_new
            
            df_combined.to_excel(filename, index=False)
            logger.info(f"Successfully saved {len(data_list)} records to {filename}")
        except Exception as e:
            logger.error(f"Error saving to {filename}: {e}")
            raise
    
    def navigate_to_tracker_summary(self):
        """Navigate to tracker summary page with better error handling"""
        try:
            logger.info("Navigating to tracker summary page")
            self.page.goto("https://erpke.trailmycar.com/AnchorERP/fused/tracking/summary", wait_until="networkidle")
            time.sleep(1)
            
            # Clear default values
            self.safe_interact("#trackerListContent\\:j_idt88_input", "fill", "")
            self.safe_interact("#trackerListContent\\:branchCombo_input", "fill", "")
            
            logger.info("Successfully navigated to tracker summary")
            return True
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    def search_device_in_tracker(self, cleaned_reg):
        """Search for device in tracker summary with improved detection"""
        try:
            logger.info(f"Searching for device: {cleaned_reg}")
            
            # Clear and fill search field
            self.safe_interact("#trackerListContent\\:j_idt76", "fill", "")
            time.sleep(0.3)
            self.safe_interact("#trackerListContent\\:j_idt76", "fill", cleaned_reg)
            
            # Click search button
            self.safe_interact("#trackerListContent\\:go", "click")
            
            # Wait for loading to complete
            time.sleep(2)
            
            # Wait for any loading indicators to disappear
            try:
                self.page.wait_for_selector(".ui-datatable-loading", state="hidden", timeout=5000)
            except:
                pass
            
            time.sleep(1)
            
            # Check if scrollable body exists and has content
            scrollable_body_selector = "#trackerListContent\\:listTable > div.ui-datatable-scrollable-body"
            
            if not self.safe_interact(scrollable_body_selector, "wait_for_element", timeout=3000):
                logger.info("Scrollable body not found - device not found")
                return False
            
            # Count rows in the data table
            row_count = self.safe_interact("#trackerListContent\\:listTable_data > tr", "count")
            logger.info(f"Found {row_count} rows in search results")
            
            if row_count == 0:
                logger.info("No table rows found - device not found")
                return False
            
            # Check if first row has actual data
            try:
                first_cell_text = self.safe_interact("#trackerListContent\\:listTable_data > tr:first-child > td:first-child", "get_text")
                
                if not first_cell_text or not first_cell_text.strip():
                    logger.info("First row is empty - device not found")
                    return False
                
                # Check for common "no data" messages
                no_data_phrases = ["no data", "not found", "no records", "no results", "not available", "--", "null"]
                if any(phrase in first_cell_text.lower().strip() for phrase in no_data_phrases):
                    logger.info(f"No data message found: '{first_cell_text}' - device not found")
                    return False
                
                if len(first_cell_text.strip()) < 2:
                    logger.info(f"First cell too short to be valid data: '{first_cell_text}' - device not found")
                    return False
                
                logger.info(f"Valid search result found: '{first_cell_text.strip()}'")
                return True
                
            except Exception as e:
                logger.info(f"Could not read first cell - assuming device not found: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return False
    
    def open_device_details(self):
        """Open device details by double-clicking first row"""
        try:
            logger.info("Opening device details")
            
            # Double click the first row
            self.safe_interact("#trackerListContent\\:listTable_data > tr:first-child", "dblclick")
            
            # Wait for the device details page to load
            time.sleep(2)
            
            # Check if device details form loaded
            if self.safe_interact("#trackerEditForm\\:j_idt71\\:j_idt75", "wait_for_element", timeout=5000):
                logger.info("Device details page opened successfully")
                return True
            else:
                logger.warning("Device details page did not load")
                return False
                
        except Exception as e:
            logger.error(f"Error opening device details: {e}")
            return False
    
    def extract_device_info(self):
        """Extract basic device information from device details page"""
        try:
            device_info = {
                'client_name': self.safe_interact("#trackerEditForm\\:j_idt71\\:j_idt75", "get_value"),
                'phone_no': self.safe_interact("#trackerEditForm\\:j_idt71\\:j_idt79", "get_value"),
                'device_number': self.safe_interact("#trackerEditForm\\:j_idt71\\:j_idt84", "get_value")
            }
            
            logger.info(f"Extracted device info: {device_info}")
            return device_info
            
        except Exception as e:
            logger.error(f"Error extracting device info: {e}")
            return {
                'client_name': '',
                'phone_no': '',
                'device_number': ''
            }
    
    def check_expiry_date_field(self):
        """Check if expiry date field has value"""
        try:
            expiry_value = self.safe_interact("#trackerEditForm\\:j_idt71\\:j_idt121_input", "get_value")
            
            if not expiry_value or not expiry_value.strip():
                logger.info("No expiry date found - device has no certificate")
                return False
            
            logger.info(f"Expiry date found: {expiry_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking expiry date field: {e}")
            return False
    
    def open_certification_details(self):
        """Click on Certification Details tab"""
        try:
            logger.info("Opening certification details tab")
            
            # Click certification details tab
            self.safe_interact("#trackerEditForm\\:j_idt71 > ul > li:nth-child(6)", "click")
            time.sleep(1)
            
            # Check if certification table is visible
            cert_table_selector = "#trackerEditForm\\:j_idt71\\:certlistTable > div.ui-datatable-scrollable-body"
            
            if self.safe_interact(cert_table_selector, "wait_for_element", timeout=3000):
                logger.info("Certification details opened successfully")
                return True
            else:
                logger.warning("Certification table not found")
                return False
                
        except Exception as e:
            logger.error(f"Error opening certification details: {e}")
            return False
    
    def open_certificate_page(self):
        """Click first certificate row to open certificate page"""
        try:
            logger.info("Opening certificate page")
            
            # Click the first certificate row
            cert_link_selector = "#trackerEditForm\\:j_idt71\\:certlistTable_data > tr.ui-widget-content.ui-datatable-even > td:nth-child(1) > a"
            self.safe_interact(cert_link_selector, "click")
            
            # Wait for certificate page to load
            time.sleep(2)
            
            # Check if certificate form loaded
            if self.safe_interact("#certificateEditForm\\:certTab\\:newExpriryDateVal_input", "wait_for_element", timeout=5000):
                logger.info("Certificate page opened successfully")
                return True
            else:
                logger.warning("Certificate page did not load")
                return False
                
        except Exception as e:
            logger.error(f"Error opening certificate page: {e}")
            return False
    
    def get_certificate_expiry_date(self):
        """Get expiry date from certificate page"""
        try:
            expiry_date_str = self.safe_interact("#certificateEditForm\\:certTab\\:newExpriryDateVal_input", "get_value")
            
            if not expiry_date_str:
                logger.warning("No expiry date found on certificate page")
                return None
            
            # Parse date
            expiry_date = self.parse_date(expiry_date_str)
            logger.info(f"Certificate expiry date: {expiry_date_str} -> {expiry_date}")
            
            return expiry_date, expiry_date_str
            
        except Exception as e:
            logger.error(f"Error getting certificate expiry date: {e}")
            return None, None
    
    def get_paid_amount_from_certificate(self):
        """Get paid amount from certificate page"""
        try:
            paid_amount_text = self.safe_interact("#certificateEditForm\\:certTab\\:j_idt169", "get_text")
            
            if not paid_amount_text:
                logger.info("No paid amount text found")
                return 0.0
            
            # Extract numeric value
            cleaned = re.sub(r'[^\d.-]', '', paid_amount_text.strip())
            paid_amount = float(cleaned) if cleaned else 0.0
            
            logger.info(f"Paid amount from certificate: {paid_amount}")
            return paid_amount
            
        except Exception as e:
            logger.error(f"Error getting paid amount: {e}")
            return 0.0
    
    def check_paybill_logs(self, device_number):
        """Check payment logs for device number"""
        try:
            logger.info(f"Checking payment logs for device: {device_number}")
            
            # Navigate to paybill logs
            self.page.goto("https://erpke.trailmycar.com/AnchorERP/fused/finance/paybillLogs", wait_until="networkidle")
            time.sleep(1)
            
            # Clear from date
            self.safe_interact("#paybillForm\\:j_idt72 > tbody > tr:nth-child(1) > td:nth-child(2)", "fill", "")
            
            # Enter device number in search
            self.safe_interact("#paybillForm\\:j_idt69 > tbody > tr:nth-child(1) > td:nth-child(2)", "fill", device_number)
            
            # Click find button
            self.safe_interact("#paybillForm\\:go > span.ui-button-text.ui-c", "click")
            
            # Wait for loading
            time.sleep(2)
            
            # Check if results table has data
            scrollable_body_selector = "#paybillForm\\:listTable > div.ui-datatable-scrollable-body"
            
            if not self.safe_interact(scrollable_body_selector, "wait_for_element", timeout=3000):
                logger.info("No payment logs found")
                return 0.0
            
            row_count = self.safe_interact("#paybillForm\\:listTable_data > tr", "count")
            
            if row_count == 0:
                logger.info("No payment log entries found")
                return 0.0
            
            # Click first row to highlight it
            self.safe_interact("#paybillForm\\:listTable_data > tr:first-child", "click")
            time.sleep(0.5)
            
            # Extract amount from 6th column
            amount_text = self.safe_interact("#paybillForm\\:listTable_data > tr > td:nth-child(6)", "get_text")
            
            if amount_text:
                cleaned = re.sub(r'[^\d.-]', '', amount_text.strip())
                amount = float(cleaned) if cleaned else 0.0
                logger.info(f"Payment log amount: {amount}")
                return amount
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error checking payment logs: {e}")
            return 0.0
    
    def check_receipts(self, client_name):
        """Check receipts for client name"""
        try:
            logger.info(f"Checking receipts for client: {client_name}")
            
            # Navigate to receipts
            self.page.goto("https://erpke.trailmycar.com/AnchorERP/fused/finance/receipts", wait_until="networkidle")
            time.sleep(1)
            
            # Click list button
            self.safe_interact("#receiptContentForm\\:list_b > span.ui-button-text.ui-c", "click")
            time.sleep(1)
            
            # Clear from date and cost center
            self.safe_interact("#receiptListContent\\:j_idt79_input", "fill", "")
            self.safe_interact("#receiptListContent\\:branchCombo_input", "fill", "")
            
            # Enter client name in search
            self.safe_interact("#receiptListContent\\:j_idt76", "fill", client_name)
            
            # Click find button
            self.safe_interact("#receiptListContent\\:go > span.ui-button-text.ui-c", "click")
            
            # Wait for loading
            time.sleep(2)
            
            # Check if results have data
            row_count = self.safe_interact("#receiptListContent\\:listTable_data > tr", "count")
            
            if row_count == 0:
                logger.info("No receipts found")
                return 0.0
            
            # Click first row to highlight it
            self.safe_interact("#receiptListContent\\:listTable_data > tr:first-child", "click")
            time.sleep(0.5)
            
            # Extract amount from 10th column
            amount_text = self.safe_interact("#receiptListContent\\:listTable_data > tr.ui-widget-content.ui-datatable-even.ui-datatable-selectable.ui-state-highlight > td:nth-child(10)", "get_text")
            
            if amount_text:
                cleaned = re.sub(r'[^\d.-]', '', amount_text.strip())
                amount = float(cleaned) if cleaned else 0.0
                logger.info(f"Receipt amount: {amount}")
                return amount
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error checking receipts: {e}")
            return 0.0
    
    def parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str or not date_str.strip():
            return None
        
        formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        return None
    
    def process_single_device(self, reg_no, customer, index):
        """Process a single device following the exact workflow specified"""
        try:
            cleaned_reg = self.clean_reg_number(reg_no)
            logger.info(f"\n--- Processing {index + 1}/{self.total_devices}: {reg_no} -> {cleaned_reg} ---")
            
            # Update progress
            progress = ((index) / self.total_devices) * 100
            self.emit_progress(f"Processing {index + 1}/{self.total_devices}: {cleaned_reg}", progress)
            
            # Step 1: Navigate to tracker summary
            if not self.navigate_to_tracker_summary():
                logger.error("Failed to navigate to tracker summary")
                return False
            
            # Step 2: Search for device
            if not self.search_device_in_tracker(cleaned_reg):
                logger.info(f"Device NOT FOUND: {cleaned_reg}")
                self.results['not_found'].append({
                    'Reg No': reg_no,
                    'Customer': customer
                })
                self.save_to_excel(self.file_mapping['not_found'], [self.results['not_found'][-1]])
                return True
            
            # Step 3: Open device details
            if not self.open_device_details():
                logger.warning(f"Could not open device details for {cleaned_reg}")
                self.results['not_found'].append({
                    'Reg No': reg_no,
                    'Customer': customer
                })
                self.save_to_excel(self.file_mapping['not_found'], [self.results['not_found'][-1]])
                return True
            
            # Step 4: Extract device information
            device_info = self.extract_device_info()
            
            # Step 5: Check if expiry date field has value
            if not self.check_expiry_date_field():
                logger.info("No certificate found")
                self.results['no_cert'].append({
                    'Client Name': device_info['client_name'],
                    'Phone No': device_info['phone_no'],
                    'Device Number': device_info['device_number']
                })
                self.save_to_excel(self.file_mapping['no_cert'], [self.results['no_cert'][-1]])
                return True
            
            # Step 6: Open certification details
            if not self.open_certification_details():
                logger.error("Failed to open certification details")
                return False
            
            # Step 7: Open certificate page
            if not self.open_certificate_page():
                logger.error("Failed to open certificate page")
                return False
            
            # Step 8: Get certificate expiry date
            expiry_date, expiry_date_str = self.get_certificate_expiry_date()
            
            if not expiry_date:
                logger.warning("Could not get expiry date from certificate")
                return False
            
            # Step 9: Check if expired
            if expiry_date <= datetime.now():
                logger.info(f"Device EXPIRED: {expiry_date_str}")
                self.results['expired'].append({
                    'Client Name': device_info['client_name'],
                    'Phone No': device_info['phone_no'],
                    'Device Number': device_info['device_number'],
                    'Expiry Date': expiry_date_str
                })
                self.save_to_excel(self.file_mapping['expired'], [self.results['expired'][-1]])
                return True
            
            # Step 10: Check paid amount on certificate
            paid_amount = self.get_paid_amount_from_certificate()
            
            if paid_amount > 0:
                logger.info(f"Device VALID and PAID: Amount = {paid_amount}")
                self.results['valid_paid'].append({
                    'Client Name': device_info['client_name'],
                    'Phone No': device_info['phone_no'],
                    'Device Number': device_info['device_number'],
                    'Expiry Date': expiry_date_str,
                    'Paid Amount': paid_amount
                })
                self.save_to_excel(self.file_mapping['valid_paid'], [self.results['valid_paid'][-1]])
                return True
            
            # Step 11: Check payment logs
            payment_amount = self.check_paybill_logs(device_info['device_number'])
            
            if payment_amount > 0:
                logger.info(f"Device VALID and PAID (from logs): Amount = {payment_amount}")
                self.results['valid_paid'].append({
                    'Client Name': device_info['client_name'],
                    'Phone No': device_info['phone_no'],
                    'Device Number': device_info['device_number'],
                    'Expiry Date': expiry_date_str,
                    'Paid Amount': payment_amount
                })
                self.save_to_excel(self.file_mapping['valid_paid'], [self.results['valid_paid'][-1]])
                return True
            
            # Step 12: Check receipts
            receipt_amount = self.check_receipts(device_info['client_name'])
            
            if receipt_amount > 0:
                logger.info(f"Device VALID and PAID (from receipts): Amount = {receipt_amount}")
                self.results['valid_paid'].append({
                    'Client Name': device_info['client_name'],
                    'Phone No': device_info['phone_no'],
                    'Device Number': device_info['device_number'],
                    'Expiry Date': expiry_date_str,
                    'Paid Amount': receipt_amount
                })
                self.save_to_excel(self.file_mapping['valid_paid'], [self.results['valid_paid'][-1]])
                return True
            
            # Step 13: No payment found - valid but not paid
            logger.info("Device VALID but NOT PAID")
            self.results['valid_not_paid'].append({
                'Client Name': device_info['client_name'],
                'Phone No': device_info['phone_no'],
                'Device Number': device_info['device_number'],
                'Expiry Date': expiry_date_str
            })
            self.save_to_excel(self.file_mapping['valid_not_paid'], [self.results['valid_not_paid'][-1]])
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing device {reg_no}: {e}")
            return False
    
    def login_erp(self):
        """Login to the ERP system"""
        logger.info("Logging in to ERP...")
        self.emit_progress("Logging in to ERP system...")
        
        try:
            self.page.goto("https://erpke.trailmycar.com/AnchorERP/fused/login", wait_until="networkidle")
            
            self.safe_interact("#username", "fill", self.username)
            self.safe_interact("#password", "fill", self.password)
            
            # Click login and wait for navigation
            with self.page.expect_navigation(timeout=10000):
                self.safe_interact("#loginBtn > span", "click")
            
            # Submit cost center form
            self.safe_interact("#costCenterForm\\:orgSubmit > span", "click", timeout=5000)
            time.sleep(1)
            
            # Verify login success
            expected_url = "https://erpke.trailmycar.com/AnchorERP/fused/index?execution=e2s1"
            self.page.wait_for_url(expected_url, timeout=10000)
            
            logger.info("ERP Login successful")
            self.emit_progress("ERP login successful")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.emit_progress(f"Login failed: {e}")
            return False
    
    def start_browser(self):
        """Start browser and login"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False, devtools=False)
            self.page = self.browser.new_page()
            
            return self.login_erp()
            
        except Exception as e:
            logger.error(f"Browser startup failed: {e}")
            return False
    
    def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    def process_excel_file(self, excel_path):
        """Process the uploaded Excel file"""
        try:
            self.emit_progress("Reading Excel file...")
            df = pd.read_excel(excel_path)
            logger.info(f"Loaded {len(df)} rows")
            
            # Find relevant columns
            reg_column = self.find_column(df, ['reg no', 'number plate', 'device name', 'registration', 'device'])
            customer_column = self.find_column(df, ['customer', 'client', 'name', 'owner'])
            
            if not reg_column:
                raise ValueError("Registration column not found in Excel file")
            
            logger.info(f"Using columns - Reg: {reg_column}, Customer: {customer_column}")
            
            # Filter out empty registration numbers
            valid_rows = df[df[reg_column].notna() & (df[reg_column].astype(str).str.strip() != "")]
            self.total_devices = len(valid_rows)
            
            self.emit_progress(f"Found {self.total_devices} devices to process")
            
            # Process each device sequentially
            for index, row in valid_rows.iterrows():
                reg_no = row[reg_column]
                customer = row[customer_column] if customer_column else ""
                
                success = self.process_single_device(reg_no, customer, self.processed_devices)
                
                if not success:
                    logger.error(f"Failed to process device {reg_no}")
                
                self.processed_devices += 1
                
                # Small delay between devices
                time.sleep(0.5)
            
            # Final progress update
            self.emit_progress("Processing complete!", 100)
            
            logger.info("Processing complete!")
            logger.info("Final results:")
            for category, count in {k: len(v) for k, v in self.results.items()}.items():
                if count > 0:
                    logger.info(f"- {category}: {count} devices")
            
            # Emit final results
            socketio.emit('processing_complete', {
                'results': {k: len(v) for k, v in self.results.items()},
                'message': 'Processing completed successfully!'
            }, namespace='/')
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            self.emit_progress(f"Error: {str(e)}")
            socketio.emit('processing_error', {'error': str(e)}, namespace='/')
            raise

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle login requests"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    session['logged_in'] = True
    session['username'] = username
    session['password'] = password
    
    logger.info(f"User logged in: {username}")
    return jsonify({'message': 'Login successful', 'username': username})

@app.route('/logout', methods=['POST'])
def logout():
    """Handle logout requests"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle Excel file uploads and start processing"""
    global is_processing, current_processor
    
    if is_processing:
        return jsonify({'error': 'Processing already in progress'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Only Excel files are allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_path = output_dir / f"uploads_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        upload_path.parent.mkdir(exist_ok=True)
        file.save(upload_path)
        
        is_processing = True
        username = session.get('username')
        password = session.get('password')
        
        def process_in_background():
            global is_processing, current_processor
            try:
                current_processor = DeviceProcessor(username, password)
                if current_processor.start_browser():
                    current_processor.process_excel_file(upload_path)
                else:
                    socketio.emit('processing_error', {'error': 'Failed to start browser or login'}, namespace='/')
            except Exception as e:
                logger.error(f"Background processing error: {e}")
                socketio.emit('processing_error', {'error': str(e)}, namespace='/')
            finally:
                if current_processor:
                    current_processor.close_browser()
                is_processing = False
                current_processor = None
        
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'File uploaded successfully, processing started'})
        
    except Exception as e:
        is_processing = False
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status')
@login_required
def get_status():
    """Get current processing status"""
    return jsonify({
        'is_processing': is_processing,
        'processed_devices': current_processor.processed_devices if current_processor else 0,
        'total_devices': current_processor.total_devices if current_processor else 0
    })

@app.route('/files')
@login_required
def list_files():
    """List files in the output directory"""
    try:
        files = []
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'download_url': f'/download/{file_path.name}'
                })
        
        return jsonify({
            'files': files,
            'output_directory': str(output_dir)
        })
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    """Download a file from the output directory"""
    try:
        return send_from_directory(output_dir, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/download-all')
@login_required
def download_all():
    """Download all output files as a zip"""
    try:
        zip_path = output_dir / f"all_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in output_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.xlsx', '.log']:
                    zipf.write(file_path, file_path.name)
        
        return send_file(zip_path, as_attachment=True, download_name="erp_data_export.zip")
    except Exception as e:
        logger.error(f"Zip download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete-file', methods=['POST'])
@login_required
def delete_file():
    """Delete a file from the output directory"""
    try:
        data = request.get_json()
        file_name = data.get('fileName')
        
        if not file_name:
            return jsonify({'error': 'File name is required'}), 400
        
        # Sanitize file name to prevent path traversal
        file_name = Path(file_name).name
        file_path = output_dir / file_name
        
        # Check if file exists
        if not file_path.exists():
            return jsonify({'error': f'File {file_name} not found'}), 404
        
        # Delete the file
        file_path.unlink()
        
        return jsonify({'success': True, 'message': f'File {file_name} deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500

@app.route('/credentials', methods=['GET'])
@login_required
def get_credentials():
    """Get current credentials from .env"""
    load_dotenv()
    return jsonify({
        'username': os.getenv('ERP_USERNAME', ''),
        'password': '***' if os.getenv('ERP_PASSWORD') else ''
    })

@app.route('/update-credentials', methods=['POST'])
@login_required
def update_credentials():
    """Update credentials in .env file"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        env_path = Path('.env')
        set_key(env_path, 'ERP_USERNAME', username)
        set_key(env_path, 'ERP_PASSWORD', password)
        
        session['username'] = username
        session['password'] = password
        
        logger.info("Credentials updated successfully")
        return jsonify({'message': 'Credentials updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating credentials: {e}")
        return jsonify({'error': str(e)}), 500

# SocketIO events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected to WebSocket')
    emit('connected', {'message': 'Connected to real-time logs'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from WebSocket')

if __name__ == '__main__':
    load_dotenv()
    output_dir.mkdir(exist_ok=True)
    
    logger.info(f"Starting ERP Device Processor Web Application")
    logger.info(f"Output directory: {output_dir}")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)