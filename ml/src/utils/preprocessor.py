"""ML utils — feature preprocessing (encoding, scaling, imputation)."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
import joblib
import os


FORMAT_MAP   = {'test': 0.25, 'odi': 0.5, 't20': 0.75, 't10': 1.0, 'other': 0.6}
CATEGORY_MAP = {'international': 1.0, 'franchise': 0.5, 'domestic': 0.3}
PITCH_MAP    = {'batting': 1.0, 'balanced': 0.5, 'bowling': 0.0}


def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """Encode categorical features into numeric values."""
    df = df.copy()
    df['format_enc']   = df['format'].map(FORMAT_MAP).fillna(0.6)
    df['category_enc'] = df['category'].map(CATEGORY_MAP).fillna(0.5)
    df['pitch_enc']    = df.get('venue__pitch_type', pd.Series('balanced', index=df.index)).map(PITCH_MAP).fillna(0.5)
    df['toss_bat']     = (df.get('toss_decision', '') == 'bat').astype(int)
    return df


def build_feature_matrix(df: pd.DataFrame, feature_cols: list) -> np.ndarray:
    """Build clean numpy matrix from DataFrame, imputing missing values."""
    imputer = SimpleImputer(strategy='median')
    X = df[feature_cols].values
    X = imputer.fit_transform(X)
    return X


def scale_features(X_train: np.ndarray, X_test: np.ndarray = None):
    """Fit StandardScaler on training data; optionally transform test data."""
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    if X_test is not None:
        return X_train_scaled, scaler.transform(X_test), scaler
    return X_train_scaled, scaler


def save_preprocessor(scaler: StandardScaler, path: str, version: str = 'v1.0'):
    """Persist fitted scaler to disk."""
    os.makedirs(os.path.join(path, version), exist_ok=True)
    joblib.dump(scaler, os.path.join(path, version, 'scaler.pkl'))


def load_preprocessor(path: str, version: str = 'v1.0') -> StandardScaler:
    """Load persisted scaler from disk."""
    return joblib.load(os.path.join(path, version, 'scaler.pkl'))
