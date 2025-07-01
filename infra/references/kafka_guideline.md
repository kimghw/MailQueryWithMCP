I understand you have your IACSRAG project services, including Kafka and Redis, running in Docker containers, and you've provided the exact connection details and topic/event structures. You'd like me to refine the previous Python Kafka example to specifically use these details.

Here's an updated Python Kafka connection and setup guide, tailored to your `IACSRAG` project's configuration:

---

## Connecting to Kafka in Python for IACSRAG Project

This guide provides Python code examples for connecting to and interacting with your Kafka instance, as defined in your IACSRAG project's external access guide. We'll use the `kafka-python` library, which is a common choice for Python Kafka clients.

### 1. Prerequisites

Before running the Python code, ensure your Kafka and Zookeeper Docker containers are up and running as per your project's `docker-compose.yml`:

```bash
docker-compose up -d iacsrag-kafka iacsrag-zookeeper # Or 'docker-compose up -d' for all services
```

Also, ensure you have the `kafka-python` library installed:

```bash
pip install kafka-python
```

### 2. Kafka Connection Details for IACSRAG

Based on your provided `IACSRAG` project external access guide, here are the key connection parameters:

* **Kafka Broker:** `localhost:9092`
* **Kafka UI:** `http://localhost:8080` (container name: `iacsrag-kafka-ui`)
* **Default Consumer Group ID:** `iacsrag-dev` (from `.env.development`)

### 3. Python Client Setup and Initial Configuration

The core of connecting to Kafka in Python involves specifying the `bootstrap_servers`.

#### 3.1 Producer Setup and Event Publishing

Producers are responsible for sending messages (events) to Kafka topics. Your `IACSRAG` project defines a standard event structure and specific topics for various events.

