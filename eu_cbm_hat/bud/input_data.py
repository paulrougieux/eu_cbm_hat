"""Input data for a small self contained runner-type of object called a bud.
"""
import pandas as pd
from autopaths.auto_paths import AutoPaths


class BudInputData:
    """
    CSV files from a scenario "input/csv" directory used as input to CBM

    Examples
    --------
    >>> input_data = InputData("scenarios/reference/input/csv/")
    >>> df = input_data["inventory"]  # Loads inventory.csv as DataFrame
    """

    all_paths = """
    /input/csv/
    /input/csv/age_classes.csv
    /input/csv/classifiers.csv
    /input/csv/disturbance_types.csv
    /input/csv/events.csv
    /input/csv/inventory.csv
    /input/csv/transitions.csv
    /input/csv/growth_curves.csv
    """

    def __init__(self, parent):
        """
        Initialize InputData with the path to the CSV directory.

        Parameters
        ----------
        parent: bud object which has a parameter do the data directory,
            where a sub-path contains the directory containing CSV files.
        """
        self.parent = parent
        # pathlib.Path object (we would prefer to use pathlib)
        self.csv_directory = self.parent.data_dir / "input/csv"
        # AutoPaths object (for compatibility with runner.input_data)
        self.paths = AutoPaths(str(self.parent.data_dir), self.all_paths)
        # Verify the CSV directory exists
        if not self.csv_directory.exists():
            raise FileNotFoundError(f"Directory not found: {self.csv_directory}")

        if not self.csv_directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.csv_directory}")

    def __getitem__(self, key: str) -> pd.DataFrame:
        """
        Load and return a CSV file as a pandas DataFrame.

        Parameters
        ----------
        key : str
            Name of the CSV file (without .csv extension).

        Returns
        -------
        pandas.DataFrame
            The loaded CSV data.

        Raises
        ------
        FileNotFoundError
            If the CSV file doesn't exist.
        Exception
            If there's an error reading the CSV file.
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

        Parameters
        ----------
        key : str
            Name of the CSV file (without .csv extension).

        Returns
        -------
        bool
            True if the file exists, False otherwise.
        """
        csv_file = self.csv_directory / f"{key}.csv"
        return csv_file.exists()

    def list_available_files(self) -> list:
        """
        List all available CSV files in the directory.

        Returns
        -------
        list of str
            List of available CSV file names (without .csv extension).
        """
        return [f.stem for f in self.csv_directory.glob("*.csv")]

    def get_file_info(self, key: str) -> dict:
        """
        Get information about a CSV file.

        Parameters
        ----------
        key : str
            Name of the CSV file (without .csv extension).

        Returns
        -------
        dict
            Information about the file including size, modification time, etc.

        Raises
        ------
        FileNotFoundError
            If the CSV file doesn't exist.
        """
        csv_file = self.csv_directory / f"{key}.csv"

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file '{key}.csv' not found")

        stat = csv_file.stat()
        return {
            "file_path": str(csv_file),
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
        }
