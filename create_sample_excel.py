#!/usr/bin/env python3
"""
Script to create a sample Excel file for testing the ERP Device Processor
"""

import pandas as pd
from pathlib import Path

def create_sample_excel():
    """Create a sample Excel file with test device data"""
    
    # Sample device data
    sample_data = [
        {"Reg No": "KCA 123A", "Customer": "John Doe"},
        {"Reg No": "KCB 456B", "Customer": "Jane Smith"},
        {"Reg No": "KCC 789C", "Customer": "Bob Johnson"},
        {"Reg No": "KCD 012D", "Customer": "Alice Brown"},
        {"Reg No": "KCE 345E", "Customer": "Charlie Wilson"},
        {"Reg No": "KCF 678F", "Customer": "Diana Davis"},
        {"Reg No": "KCG 901G", "Customer": "Edward Miller"},
        {"Reg No": "KCH 234H", "Customer": "Fiona Garcia"},
        {"Reg No": "KCI 567I", "Customer": "George Martinez"},
        {"Reg No": "KCJ 890J", "Customer": "Helen Rodriguez"}
    ]
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Create output directory
    output_dir = Path.home() / "Desktop" / "ERP DATA"
    output_dir.mkdir(exist_ok=True)
    
    # Save sample file
    sample_file_path = output_dir / "sample_devices.xlsx"
    df.to_excel(sample_file_path, index=False)
    
    print(f"✅ Sample Excel file created: {sample_file_path}")
    print(f"📊 Contains {len(sample_data)} sample devices")
    print("\nFile contents:")
    print(df.to_string(index=False))
    print(f"\n💡 You can use this file to test the ERP Device Processor")
    
    return sample_file_path

if __name__ == "__main__":
    try:
        create_sample_excel()
    except Exception as e:
        print(f"❌ Error creating sample file: {e}")
        print("Make sure you have pandas and openpyxl installed:")
        print("  pip install pandas openpyxl")