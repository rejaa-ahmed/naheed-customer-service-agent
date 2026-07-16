-- Adds AI-judged priority and mood tracking to complaint tickets.
--
-- priority: urgency of the customer's message, judged by the AI intent classifier ('High' / 'Low')
-- mood:     customer's emotional tone, judged by the AI intent classifier ('Happy' / 'Sad')
--
-- Column type matches the existing `type`/`status` VARCHAR columns on this table.
-- Requires MySQL 8.0.29+ for "ADD COLUMN IF NOT EXISTS"; on older MySQL, drop the
-- IF NOT EXISTS clause and run manually after confirming the columns don't exist.

ALTER TABLE nhd_complain_tickets
    ADD COLUMN IF NOT EXISTS priority VARCHAR(10) NOT NULL DEFAULT 'Low' AFTER type,
    ADD COLUMN IF NOT EXISTS mood VARCHAR(10) NOT NULL DEFAULT 'Happy' AFTER priority;
