import argparse
from .generator import generate_dataset, export_dataset
from .config import EXPORT_DIR, DB_PATH
from .db import save_tables
from .validation import validate_tables

def main():
    parser=argparse.ArgumentParser(description="Generate FactoryMind synthetic factory data")
    parser.add_argument("--scale",choices=["starter","full"],default="starter")
    parser.add_argument("--seed",type=int,default=20261022)
    args=parser.parse_args()
    tables=generate_dataset(args.scale,args.seed)
    manifest=export_dataset(tables,EXPORT_DIR)
    save_tables(tables,DB_PATH)
    report=validate_tables(tables)
    report.to_csv(EXPORT_DIR/"validation_report.csv",index=False)
    print(f"Generated {args.scale} dataset in {EXPORT_DIR}")
    print(f"All master-data checks passed: {report.passed.all()}")
    for name,meta in manifest["tables"].items():
        print(f"{name}: {meta['rows']} rows")
if __name__=="__main__": main()
