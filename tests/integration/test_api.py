import os
import time
import requests

API_BASE = "http://127.0.0.1:8000/api/v1"
RAW_FOLDER = os.path.join(os.getcwd(), "authorised_capital_changes", "data", "raw")

def test_api():
    print(f"--- Triggering Pipeline via API ---")
    print(f"Input folder: {RAW_FOLDER}")
    
    # 1. Start the run
    resp = requests.post(f"{API_BASE}/pipeline/run", json={"input_folder": RAW_FOLDER})
    resp.raise_for_status()
    data = resp.json()
    run_id = data["run_id"]
    print(f"Started run! ID: {run_id}")
    
    # 2. Poll for status
    while True:
        time.sleep(5)
        s_resp = requests.get(f"{API_BASE}/pipeline/status/{run_id}")
        if not s_resp.ok:
            print(f"Error polling status: {s_resp.text}")
            return
            
        s_data = s_resp.json()
        print(f"Status: {s_data['status']} | Completed stages: {len(s_data['completed_stages'])}")
        
        if s_data["status"] in ["completed", "failed", "partial"]:
            print(f"Pipeline finished with status: {s_data['status']}")
            break
            
    # 3. Fetch results
    if s_data["status"] == "completed":
        t_resp = requests.get(f"{API_BASE}/results/{run_id}/table")
        if t_resp.ok:
            t_data = t_resp.json()
            print("\n--- Final API Table Result ---")
            for idx, row in enumerate(t_data.get("capital_table", [])):
                safe_from = str(row['authorised_from']).replace('₹', 'Rs.') if row.get('authorised_from') else 'None'
                safe_to = str(row['authorised_to']).replace('₹', 'Rs.') if row.get('authorised_to') else 'None'
                print(f"Row {idx}: {row['meeting_date']} | {safe_from} -> {safe_to}")
            
            flags = t_data.get("flags", [])
            print(f"\nDiscrepancy Flags: {len(flags)}")
            for f in flags:
                print(f"- {f['flag_code']} (Row {f['row_number']}): {f['flag_message']}")
        else:
            print(f"Failed to fetch table: {t_resp.text}")

if __name__ == "__main__":
    test_api()
