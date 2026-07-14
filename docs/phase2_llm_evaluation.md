# Phase 2 LLM Evaluation Report

## Overall Accuracy: **96.00%**

## Metrics by Intent
| Intent | Precision | Recall |
|--------|-----------|--------|
| general_query | 92.86% | 100.00% |
| unknown | 66.67% | 100.00% |
| complaint | 100.00% | 95.83% |
| refund | 100.00% | 100.00% |
| order_tracking | 100.00% | 91.67% |
| goodbye | 100.00% | 100.00% |
| greeting | 100.00% | 88.89% |

## Top 10 Failure Cases
| Message | Expected | Detected | Confidence | Fallback |
|---------|----------|----------|------------|----------|
| Hello Naheed | greeting | unknown | 0.55 | True |
| Check status for 555444333 | order_tracking | unknown | 1.0 | True |
| Track order 12345 and 67890 | order_tracking | unknown | 1.0 | True |
| Are you guys scammers??? My parcel is empty! | complaint | general_query | 0.9 | False |

## Confusion Matrix
- **general_query** was predicted as: {'general_query': 13}
- **unknown** was predicted as: {'unknown': 6}
- **complaint** was predicted as: {'complaint': 23, 'general_query': 1}
- **refund** was predicted as: {'refund': 19}
- **order_tracking** was predicted as: {'order_tracking': 22, 'unknown': 2}
- **goodbye** was predicted as: {'goodbye': 5}
- **greeting** was predicted as: {'greeting': 8, 'unknown': 1}

## Suggested Prompt Improvements
1. **Ambiguous Short Strings:** Adding negative examples in the prompt to prevent numeric-only strings from defaulting to Order Tracking.
2. **Context Window Limitations:** The current prompt handles Roman Urdu effectively, but inserting a translation primer could eliminate the margin of error on highly informal slang complaints.

