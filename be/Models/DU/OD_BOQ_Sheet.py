"""
BOQ CSV Parser with Multi-Level Headers
Efficiently parses CSV with complex headers and stores in SQL Server
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, create_model
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, MetaData, Table
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import re


class BOQHeaderMapping:
    """Manages the multi-level header structure"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.level1_headers = []  # Row 1: Main categories
        self.level2_headers = []  # Row 4: Column codes (OD_SRAN, OD_5G, etc.)
        self.column_mapping = {}  # Maps combined headers to original positions
        
    def parse_headers(self) -> Dict[str, Any]:
        """Parse the multi-level headers from the CSV"""
        # Read first 15 rows to capture all header information
        df_headers = pd.read_csv(self.csv_path, nrows=15, header=None)
        
        # Row 0 (index 0): Main categories
        level1 = df_headers.iloc[0].fillna('')
        
        # Find the row with actual column codes (contains CAT, BU, Description, OD_SRAN, OD_5G, etc.)
        header_row_idx = None
        for idx in range(len(df_headers)):
            row_str = ' '.join(df_headers.iloc[idx].astype(str))
            if 'CAT' in row_str and 'Description' in row_str and 'OD_SRAN' in row_str:
                header_row_idx = idx
                break
        
        if header_row_idx is None:
            raise ValueError("Could not find the main header row with column codes")
        
        # Extract level 2 headers (the actual column codes)
        level2_raw = df_headers.iloc[header_row_idx]
        
        # Clean and process headers
        self.level1_headers = [str(h).strip() if pd.notna(h) else '' for h in level1]
        self.level2_headers = [self._clean_header(h) for h in level2_raw]
        
        # Create mapping: combine level1 and level2 headers
        self.column_mapping = self._create_column_mapping()
        
        return {
            'level1': self.level1_headers,
            'level2': self.level2_headers,
            'mapping': self.column_mapping,
            'header_row_idx': header_row_idx
        }
    
    def _clean_header(self, header: Any) -> str:
        """Clean header text by removing newlines and extra spaces"""
        if pd.isna(header):
            return ''
        header_str = str(header)
        # Remove newlines and multiple spaces
        cleaned = re.sub(r'\s+', ' ', header_str.replace('\n', ' ')).strip()
        return cleaned
    
    def _create_column_mapping(self) -> Dict[str, str]:
        """Create mapping between combined headers and database column names"""
        mapping = {}
        current_level1 = ''
        
        for idx, (l1, l2) in enumerate(zip(self.level1_headers, self.level2_headers)):
            # Update current main category if not empty
            if l1:
                current_level1 = l1
            
            # Create column name
            if l2:
                if current_level1 and l2 not in ['CAT', 'BU', 'Cat.', 'Description', 'UoM']:
                    # Combine level1 and level2 for quantity columns
                    col_name = f"{self._slugify(current_level1)}_{self._slugify(l2)}"
                else:
                    col_name = self._slugify(l2)
                
                mapping[idx] = {
                    'column_name': col_name,
                    'level1_header': current_level1,
                    'level2_header': l2,
                    'original_index': idx
                }
        
        return mapping
    
    def _slugify(self, text: str) -> str:
        """Convert text to valid database column name"""
        if not text:
            return f"col_{np.random.randint(1000, 9999)}"
        
        # Remove special characters and replace spaces with underscores
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        slug = slug.strip('_')
        
        # Ensure it doesn't start with a number
        if slug and slug[0].isdigit():
            slug = f"col_{slug}"
        
        return slug or f"col_{np.random.randint(1000, 9999)}"


class BOQDataLoader:
    """Loads and processes the BOQ data"""
    
    def __init__(self, csv_path: str, header_mapping: BOQHeaderMapping):
        self.csv_path = csv_path
        self.header_mapping = header_mapping
        self.df = None
        
    def load_data(self, skip_rows: int) -> pd.DataFrame:
        """Load the CSV data, skipping header rows"""
        # Read CSV, skipping the header rows
        self.df = pd.read_csv(
            self.csv_path,
            skiprows=skip_rows + 1,  # Skip headers + 1 for the actual data to start
            header=None
        )
        
        # Assign column names based on mapping
        new_columns = []
        for idx in range(len(self.df.columns)):
            if idx in self.header_mapping.column_mapping:
                new_columns.append(
                    self.header_mapping.column_mapping[idx]['column_name']
                )
            else:
                new_columns.append(f'col_{idx}')
        
        self.df.columns = new_columns
        
        # Remove empty rows
        self.df = self.df.dropna(how='all')
        
        # Clean data: remove rows that are actually part of headers (like "Site Qty" row)
        # You can add more specific filters here
        
        return self.df
    
    def get_data_dict(self) -> List[Dict[str, Any]]:
        """Convert DataFrame to list of dictionaries for Pydantic validation"""
        return self.df.to_dict('records')