```python
import json
from kafka import KafkaProducer
from uuid import uuid4
from datetime import datetime

# --- IACSRAG Kafka Connection & Configuration ---
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092'] # From .env.development

def get_iacsrag_producer():
    """Initializes a Kafka Producer for IACSRAG project."""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        # Serialize event data to JSON bytes
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        # Key serializer (optional, but good for consistent partitioning)
        key_serializer=lambda k: str(k).encode('utf-8'),
        acks='all',  # Ensure message is written to all in-sync replicas
        retries=3,   # Retry failed sends
        compression_type='gzip' # Compress messages for efficiency
    )
    print(f"IACSRAG Kafka Producer initialized for {KAFKA_BOOTSTRAP_SERVERS}")
    return producer

def create_standard_event(event_type: str, data: dict) -> dict:
    """
    Creates a standard IACSRAG event structure.
    Based on the 'Standard Event Structure' from your guide.
    """
    return {
        "event_type": event_type,
        "source": "iacsrag",
        "correlation_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat(timespec='milliseconds') + 'Z',
        "version": "1.0", # Assuming a default version, adjust as needed
        "data": data
    }

def create_mail_raw_data_event(account_id: str, email_data: dict, api_endpoint: str, response_status: int, request_params: dict, response_timestamp: str) -> dict:
    """
    Creates a Mail Raw Data Event based on the provided structure.
    """
    event_id = str(uuid4()) # Unique ID for this specific event instance
    occurred_at = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z' # Time this event happened

    raw_data_event = {
        "event_type": "email_type",
        "event_id": event_id,
        "account_id": account_id,
        "occurred_at": occurred_at,
        "api_endpoint": api_endpoint,
        "response_status": response_status,
        "request_params": request_params,
        "response_data": {
            "value": [email_data], # Wrap single email_data in a list as per example
            "@odata.context": f"https://graph.microsoft.com/v1.0/$metadata#users('{account_id}')/messages",
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$skip=50" # Example, adjust as needed
        },
        "response_timestamp": response_timestamp
    }
    return raw_data_event


# Example Usage
if __name__ == "__main__":
    producer = get_iacsrag_producer()
    
    # --- Example 1: Publish a document-uploaded event ---
    document_event_data = {
        "document_id": "doc-123",
        "file_name": "report.pdf",
        "file_size": 1024,
        "uploader_id": "user-abc"
    }
    doc_uploaded_event = create_standard_event("document.uploaded", document_event_data)
    
    try:
        # Publish to 'document-uploaded' topic (3 partitions)
        future = producer.send('document-uploaded', value=doc_uploaded_event, key=doc_uploaded_event['correlation_id'])
        record_metadata = future.get(timeout=10)
        print(f"\n[document-uploaded] Event sent! Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
    except Exception as e:
        print(f"Error sending document-uploaded event: {e}")

    # --- Example 2: Publish an email-raw-data event ---
    # Simulate data obtained from Microsoft Graph API
    sample_email_graph_data = {
        "id": "graph-email-id-xyz",
        "subject": "[EA004] Your Latest Update",
        "from": {"emailAddress": {"name": "Sender Name", "address": "sender@example.com"}},
        "body": {"contentType": "html", "content": "<html><body>Email body HTML here</body></html>"},
        "toRecipients": [{"emailAddress": {"name": "Recipient Name", "address": "recipient@example.com"}}],
        "ccRecipients": [],
        "bccRecipients": [],
        "hasAttachments": False,
        "receivedDateTime": "2024-06-15T09:30:00Z",
        "importance": "normal",
        "isRead": False,
        "bodyPreview": "Email preview text...",
        "categories": [],
        "flag": {"flagStatus": "notFlagged"}
    }
    
    mail_raw_event = create_mail_raw_data_event(
        account_id="user-account-id-123",
        email_data=sample_email_graph_data,
        api_endpoint="/v1.0/me/messages",
        response_status=200,
        request_params={"$select": "id,subject,from", "$top": 50, "$skip": 0},
        response_timestamp="2024-06-15T09:35:00Z"
    )

    try:
        # Publish to 'email-raw-data' topic (3 partitions)
        future = producer.send('email-raw-data', value=mail_raw_event, key=mail_raw_event['event_id'])
        record_metadata = future.get(timeout=10)
        print(f"\n[email-raw-data] Event sent! Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
    except Exception as e:
        print(f"Error sending email-raw-data event: {e}")

    finally:
        producer.flush()
        producer.close()
        print("\nProducer closed.")

```

#### 3.2 Consumer Setup and Event Consumption

Consumers read messages from Kafka topics. For your IACSRAG project, you'll need to specify the `group_id` for your consumers, which is set to `iacsrag-dev` in your `.env.development`.