## Full Test Suite
| Message | Expected | Detected | Confidence | Fallback | Pass |
|---------|----------|----------|------------|----------|------|
| Hello there | greeting | greeting | 0.93 | False | ✅ |
| Hi | greeting | greeting | 0.96 | False | ✅ |
| Assalam o alaikum | greeting | greeting | 0.97 | False | ✅ |
| Good morning | greeting | greeting | 0.97 | False | ✅ |
| hey bot | greeting | greeting | 0.96 | False | ✅ |
| Hello Naheed | greeting | unknown | 0.55 | True | ❌ |
| hiiiii | greeting | greeting | 0.96 | False | ✅ |
| Goodbye | goodbye | goodbye | 0.93 | False | ✅ |
| Thanks bye | goodbye | goodbye | 0.94 | False | ✅ |
| Khuda hafiz | goodbye | goodbye | 0.99 | False | ✅ |
| See you | goodbye | goodbye | 0.96 | False | ✅ |
| Ok bye | goodbye | goodbye | 0.97 | False | ✅ |
| Where is my order? | order_tracking | order_tracking | 0.92 | False | ✅ |
| Track order 100000123 | order_tracking | order_tracking | 0.96 | False | ✅ |
| I want to track my parcel | order_tracking | order_tracking | 0.95 | False | ✅ |
| Check status for 555444333 | order_tracking | unknown | 1.0 | True | ❌ |
| Can you tell me where order 987654321 is? | order_tracking | order_tracking | 0.97 | False | ✅ |
| Mera order kahan hai? | order_tracking | order_tracking | 0.93 | False | ✅ |
| Order kab tak aye ga? | order_tracking | order_tracking | 0.95 | False | ✅ |
| Bhai mera parcel 12345 track kardo | order_tracking | order_tracking | 0.94 | False | ✅ |
| I placed an order yesterday. | order_tracking | order_tracking | 0.95 | False | ✅ |
| order trckng | order_tracking | order_tracking | 0.95 | False | ✅ |
| My order hasn't arrived. | order_tracking | order_tracking | 0.93 | False | ✅ |
| when delivery? | order_tracking | order_tracking | 0.97 | False | ✅ |
| trac my package 999888777 | order_tracking | order_tracking | 0.94 | False | ✅ |
| Track order 12345 and 67890 | order_tracking | unknown | 1.0 | True | ❌ |
| Where are my orders 111 and 222? | order_tracking | order_tracking | 0.94 | False | ✅ |
| Order 4567 arrived but 8901 is missing | order_tracking | order_tracking | 0.96 | False | ✅ |
| I want to complain. | complaint | complaint | 0.95 | False | ✅ |
| The item I received is broken. | complaint | complaint | 0.93 | False | ✅ |
| Missing items in my delivery. | complaint | complaint | 0.93 | False | ✅ |
| Horrible service, I need to complain. | complaint | complaint | 0.97 | False | ✅ |
| File a complaint for order 12345 | complaint | complaint | 0.92 | False | ✅ |
| This is ridiculous! I am never shopping here again! | complaint | complaint | 0.97 | False | ✅ |
| Worst experience ever. Fix this now. | complaint | complaint | 0.95 | False | ✅ |
| Are you guys scammers??? My parcel is empty! | complaint | general_query | 0.9 | False | ❌ |
| Baqwas service hai aap ki | complaint | complaint | 0.93 | False | ✅ |
| Wah kya service hai, toota hua saman bhej diya | complaint | complaint | 0.96 | False | ✅ |
| Mujhe shikayat karni hai | complaint | complaint | 0.94 | False | ✅ |
| I want a refund. | refund | refund | 0.93 | False | ✅ |
| How do I get my money back? | refund | refund | 0.93 | False | ✅ |
| Cancel my order and refund me | refund | refund | 0.98 | False | ✅ |
| Refund required for 12345 | refund | refund | 0.94 | False | ✅ |
| Return product and need refund | refund | refund | 0.97 | False | ✅ |
| Mera paisa wapas karo | refund | refund | 0.92 | False | ✅ |
| Refund kab milega? | refund | refund | 0.97 | False | ✅ |
| What are your delivery hours? | general_query | general_query | 0.98 | False | ✅ |
| Do you sell shoes? | general_query | general_query | 0.95 | False | ✅ |
| Where is your store located? | general_query | general_query | 0.96 | False | ✅ |
| Do you offer cash on delivery? | general_query | general_query | 0.94 | False | ✅ |
| Can I pay with credit card? | general_query | general_query | 0.97 | False | ✅ |
| Store timings kya hain? | general_query | general_query | 0.99 | False | ✅ |
| Is delivery free? | general_query | general_query | 0.95 | False | ✅ |
| Who is the president of the USA? | unknown | unknown | 0.99 | False | ✅ |
| Translate this to French | unknown | unknown | 0.97 | False | ✅ |
| Write a poem about shopping | unknown | unknown | 0.92 | False | ✅ |
| 123 | unknown | unknown | 0.96 | False | ✅ |
| asdfasdfasdf | unknown | unknown | 0.92 | False | ✅ |
| Tell me a joke | unknown | unknown | 0.99 | False | ✅ |
| Refund my order 13839 | refund | refund | 0.97 | False | ✅ |
| Is 36288 in stock? | general_query | general_query | 0.95 | False | ✅ |
| I hate 30224 | complaint | complaint | 0.94 | False | ✅ |
| Refund my order 98009 | refund | refund | 0.95 | False | ✅ |
| I hate 78044 | complaint | complaint | 0.93 | False | ✅ |
| Please check order 74928 | order_tracking | order_tracking | 0.96 | False | ✅ |
| Please check order 51969 | order_tracking | order_tracking | 0.97 | False | ✅ |
| Please check order 15782 | order_tracking | order_tracking | 0.93 | False | ✅ |
| Refund my order 71858 | refund | refund | 0.94 | False | ✅ |
| Cancel 29143 | refund | refund | 0.97 | False | ✅ |
| Cancel 29610 | refund | refund | 0.98 | False | ✅ |
| I hate 91231 | complaint | complaint | 0.97 | False | ✅ |
| Is 20293 in stock? | general_query | general_query | 0.94 | False | ✅ |
| Is 57708 in stock? | general_query | general_query | 0.98 | False | ✅ |
| Complaint regarding 32462 | complaint | complaint | 0.97 | False | ✅ |
| Complaint regarding 60708 | complaint | complaint | 0.97 | False | ✅ |
| Please check order 37728 | order_tracking | order_tracking | 0.98 | False | ✅ |
| Complaint regarding 86575 | complaint | complaint | 0.95 | False | ✅ |
| Cancel 78035 | refund | refund | 0.92 | False | ✅ |
| Complaint regarding 60908 | complaint | complaint | 0.97 | False | ✅ |
| Complaint regarding 86910 | complaint | complaint | 0.95 | False | ✅ |
| Hello I am 39414 | greeting | greeting | 0.97 | False | ✅ |
| Is 90049 in stock? | general_query | general_query | 0.96 | False | ✅ |
| My package 73673 is late | complaint | complaint | 0.94 | False | ✅ |
| Is 95332 in stock? | general_query | general_query | 0.95 | False | ✅ |
| Cancel 39936 | refund | refund | 0.98 | False | ✅ |
| I hate 54275 | complaint | complaint | 0.96 | False | ✅ |
| Please check order 41010 | order_tracking | order_tracking | 0.99 | False | ✅ |
| Is 96636 in stock? | general_query | general_query | 0.94 | False | ✅ |
| Cancel 33934 | refund | refund | 0.94 | False | ✅ |
| My package 52029 is late | complaint | complaint | 0.99 | False | ✅ |
| Please check order 35025 | order_tracking | order_tracking | 0.97 | False | ✅ |
| Refund my order 46475 | refund | refund | 0.97 | False | ✅ |
| Cancel 20860 | refund | refund | 0.97 | False | ✅ |
| Cancel 34964 | refund | refund | 0.98 | False | ✅ |
| Hello I am 90258 | greeting | greeting | 0.96 | False | ✅ |
| Please check order 95711 | order_tracking | order_tracking | 0.94 | False | ✅ |
| Please check order 34573 | order_tracking | order_tracking | 0.98 | False | ✅ |
| Refund my order 69458 | refund | refund | 0.98 | False | ✅ |
| My package 63829 is late | complaint | complaint | 0.97 | False | ✅ |
| My package 14653 is late | complaint | complaint | 0.98 | False | ✅ |