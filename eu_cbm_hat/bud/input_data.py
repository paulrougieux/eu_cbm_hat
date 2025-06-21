from pathlib import Path
import pandas as pd
from typing import Union, Dict


class BudInputData:
    """
    A class that provides dictionary-like access to CSV files in a directory.
    
    Usage:
        input_data = InputData("scenarios/reference/input/csv/")
        df = input_data["inventory"]  # Loads inventory.csv as DataFrame
    """
    
    def __init__(self, parent):
        """
        Initialize InputData with the path to the CSV directory.
        
        Args:
            parent: bud object which has a parameter do the data directory,
            where a sub-path contains the directory containing CSV files.
        """
        self.bud = parent
        self.csv_directory = self.bud.data_dir / "input/csv"
        if not self.csv_directory.exists():
            raise FileNotFoundError(f"Directory not found: {self.csv_directory}")
        if not self.csv_directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.csv_directory}")
    
    def __getitem__(self, key: str) -> pd.DataFrame:
        """
        Load and return a CSV file as a pandas DataFrame.
        
        Args:
            key: Name of the CSV file (without .csv extension)
            
        Returns:
            pandas.DataFrame: The loaded CSV data
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            Exception: If there's an error reading the CSV file
        """
        csv_file = self.csv_directory / f"{key}.csv"
        if not csv_file.exists():
            available_files = [f.stem for f in self.csv_directory.glob("*.csv")]
            raise FileNotFoundError(
                f"CSV file '{key}.csv' not found in {self.csv_directory}. "
                f"Available files: {available_files}"
            )
        try:
            df = pd.read_csv(csv_file)
            return df
        except Exception as e:
            raise Exception(f"Error reading CSV file '{csv_file}': {str(e)}")
    
    def __contains__(self, key: str) -> bool:
        """
        Check if a CSV file exists in the directory.
        
        Args:
            key: Name of the CSV file (without .csv extension)
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        csv_file = self.csv_directory / f"{key}.csv"
        return csv_file.exists()
    
    def list_available_files(self) -> list:
        """
        List all available CSV files in the directory.
        
        Returns:
            list: List of available CSV file names (without .csv extension)
        """
        return [f.stem for f in self.csv_directory.glob("*.csv")]
    
    
    def get_file_info(self, key: str) -> dict:
        """
        Get information about a CSV file.
        
        Args:
            key: Name of the CSV file (without .csv extension)
            
        Returns:
            dict: Information about the file including size, modification time, etc.
        """
        csv_file = self.csv_directory / f"{key}.csv"
        
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file '{key}.csv' not found")
        
        stat = csv_file.stat()
        return {
            'file_path': str(csv_file),
            'size_bytes': stat.st_size,
            'modified_time': stat.st_mtime,
        }

