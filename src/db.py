import sqlite3
from pathlib import Path
import pandas as pd

def save_tables(tables: dict[str,pd.DataFrame], db_path: Path):
    db_path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        for name, df in tables.items():
            df.to_sql(name,con,if_exists="replace",index=False)
