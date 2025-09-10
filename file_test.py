import pandas as pd
import glob
import os


def create_master_predictions(folder_path, file_type="csv"):
    """
    Reads all weekly prediction files in a folder and combines them into a single master file.

    Parameters:
        folder_path (str): Path to the folder containing the weekly prediction files.
        file_type (str): "csv" (default) or "excel" depending on your file type.

    Returns:
        pd.DataFrame: The combined master DataFrame.
    """
    # Pattern to match all your weekly prediction files
    file_pattern = os.path.join(folder_path, f"Week_*_Predictions_Full_Season.{file_type}")

    # List all files matching the pattern
    all_files = glob.glob(file_pattern)

    # Sort files by week number
    all_files.sort(key=lambda x: int(x.split('Week_')[1].split('_')[0]))

    # Read and concatenate all files
    if file_type == "csv":
        df_list = [pd.read_csv(f) for f in all_files]
        master_df = pd.concat(df_list, ignore_index=True)
        master_df.to_csv(os.path.join(folder_path, "Master_Predictions_Full_Season.csv"), index=False)
    elif file_type in ["xls", "xlsx", "excel"]:
        df_list = [pd.read_excel(f) for f in all_files]
        master_df = pd.concat(df_list, ignore_index=True)
        master_df.to_excel(os.path.join(folder_path, "Master_Predictions_Full_Season.xlsx"), index=False)
    else:
        raise ValueError("file_type must be 'csv' or 'excel'")

    print(f"Master file created with {len(master_df)} rows.")
    return master_df

master_df = create_master_predictions("2025_Weekly_Predictions", file_type="csv")
