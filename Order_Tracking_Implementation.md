# Order Tracking Module – Technical Implementation Document

## 1. Introduction
### Purpose
The Order Tracking module serves as a core automation feature within the conversational AI ecosystem, designed to independently handle customer inquiries regarding their orders. It retrieves precise, real-time data directly from the live Magento database without human intervention.

### Business Problem
E-commerce customer support teams frequently face a high volume of repetitive "Where is my order?" inquiries. This backlog leads to delayed responses and decreased customer satisfaction. The Order Tracking module solves this by providing instantaneous, accurate, and 24/7 visibility into order statuses, tracking numbers, estimated delivery times, and missing items.

### High-Level Overview
The system interfaces customer requests through an orchestration layer that parses intents using an LLM. Once an Order Tracking intent and its corresponding Order ID are extracted, the system securely executes read-only queries against the live Magento MySQL database. The retrieved data is then evaluated through a robust set of business rules—including parent-child order relationships and missing item mathematics—before generating a highly structured response to the user.

---

## 2. System Architecture

The architecture utilizes a modular, layered design to ensure separation of concerns, high testability, and scalability.

- **Streamlit UI:** The front-end application interface where customers interact with the chatbot in real-time.
- **Conversation Manager:** Orchestrates the dialogue state, manages conversation history, and routes parsed intents to the appropriate operational flow.
- **Intent Parser:** Evaluates user input using natural language processing to detect the intent (e.g., "track_order") and extract required entities (e.g., "Order ID").
- **LLM Factory:** Abstracted interface managing connections to Large Language Models.
- **Gemini / Groq:** Primary and fallback LLM services utilized exclusively for natural language understanding and entity extraction.
- **Flow Manager:** Manages the lifecycle and state transitions of the active conversational flow, ensuring multi-turn dialog consistency.
- **Order Tracking Flow:** The specific state machine responsible for guiding the user through the tracking process, prompting for missing Order IDs when necessary.
- **Order Service:** Contains the core business logic. It handles data formatting, ETA evaluations, tracking link generation, and determines the active order in parent-child relationships.
- **Order Repository:** The database abstraction layer. It encapsulates all raw SQL queries, handles connection acquisition, and performs complex relational joins.
- **Database Layer:** Manages high-performance MySQL connection pooling and direct interaction with the live Magento schema.

### ASCII Architecture Diagram

```text
  [Streamlit UI]
        │
        ▼
[Conversation Manager] ◄────► [Flow Manager] ◄────► [Order Tracking Flow]
        │                                                   │
        ▼                                                   ▼
 [Intent Parser]                                     [Order Service]
        │                                                   │
        ▼                                                   ▼
  [LLM Factory]                                    [Order Repository]
  (Gemini/Groq)                                             │
                                                            ▼
                                                    [Database Layer]
                                                    (Connection Pool)
                                                            │
                                                            ▼
                                                    [Magento Database]
```

---

## 3. End-to-End Order Tracking Flow

The sequence of operations required to service an order tracking request is strictly enforced.

### Flow Execution Diagram

```text
    User Message
         │
         ▼
[Conversation Manager] ── Receives input and orchestrates routing
         │
         ▼
    [Intent Parser] ───── Parses intent & extracts entities (e.g., "Where is 12345?")
         │
         ▼
[Order Tracking Flow] ─── Validates presence of Order ID entity
         │
         ▼
  [Order Service] ─────── Applies formatting and business rules
         │
         ▼
 [Order Repository] ───── Executes SQL queries, handles parent-child joins
         │
         ▼
 [Magento Database] ───── Returns raw relational data
         │
         ▼
 [Response Builder] ───── Constructs the unified customer-facing text
         │
         ▼
    Customer Output
```

