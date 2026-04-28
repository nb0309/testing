import os
import json
import pandas as pd
from datetime import datetime
from nvda_capture import NVDACapture
from classifier import AccessibilityClassifier
from llm_reasoner import LLMReasoner

class DatasetBuilder:
    def __init__(self, output_dir="output"):
        self.output_dir = os.path.join(os.path.dirname(__file__), output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.capturer = NVDACapture()
        self.classifier = AccessibilityClassifier()
        self.reasoner = LLMReasoner()
        
    def build_from_urls(self, urls: list, output_filename="accessibility_dataset.csv"):
        all_records = []
        
        print(f"Starting dataset generation for {len(urls)} URLs...")
        
        for url in urls:
            print(f"Processing: {url}")
            
            captured_data = []
            for mode in ["browse", "interactive"]:
                print(f"[{mode} mode] Capturing for {url}...")
                capture_result = self.capturer.capture(url, mode)
                
                if not capture_result.get("success"):
                    print(f"Failed to capture {url} in {mode} mode: {capture_result.get('error')}")
                    continue
                    
                data = capture_result.get("data", [])
                print(f"Successfully captured {len(data)} announcements from {url} in {mode} mode")
                
                for item in data:
                    item["capture_mode"] = mode
                
                captured_data.extend(data)
            
            if not captured_data:
                print(f"No data captured for {url} in any mode.")
                continue
                
            # 2. Classify output and build dataset rows
            for item in captured_data:
                index = item.get("index")
                role = item.get("role")
                name = item.get("name")
                announcement = item.get("announcement")
                html_snippet = item.get("html_snippet", "")
                
                classification = self.classifier.classify_announcement(role, name, html_snippet)
                capture_mode = item.get("capture_mode", "browse")
                
                print(f"Generating LLM reasoning for element index {index}...")
                reasoning = self.reasoner.generate_reasoning(
                    role, name, html_snippet, 
                    classification["is_accessible"], 
                    classification["wcag_violations"], 
                    classification["wcag_passes"]
                )
                
                record = {
                    "url": url,
                    "element_index": index,
                    "element_role": role,
                    "element_name": name,
                    "announcement": announcement,
                    "html_snippet": html_snippet,
                    "is_accessible": classification["is_accessible"],
                    "wcag_violations": classification["wcag_violations"],
                    "wcag_passes": classification["wcag_passes"],
                    "llm_reasoning": reasoning,
                    "capture_mode": capture_mode,
                    "timestamp": datetime.now().isoformat()
                }
                all_records.append(record)
                
        # 3. Save to CSV and JSONL
        csv_output_path = os.path.join(self.output_dir, output_filename)
        jsonl_output_path = os.path.join(self.output_dir, "fine_tuning_dataset.jsonl")
        
        if all_records:
            # Generate CSV
            df = pd.DataFrame(all_records)
            df.to_csv(csv_output_path, index=False)
            
            # Generate JSONL for SLM Fine-tuning
            with open(jsonl_output_path, "w", encoding="utf-8") as f:
                for r in all_records:
                    # Skip empty nodes for high-quality instruction data
                    if not r.get("html_snippet"): 
                        continue
                    
                    message_row = {
                        "messages": [
                            {
                                "role": "system", 
                                "content": "You are an accessibility auditor. Given a screen reader transcript and its HTML snippet, determine if it is accessible and identify applicable WCAG guidelines."
                            },
                            {
                                "role": "user",
                                "content": f"Transcript: {r['announcement']}\nHTML: {r['html_snippet']}"
                            },
                            {
                                "role": "assistant",
                                "content": f"<think>\n{r['llm_reasoning']}\n</think>\n\nAccessible: {r['is_accessible']}\nWCAG Violations: {r['wcag_violations']}\nWCAG Passes: {r['wcag_passes']}"
                            }
                        ]
                    }
                    f.write(json.dumps(message_row) + "\n")
            
            print(f"Dataset successfully saved to {csv_output_path} with {len(all_records)} records.")
            print(f"Fine-tuning JSONL successfully saved to {jsonl_output_path}.")
        else:
            print("No records were captured. Dataset not created.")
            
if __name__ == "__main__":
    # Example usage - add URLs you want to collect data from here!
    target_urls = [
        "https://nodejs.org/"
    ]
    
    builder = DatasetBuilder()
    builder.build_from_urls(target_urls)
