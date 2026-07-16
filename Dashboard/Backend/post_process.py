import os
from scraper import scrape_and_optimize
from pipeline import AdGenerationPipeline

def main():
    print("[*] Starting Post-Processing...")
    
    # 1. Scrape the website (deterministic, fast, zero LLM cost)
    url = "https://www.maxhealthcare.in/"
    print(f"[*] Scraping website metadata: {url}")
    scraped_data = scrape_and_optimize(url)
    
    # 2. Read the saved raw LLM output from logs
    log_path = "logs/last_llm_raw_output.txt"
    if not os.path.exists(log_path):
        fallback_log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "last_llm_raw_output.txt")
        if os.path.exists(fallback_log_path):
            log_path = fallback_log_path
        else:
            print(f"[!] Error: Raw output log file not found at: {log_path}")
            return
        
    print(f"[*] Reading raw LLM response from: {log_path}")
    with open(log_path, "r", encoding="utf-8") as f:
        raw_response = f.read()
        
    # 3. Initialize Pipeline
    # Pass a dummy API key since we're mocking the API call
    pipeline = AdGenerationPipeline(provider="openai", api_key="dummy_key_not_used")
    
    # 4. Mock call_llm to return the raw text directly without hitting the API
    pipeline.engine.call_llm = lambda sys_prompt, usr_prompt: raw_response
    
    # 5. Run the pipeline (this executes scraper + hybrid parsing + file generation)
    output_directory = "MaxHealth_test_single_call"
    print(f"[*] Parsing response and generating configs into: {output_directory}/")
    pipeline.run(url, bulk=False, output_dir=output_directory)
    print("[+] Post-Processing Completed Successfully!")

if __name__ == "__main__":
    main()