```python
import json
from kafka import KafkaConsumer
import time # For simulation of processing

# --- IACSRAG Kafka Connection & Configuration ---
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092'] # From .env.development
KAFKA_CONSUMER_GROUP_ID = 'iacsrag-dev' # From .env.development

def get_iacsrag_consumer(topics: list):
    """Initializes a Kafka Consumer for IACSRAG project."""
    consumer = KafkaConsumer(
        *topics, # Unpack the list of topics
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_CONSUMER_GROUP_ID,
        auto_offset_reset='earliest', # Start from the beginning if no committed offset
        enable_auto_commit=True,      # Automatically commit offsets
        auto_commit_interval_ms=5000, # Commit every 5 seconds
        value_deserializer=lambda m: json.loads(m.decode('utf-8')), # Deserialize JSON bytes to Python dict
        key_deserializer=lambda k: k.decode('utf-8') if k else None,
        # Adjust session_timeout_ms and max_poll_interval_ms based on expected processing time
        session_timeout_ms=10000, # Max time consumer can be inactive before being removed from group
        max_poll_interval_ms=300000 # Max time between polls before consumer is considered failed
    )
    print(f"IACSRAG Kafka Consumer initialized for topics {topics} in group '{KAFKA_CONSUMER_GROUP_ID}'")
    return consumer

# Example Usage
if __name__ == "__main__":
    # Specify the topics you want this consumer to listen to
    topics_to_consume = ['document-uploaded', 'email-raw-data'] 
    consumer = get_iacsrag_consumer(topics_to_consume)

    print(f"Listening for messages on topics: {topics_to_consume}...")
    try:
        for message in consumer:
            # message is a ConsumerRecord object
            print(f"\n--- Received Message ---")
            print(f"Topic: {message.topic}")
            print(f"Partition: {message.partition}")
            print(f"Offset: {message.offset}")
            print(f"Key: {message.key}")
            print(f"Value (deserialized): {json.dumps(message.value, indent=2)}")

            # --- Process Message based on Topic/Event Type ---
            if message.topic == 'document-uploaded':
                event_data = message.value
                print(f"Processing document upload: Document ID = {event_data['data']['document_id']}")
                # Example: Trigger document processing pipeline
                time.sleep(1) # Simulate work
                print(f"Document {event_data['data']['document_id']} processed.")
                # You might publish a 'document-processed' event here
            
            elif message.topic == 'email-raw-data':
                event_data = message.value
                print(f"Processing raw email data: Account ID = {event_data['account_id']}")
                email_subject = event_data['response_data']['value'][0]['subject'] if event_data['response_data']['value'] else 'N/A'
                print(f"Email Subject: {email_subject}")
                # Example: Store raw email in MongoDB, then extract text, etc.
                time.sleep(2) # Simulate work
                print(f"Raw email from account {event_data['account_id']} processed.")
                # You might publish 'email-processing-events' or 'text-extraction-events' here
            
            else:
                print(f"Unhandled topic: {message.topic}")

    except KeyboardInterrupt:
        print("\nConsumer interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred during consumption: {e}")
    finally:
        consumer.close() # Important to close the consumer for proper group rebalancing
        print("Consumer closed.")

```

### 4. Key Considerations for IACSRAG Project

* **`bootstrap_servers`**: This is your primary connection point, defined as `localhost:9092` in your `KAFKA_BOOTSTRAP_SERVERS` environment variable.
* **`group_id`**: Crucial for consumers. All consumers within the same `group_id` will collectively consume messages from a topic, ensuring each message is processed only once by one member of the group. Your `iacsrag-dev` group is specified.
* **Serialization/Deserialization**: You're consistently using `json.dumps().encode('utf-8')` for producers and `json.loads(m.decode('utf-8'))` for consumers, which aligns with your standard event structure. This is critical for data integrity.
* **Topic Partitions**: Your topics have specific partition counts (e.g., `document-uploaded` has 3, `email-graph-iacs-events` has 5). While the `kafka-python` library handles distribution automatically, this is important for understanding parallelism and ordering guarantees.
* **Error Handling**: The examples include basic `try-except` blocks. In a production IACSRAG environment, you'd want more sophisticated error handling, including dead-letter queues, retry mechanisms, and robust logging.
* **Consumer Offset Management**: `enable_auto_commit=True` and `auto_commit_interval_ms=5000` mean the consumer automatically saves its progress every 5 seconds. For critical applications, consider `enable_auto_commit=False` and manually committing offsets after successful message processing.
* **Producer `flush()`/`close()`**: Always ensure your producer is flushed and closed to guarantee all buffered messages are sent to Kafka.
* **Consumer `close()`**: Always close your consumer when shutting down. This signals to Kafka that it can reassign partitions to other consumers in the group.
* **Security (Important for Production)**: Your guide correctly points out that `localhost` connections are for development. For a production IACSRAG deployment, you **must** configure SSL/TLS encryption and SASL authentication as discussed in the general Kafka setup guide. This would involve adding `security_protocol`, `ssl_cafile`, `sasl_mechanism`, `sasl_plain_username`, `sasl_plain_password`, etc., to your `KafkaProducer` and `KafkaConsumer` configurations.

This tailored guide and code examples should help you effectively connect your Python applications to the Kafka cluster within your IACSRAG project.