### Execution Stages
1. **Receive Order ID:** The user provides an input string containing an intent and order ID.
2. **Validate Order ID:** The service validates the raw string format against database constraints.
3. **Fetch Parent Order:** The repository executes a primary lookup.
4. **Resolve Parent/Child Relationship:** Evaluates hierarchical references to locate split shipments.
5. **Determine Active Shipment:** Identifies the latest active tracking order (child vs. parent).
6. **Calculate Unavailable Items:** Computes SKU quantities via database comparison.
7. **Determine Payment/Refund Message:** Cross-references invoices and credit memos.
8. **Execute Tracking Logic:** Parses status, ETA, and external courier details.
9. **Build Final Response:** Formats all data into the required output structure.

---

## 4. Intent Detection

The chatbot utilizes an advanced LLM specifically configured for intent parsing.

### Supported Languages
The Intent Parser is fully equipped to understand both **English** and **Roman Urdu**, which is critical for local demographic coverage.
- *English Example:* "Can you track my order 2000098941?"
- *Roman Urdu Example:* "Mera order 2000098941 kahan hai?"

### Scope Constraints
The LLM is highly constrained. It is **ONLY** responsible for:
1. Intent detection (`track_order`).
2. Entity extraction (`order_id`).

The LLM is strictly prohibited from inferring or deciding:
- Shipment status
- ETA
- Refunds
- Payment specifics
- Courier details

All factual data is retrieved **exclusively** from the database to prevent AI hallucination.

---

## 5. Order ID Validation

Before executing any database queries, Order IDs must pass strict validation to ensure security and prevent unnecessary latency.

### Validation Rules
- Order IDs must not be assumed to be strictly numeric.
- Magento increment IDs may contain letters, digits, underscores (`_`), and hyphens (`-`).
- Security is maintained through SQL parameterized queries at the repository layer.

**Accepted Examples:**
- `2000098941`
- `2000098941_2`
- `ORD-123-ABC`

**Rejected Examples:**
- `2000098941@`
- `abc#123`
- `20000$`

---

## 6. Database Design

The tracking module interacts with a highly relational Magento 2 database schema. 

| Table Name | Purpose |
| :--- | :--- |
| `sales_order` | Core table containing the `entity_id`, `increment_id`, `status`, and relational parent mapping (`relation_parent_id`). |
| `sales_order_address` | Contains shipping destination details, including the `city`, which is critical for Karachi vs. External routing. |
| `nhd_sales_order_additionals` | A custom table housing `delivery_due_date` (ETA), `courier`, and `cn_number` (tracking numbers). |
| `sales_order_item` | Stores individual line items (`sku`, `qty_ordered`). Critical for identifying missing products. |
| `sales_order_payment` | Defines the transaction type (e.g., `cashondelivery`, `ccavenuepay`). |
| `sales_creditmemo` | Tracks financial returns, storing the refund `state` and `grand_total`. |
| `sales_shipment_track` | Secondary Magento table for shipment tracking associations. |

---

## 7. SQL Query Design

Security, efficiency, and robustness are the primary tenets of the repository's SQL design.

### Joins and Relationship Mapping
- **LEFT JOIN Strategy:** `sales_order` is always the primary driver. We use `LEFT JOIN` for addresses and additionals because an order may legitimately exist without an assigned courier or completed address in edge cases. Inner joins would cause these orders to erroneously return as "Not Found."
- **Parameterized Queries:** All user inputs (`increment_id`) are passed via safe `%s` parameters to the `mysql.connector`, entirely mitigating SQL injection vectors.
- **Relational Integrity:** Queries navigate Magento's hierarchical structure via `entity_id` (internal ID) and `increment_id` (customer-facing ID).

---

## 8. Parent–Child Order Logic

Magento splits orders into parent and child records when items ship from different warehouses or at different times. 

