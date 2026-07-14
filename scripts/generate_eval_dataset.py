import json

dataset = [
    # Greetings
    {"text": "Hello there", "intent": "greeting"},
    {"text": "Hi", "intent": "greeting"},
    {"text": "Assalam o alaikum", "intent": "greeting"},
    {"text": "Good morning", "intent": "greeting"},
    {"text": "hey bot", "intent": "greeting"},
    {"text": "Hello Naheed", "intent": "greeting"},
    {"text": "hiiiii", "intent": "greeting"},
    
    # Goodbye
    {"text": "Goodbye", "intent": "goodbye"},
    {"text": "Thanks bye", "intent": "goodbye"},
    {"text": "Khuda hafiz", "intent": "goodbye"},
    {"text": "See you", "intent": "goodbye"},
    {"text": "Ok bye", "intent": "goodbye"},

    # Order Tracking - Clean
    {"text": "Where is my order?", "intent": "order_tracking"},
    {"text": "Track order 100000123", "intent": "order_tracking"},
    {"text": "I want to track my parcel", "intent": "order_tracking"},
    {"text": "Check status for 555444333", "intent": "order_tracking"},
    {"text": "Can you tell me where order 987654321 is?", "intent": "order_tracking"},
    
    # Order Tracking - Mixed/Urdu
    {"text": "Mera order kahan hai?", "intent": "order_tracking"},
    {"text": "Order kab tak aye ga?", "intent": "order_tracking"},
    {"text": "Bhai mera parcel 12345 track kardo", "intent": "order_tracking"},
    
    # Order Tracking - Ambiguous / Typos
    {"text": "I placed an order yesterday.", "intent": "order_tracking"},
    {"text": "order trckng", "intent": "order_tracking"},
    {"text": "My order hasn't arrived.", "intent": "order_tracking"},
    {"text": "when delivery?", "intent": "order_tracking"},
    {"text": "trac my package 999888777", "intent": "order_tracking"},

    # Order Tracking - Multiple numbers
    {"text": "Track order 12345 and 67890", "intent": "order_tracking"},
    {"text": "Where are my orders 111 and 222?", "intent": "order_tracking"},
    {"text": "Order 4567 arrived but 8901 is missing", "intent": "order_tracking"},
    
    # Complaints - Clean
    {"text": "I want to complain.", "intent": "complaint"},
    {"text": "The item I received is broken.", "intent": "complaint"},
    {"text": "Missing items in my delivery.", "intent": "complaint"},
    {"text": "Horrible service, I need to complain.", "intent": "complaint"},
    {"text": "File a complaint for order 12345", "intent": "complaint"},
    
    # Complaints - Angry / Aggressive
    {"text": "This is ridiculous! I am never shopping here again!", "intent": "complaint"},
    {"text": "Worst experience ever. Fix this now.", "intent": "complaint"},
    {"text": "Are you guys scammers??? My parcel is empty!", "intent": "complaint"},
    
    # Complaints - Urdu / Sarcastic
    {"text": "Baqwas service hai aap ki", "intent": "complaint"},
    {"text": "Wah kya service hai, toota hua saman bhej diya", "intent": "complaint"},
    {"text": "Mujhe shikayat karni hai", "intent": "complaint"},
    
    # Refunds
    {"text": "I want a refund.", "intent": "refund"},
    {"text": "How do I get my money back?", "intent": "refund"},
    {"text": "Cancel my order and refund me", "intent": "refund"},
    {"text": "Refund required for 12345", "intent": "refund"},
    {"text": "Return product and need refund", "intent": "refund"},
    {"text": "Mera paisa wapas karo", "intent": "refund"},
    {"text": "Refund kab milega?", "intent": "refund"},

    # General Query
    {"text": "What are your delivery hours?", "intent": "general_query"},
    {"text": "Do you sell shoes?", "intent": "general_query"},
    {"text": "Where is your store located?", "intent": "general_query"},
    {"text": "Do you offer cash on delivery?", "intent": "general_query"},
    {"text": "Can I pay with credit card?", "intent": "general_query"},
    {"text": "Store timings kya hain?", "intent": "general_query"},
    {"text": "Is delivery free?", "intent": "general_query"},
    
    # Unknown / Off-topic
    {"text": "Who is the president of the USA?", "intent": "unknown"},
    {"text": "Translate this to French", "intent": "unknown"},
    {"text": "Write a poem about shopping", "intent": "unknown"},
    {"text": "123", "intent": "unknown"},
    {"text": "asdfasdfasdf", "intent": "unknown"},
    {"text": "Tell me a joke", "intent": "unknown"}
]

# We will generate up to 100 by repeating some variations
import random
# Let's add some more programmatically to reach 100
extra_templates = [
    ("Please check order {id}", "order_tracking"),
    ("My package {id} is late", "complaint"),
    ("Refund my order {id}", "refund"),
    ("Cancel {id}", "refund"),
    ("Complaint regarding {id}", "complaint"),
    ("Hello I am {id}", "greeting"), # confusing ID
    ("Is {id} in stock?", "general_query"),
    ("I hate {id}", "complaint")
]

for i in range(100 - len(dataset)):
    template, intent = random.choice(extra_templates)
    rand_id = str(random.randint(10000, 99999))
    dataset.append({"text": template.replace("{id}", rand_id), "intent": intent})

with open("tests/eval_dataset.json", "w") as f:
    json.dump(dataset, f, indent=4)

print(f"Generated {len(dataset)} examples in eval_dataset.json")
