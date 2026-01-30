import os
import pandas as pd
import numpy as np
from glob import glob

# ==========================================
# CONFIGURATION
# ==========================================
DATASET_PATH = "Dataset V4" 
OUTPUT_PATH = "processed_data"
SAMPLING_RATE = 100    # 100 Hz
WINDOW_SECONDS = 2     # 2-second windows
STRIDE_SECONDS = 1     # 50% Overlap
WINDOW_SIZE = int(SAMPLING_RATE * WINDOW_SECONDS) # 200 samples
STRIDE_SIZE = int(SAMPLING_RATE * STRIDE_SECONDS) # 100 samples

# Define folder mapping
FALL_FOLDERS = ['Falls']
ADL_FOLDERS = ['Driving', 'Running', 'Stand Up', 'Walking']

def calculate_features(df):
    """
    Feature Engineering based on YOUR CSV headers:
    AccX, AccY, AccZ, Magnitude, GyroX, GyroY, GyroZ, Temperature, Altitude
    """
    
    # 1. ACCELERATION MAGNITUDE
    # Your CSV already has 'Magnitude', but let's recalculate it to be safe 
    # (or you can trust the column if you prefer).
    df['acc_mag'] = np.sqrt(df['AccX']**2 + df['AccY']**2 + df['AccZ']**2)

    # 2. GYROSCOPE MAGNITUDE
    if 'GyroX' in df.columns:
        df['gyro_mag'] = np.sqrt(df['GyroX']**2 + df['GyroY']**2 + df['GyroZ']**2)
    else:
        df['gyro_mag'] = 0.0

    # 3. JERK (Rate of change of acceleration)
    # Formula: (Acc_new - Acc_old) / dt
    dt = 1.0 / SAMPLING_RATE
    for axis in ['AccX', 'AccY', 'AccZ']:
        # Create 'Jerk_AccX', 'Jerk_AccY', etc.
        df[f'Jerk_{axis}'] = df[axis].diff().fillna(0) / dt

    # 4. ALTITUDE / PRESSURE
    # Your CSV has 'Altitude'. The paper uses "Pressure Delta".
    # "Altitude Delta" is mathematically equivalent for this purpose (change in height).
    if 'Altitude' not in df.columns:
        df['Altitude'] = 0.0
        
    return df

def create_windows(df, label):
    windows = []
    labels = []
    
    num_samples = len(df)
    
    if num_samples < WINDOW_SIZE:
        return [], []

    for start in range(0, num_samples - WINDOW_SIZE + 1, STRIDE_SIZE):
        end = start + WINDOW_SIZE
        window = df.iloc[start:end].copy()
        
        # 5. NORMALIZE ALTITUDE (Critical Step)
        # We don't care if you are at 100m or 2000m. We care if you DROP 1 meter.
        # So we subtract the first altitude reading of the window from all readings.
        alt_0 = window['Altitude'].iloc[0]
        window['Altitude_Delta'] = window['Altitude'] - alt_0
        
        # 6. SELECT FINAL FEATURES
        # We need exactly 12 columns for the TCT model logic
        # 3 Acc + 3 Gyro + 1 Alt + 2 Mags + 3 Jerks = 12 Features
        try:
            feature_cols = [
                'AccX', 'AccY', 'AccZ',           # 1-3
                'GyroX', 'GyroY', 'GyroZ',        # 4-6
                'Altitude_Delta',                 # 7
                'acc_mag', 'gyro_mag',            # 8-9
                'Jerk_AccX', 'Jerk_AccY', 'Jerk_AccZ' # 10-12
            ]
            windows.append(window[feature_cols].values)
            labels.append(label)
        except KeyError as e:
            print(f"Missing column in window: {e}")
            return [], []
            
    return windows, labels

def process_folder(folder_name, label):
    folder_path = os.path.join(DATASET_PATH, folder_name)
    # Recursively find CSVs in case there are subfolders
    csv_files = glob(os.path.join(folder_path, "**/*.csv"), recursive=True)
    
    print(f"Processing '{folder_name}': Found {len(csv_files)} files.")
    
    folder_windows = []
    folder_labels = []
    
    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path)
            
            # Sanity Check: Ensure headers match expected format
            if 'AccX' not in df.columns:
                # Some CSVs might have different headers, skip them or print warning
                print(f"  Skipping {os.path.basename(file_path)}: Header mismatch")
                continue
                
            df = calculate_features(df)
            wins, labs = create_windows(df, label)
            folder_windows.extend(wins)
            folder_labels.extend(labs)
        except Exception as e:
            print(f"  Error reading {os.path.basename(file_path)}: {e}")
            
    return folder_windows, folder_labels

def main():
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)
        
    all_X = []
    all_y = []

    # Process FALLS (Label = 1)
    for folder in FALL_FOLDERS:
        windows, labels = process_folder(folder, label=1)
        all_X.extend(windows)
        all_y.extend(labels)

    # Process ADL (Label = 0)
    for folder in ADL_FOLDERS:
        windows, labels = process_folder(folder, label=0)
        all_X.extend(windows)
        all_y.extend(labels)

    # Convert to Numpy
    X = np.array(all_X)
    y = np.array(all_y)

    print(f"\nProcessing Complete!")
    print(f"Final Data Shape: {X.shape}") 
    print(f"  (Should be: [Total_Windows, 200, 12])")
    print(f"Class Distribution: Falls={np.sum(y == 1)}, ADL={np.sum(y == 0)}")

    np.save(f"{OUTPUT_PATH}/X_data.npy", X)
    np.save(f"{OUTPUT_PATH}/y_data.npy", y)
    print(f"Saved to {OUTPUT_PATH}/")

if __name__ == "__main__":
    main()