### Architecture
- **Parent Order:** The original customer transaction. Contains the full item list and primary payment details.
- **Child Order:** The actual shipment execution record.
- **Relationships:** A child order links back to the parent using `relation_parent_id` (linking `entity_id` to `entity_id`) and `relation_parent_real_id` (linking to the parent's `increment_id`).

### Active Order Determination
When a parent order is queried, the repository searches for all associated child orders. If child orders exist, the chatbot defines the **active tracking order** as the child order, as it holds the true physical shipment status, ETA, and tracking numbers. 

```text
[User Queries Parent: 2000098287]
         │
         ▼
[Repo Locates Parent] ──► [Queries relation_parent_id] ──► [Finds Child: 2000098287-1]
                                                                     │
                                                                     ▼
                                                   [Child marked as 'Active Order']
```

---

## 9. Missing Item Detection

When a parent order is split into a child order, some items may be deliberately omitted (e.g., out of stock).

### Mathematical Algorithm
The repository calculates unavailable items on-the-fly comparing the parent against **ALL** active child orders:

`Unavailable Quantity = Parent Qty Ordered - SUM(Child Qty Ordered)`

### Edge Case Handling
1. **Configurable Products:** Magento duplicates items across simple and configurable product rows with the same SKU. The algorithm strictly filters `WHERE parent_item_id IS NULL` to eliminate double-counting.
2. **Filtering Zeroes:** If `Unavailable Quantity <= 0`, the SKU is cleanly omitted. 
3. **Multiple Children:** By calculating the `SUM()` across all child orders grouped by SKU, the algorithm accurately reflects items missing across the entire aggregate fulfillment.

---

## 10. ETA Logic

Estimated Time of Arrival (ETA) provides customer peace of mind, but must be stringently validated before display.

### Decision Flow
1. **Retrieval:** The algorithm looks for `estimated_delivery_datetime` on the active tracking order. If absent, it inherits from the parent order.
2. **Validation:**
   - **NULL ETA:** If the database contains no ETA, the section is entirely omitted.
   - **Expired ETA:** The datetime is compared against the live server clock (`datetime.now()`). If the ETA has already elapsed, it is considered stale and omitted.
   - **Future ETA:** If valid and in the future, it is formatted gracefully (e.g., `16 July 2026, 02:00 PM`) and presented to the user.

---

## 11. Shipment Status Logic

The fundamental business rule for order status is **Absolute Fidelity**.

- The chatbot returns the **exact string** stored in the database's `status` column.
- There is **No Paraphrasing, Normalization, or Translation**. 
- If the database outputs `processing`, the chatbot outputs `processing`. If the database outputs `shipped`, the chatbot outputs `shipped`.
- This ensures customers receive the exact same information from the chatbot as they do from customer support agents examining the backend.

---

## 12. Karachi vs External Logic

Order tracking varies drastically depending on geographic destination.

- **Local Deliveries (Karachi):** If the `shipping_city` evaluates to `karachi` (case-insensitive), internal fleet logistics govern the delivery. External tracking strings are omitted.
- **External Deliveries (Nationwide):** If the city is anything else, the order relies on 3rd-party logistics.
  - **Courier Mapping:** Carrier codes like `mnpshipping` and `lcsshipping` map to physical couriers (M&P, Leopards).
  - **Tracking Number:** `cn_number` is presented explicitly.
  - **Tracking URLs:** Direct click-through URLs are dynamically generated linking the user to the courier's real-time web portal. If a courier is assigned but no tracking number is yet generated, the system outputs a placeholder informing the user it has been handed over.

---

## 13. Payment Logic

Handling financial messaging requires care to avoid customer confusion.

### Cash on Delivery (COD)
- Detected via substrings (`cod`, `cashondelivery`).
- For missing items, a specific disclaimer is provided: *"This order was placed using Cash on Delivery. You will only pay for the items that were delivered. No refund is required."*

### Online Payments
- If prepaid, the customer is owed money for missing items.
- The `sales_creditmemo` table is queried for the latest refund state.
- **Refund States Displayed:**
  - `Completed` (State 2)
  - `Processing` (State 1)
  - `Pending` (State Exists)
  - `No refund has been initiated yet.` (No State)

---

## 14. Response Generation

The Final Response Builder aggregates all validated data into a highly professional, unified, and sectioned layout.

### Unified Layout Structure
```text
Order ID:
[Active Order ID]

Shipment Status:
[Exact DB Status]

Estimated Delivery:
[ETA] (Omitted if expired or NULL)

Tracking Information: (Omitted if Karachi)
Courier: [Courier]
Tracking Number: [Tracking Number]
Tracking Link: [URL]

Unavailable Items: (Omitted if none exist)
• [Item Name] ([Qty])

Payment / Refund Status: (Omitted if no unavailable items)
[COD text OR Prepaid Refund state]

Notes:
[Dynamic closure note based on ETA, shipment, and refunds]
```

---

## 15. Performance Optimizations

To handle high traffic, the database layer was refactored for efficiency.

### MySQL Connection Pooling
- **Previous Bottleneck:** Initial implementations instantiated a fresh TCP handshake and authentication sequence with the MySQL server for every single database read, causing extreme latency (upwards of 1.6s per query).
- **Optimization:** A global `MySQLConnectionPool` was implemented.
- **Improvements:** Connections are kept alive and leased to threads upon request. Handshake latency was entirely eliminated, driving total database request times down by over 90%.

---

## 16. Logging Strategy

A comprehensive logging strategy acts as the module's nervous system, providing immediate visibility for debugging.

- **Intent Parser Logs:** Tracks exact string input and extracted entities.
- **LLM Logs:** Monitors token usage, latency, and failover triggers.
- **Database Logs:** Benchmarks performance (Time to Acquire Connection, Time to Execute).
- **Repository Logs:** Documents parent-child hierarchy resolutions and missing SKU math.
- **Order Service Logs:** Tracks ETA validity, status evaluations, and response formatting branches.

---

## 17. Error Handling

Resilience is built into every layer.

- **Invalid Order IDs:** Regex rejection at the service layer prevents backend hits.
- **Order Not Found:** Custom `OrderNotFoundError` cleanly halts execution and provides a polite fallback response.
- **Database Failures / Timeouts:** Trapped by `try/except` blocks to prevent application crashes, returning a technical difficulty message.
- **LLM Failover:** Primary Gemini failures instantly roll over to Groq.

---

## 18. Testing Strategy

The module boasts robust quality assurance.

- **Unit Testing:** 16 independent test cases covering all edge scenarios using `unittest` and `mock` repositories.
- **Integration Testing:** Live database scripts executed against actual staging IDs (e.g., `2000098287`).
- **Regression Testing:** Continuous verification ensuring that parent-child updates do not break standard order tracking flows.
- **Major Scenarios Tested:** COD refund suppression, ETA expiration, empty missing item calculations, external tracking URL generation, and malformed inputs.

---

## 19. Features Implemented

- [x] Basic Order Status Retrieval
- [x] Strict DB Status Compliance
- [x] Delivery ETA Processing and Validation
- [x] Geographic Routing (Karachi vs. External)
- [x] External Courier & Tracking Link Mapping
- [x] Parent-Child Shipment Detection
- [x] Complex Mathematical Missing Item Resolution
- [x] COD vs Prepaid Refund Logic
- [x] MySQL Connection Pooling
- [x] Roman Urdu Support

---

## 20. Current Limitations

Honesty in documentation ensures correct future maintenance.

- **Read-Only Scope:** The current implementation strictly reads data. It cannot take action on delayed orders or notify human dispatchers.
- **No Complex Bundles:** Highly customized Magento bundled products may require extended parent/child item tracking logic in the future depending on catalog architecture.

---

## 21. Future Work

The robust architectural foundation paves the way for extended capabilities.

- **Refund Flow:** Dedicated workflows for processing returns and credit memos.
- **Complaints:** Automated complaint logging integrated into Zendesk or custom CRMs.
- **Human Escalation:** Live hand-offs to support agents when tracking reveals severe anomalies.
- **Voice Support:** Integrating STT and TTS to enable voice-based tracking queries.

---

## 22. Conclusion

The Order Tracking module successfully resolves the primary business objective of automating real-time customer status requests. Through rigorous mathematical verifications, robust parent-child database logic, strict architectural layering, and substantial connection pool performance optimizations, the chatbot provides a fast, resilient, and highly scalable customer service solution. This decoupled architecture natively supports the straightforward integration of future workflows like Complaints and Refund Tracking without disrupting the established codebase.
