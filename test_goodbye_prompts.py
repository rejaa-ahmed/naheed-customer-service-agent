import os
import json
from dotenv import load_dotenv
from ai.intent_parser import IntentParser

load_dotenv()

def test_goodbye_prompts():
    parser = IntentParser()
    
    test_cases = [
        # True Positives - English
        ("bye", "goodbye"),
        ("bye bye", "goodbye"),
        ("goodbye", "goodbye"),
        ("see you", "goodbye"),
        ("see you later", "goodbye"),
        ("catch you later", "goodbye"),
        ("take care", "goodbye"),
        ("have a nice day", "goodbye"),
        ("thanks bye", "goodbye"),
        ("thank you bye", "goodbye"),
        ("thanks that's all", "goodbye"),
        ("that's all", "goodbye"),
        ("that's all I needed", "goodbye"),
        ("no thanks", "goodbye"),
        
        # True Positives - Urdu/Roman
        ("Allah Hafiz", "goodbye"),
        ("Allah Hafiz ji", "goodbye"),
        ("Allah hafiz", "goodbye"),
        ("Khuda Hafiz", "goodbye"),
        ("Allah Nigeban", "goodbye"),
        ("Fi Amanillah", "goodbye"),
        ("shukriya Allah Hafiz", "goodbye"),
        
        # False Positives - Continuing conversation
        ("Thanks, one more question.", ("general_query", "greeting")), # Could be general or greeting, but NOT goodbye
        ("Okay, now track my order.", "order_tracking"),
        ("Thanks, can you also check my complaint?", "complaint_tracking"),
        ("Bye, actually wait...", "general_query"),
        ("No wait I have to cancel my order", "cancel_order"),
        ("Thanks, but I want to return this", "refund"),
        ("Thank you, where is my parcel", "order_tracking"),
        ("Allah hafiz, oh one more thing", "general_query"),
        ("bye... why is my order late?", "order_tracking")
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("--- Running Goodbye Intent Prompts Verification ---")
    for phrase, expected in test_cases:
        try:
            result = parser.parse_intent(phrase)
            intent = result.intent
            
            if isinstance(expected, tuple):
                is_pass = intent in expected
                expected_str = " OR ".join(expected)
            else:
                is_pass = (intent == expected)
                if expected != "goodbye" and intent != "goodbye" and intent != "unknown":
                    # For false positives, as long as it's not goodbye, it's a pass
                    is_pass = True
                expected_str = expected
            
            if is_pass:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"
                
            print(f"[{status}] Phrase: '{phrase}' -> Detected: {intent} (Expected: {expected_str})")
            results.append({"phrase": phrase, "status": status, "detected": intent, "expected": expected_str})
        except Exception as e:
            print(f"[ERROR] Exception testing '{phrase}': {e}")
            failed += 1
            results.append({"phrase": phrase, "status": "ERROR", "error": str(e)})
            
    print("\n--- Summary ---")
    print(f"Total: {len(test_cases)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    with open("test_goodbye_results.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    test_goodbye_prompts()