def create_dynamic_pydantic_model(column_mapping: Dict[str, Dict]) -> type[BaseModel]:
    """
    Dynamically create a Pydantic model based on the column mapping
    """
    fields = {}
    
    for col_info in column_mapping.values():
        col_name = col_info['column_name']
        level2_header = col_info['level2_header']
        
        # Determine field type based on column name
        if col_name in ['cat', 'bu', 'cat_', 'description', 'uom']:
            fields[col_name] = (Optional[str], Field(None, description=level2_header))
        else:
            # Quantity columns - can be int, float, or None
            fields[col_name] = (Optional[float], Field(None, description=level2_header))
    
    # Create the model
    BOQItemModel = create_model('BOQItem', **fields)
    
    return BOQItemModel


def create_sqlalchemy_table(
    engine,
    table_name: str,
    column_mapping: Dict[str, Dict]
) -> Table:
    """
    Create SQLAlchemy table based on column mapping
    """
    metadata = MetaData()
    
    columns = [
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('created_at', String, default=str(datetime.now())),
    ]
    
    for col_info in column_mapping.values():
        col_name = col_info['column_name']
        level2_header = col_info['level2_header']
        
        if col_name in ['cat', 'bu', 'cat_', 'description', 'uom']:
            columns.append(Column(col_name, Text, comment=level2_header))
        else:
            columns.append(Column(col_name, Float, nullable=True, comment=level2_header))
    
    table = Table(table_name, metadata, *columns)
    metadata.create_all(engine)
    
    return table


class BOQProcessor:
    """Main processor for BOQ CSV to SQL Server"""
    
    def __init__(
        self,
        csv_path: str,
        connection_string: str,
        table_name: str = 'boq_data'
    ):
        self.csv_path = csv_path
        self.connection_string = connection_string
        self.table_name = table_name
        self.engine = create_engine(connection_string)
        
        # Initialize components
        self.header_mapping = BOQHeaderMapping(csv_path)
        self.data_loader = None
        self.pydantic_model = None
        self.table = None
        
    def process(self):
        """Main processing pipeline"""
        print("Step 1: Parsing headers...")
        header_info = self.header_mapping.parse_headers()
        print(f"Found {len(header_info['mapping'])} columns")
        
        print("\nStep 2: Loading data...")
        self.data_loader = BOQDataLoader(self.csv_path, self.header_mapping)
        df = self.data_loader.load_data(skip_rows=header_info['header_row_idx'])
        print(f"Loaded {len(df)} rows")
        
        print("\nStep 3: Creating Pydantic model...")
        self.pydantic_model = create_dynamic_pydantic_model(
            self.header_mapping.column_mapping
        )
        print("Pydantic model created")
        
        print("\nStep 4: Creating SQL table...")
        self.table = create_sqlalchemy_table(
            self.engine,
            self.table_name,
            self.header_mapping.column_mapping
        )
        print(f"Table '{self.table_name}' created")
        
        print("\nStep 5: Validating and inserting data...")
        data_dicts = self.data_loader.get_data_dict()
        validated_data = []
        
        for idx, row in enumerate(data_dicts):
            try:
                validated_item = self.pydantic_model(**row)
                validated_data.append(validated_item.dict())
            except Exception as e:
                print(f"Warning: Row {idx} validation failed: {e}")
                continue
        
        print(f"Validated {len(validated_data)} rows")
        
        # Insert data
        if validated_data:
            with self.engine.connect() as conn:
                conn.execute(self.table.insert(), validated_data)
                conn.commit()
            print(f"Successfully inserted {len(validated_data)} rows")
        
        return {
            'rows_processed': len(data_dicts),
            'rows_inserted': len(validated_data),
            'table_name': self.table_name,
            'columns': list(self.header_mapping.column_mapping.keys())
        }
    
    def get_column_info(self) -> pd.DataFrame:
        """Get a summary of all columns and their mappings"""
        if not self.header_mapping.column_mapping:
            self.header_mapping.parse_headers()
        
        info = []
        for col_info in self.header_mapping.column_mapping.values():
            info.append({
                'DB Column Name': col_info['column_name'],
                'Level 1 Header': col_info['level1_header'],
                'Level 2 Header': col_info['level2_header'],
                'Original Index': col_info['original_index']
            })
        
        return pd.DataFrame(info)


# Example usage
if __name__ == "__main__":
    # SQL Server connection string
    # Format: mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server
    connection_string = "mssql+pyodbc://username:password@localhost/database?driver=ODBC+Driver+17+for+SQL+Server"
    
    # Initialize processor
    processor = BOQProcessor(
        csv_path="OD_BOQ_sheet.csv",
        connection_string=connection_string,
        table_name="boq_items"
    )
    
    # Get column information first (useful for verification)
    print("Column Mapping Preview:")
    print(processor.get_column_info().head(10))
    
    # Process and load data
    result = processor.process()
    print("\nProcessing complete!")
    print(result)