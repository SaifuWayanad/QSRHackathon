import time
import os
import threading
from datetime import datetime

from .KitchenAgent import kitchen_agent 

# Global lock to prevent concurrent agent execution
_agent_lock = threading.Lock()
_agent_running = False

           

def new_order_recieved():
    global _agent_running
    
    # Quick check before even printing - discard immediately if busy
    if _agent_running:
        print("⚠️  Kitchen Agent is already processing - discarding this request")
        return "Kitchen Agent is busy. Request discarded."
    
    print("🔔 Informing Kitchen Agent about new order...")
    prompt = """
    A new order has been received and is pending assignment to kitchens. 
    
    Please check the 'orders' table in the MySQL database for orders with status='pending'.
    
    For each pending order:
    1. Query the order_items to get all food items
    2. Query food_items table to determine which kitchen each item should be assigned to (using kitchen_id)
    3. Create kitchen_assignments records for each item-kitchen pair
    4. Update the order status to 'assigned_to_kitchen'
    
    Follow the instructions in your system prompt for proper MySQL query syntax and data integrity.
    insertion query like 
    INSERT INTO `qsr_db`.`kitchen_assignments`
        (`id`,
        `item_id`,
        `kitchen_id`,
        `order_id`,
        `status`,
        `assigned_at`,
        `completed_at`,
        `started`,
        `completed`)
        VALUES
        (<{id: }>,
        <{item_id: }>,
        <{kitchen_id: }>,
        <{order_id: }>,
        <{status: pending}>,
        <{assigned_at: current_timestamp()}>,
        <{completed_at: 0000-00-00 00:00:00}>,
        <{started: 0}>,
        <{completed: 0}>);

    """
    
    # Acquire lock to mark agent as running (double-check with lock)
    with _agent_lock:
        if _agent_running:
            print("⚠️  Kitchen Agent already processing - discarding this request")
            return "Kitchen Agent is busy. Request discarded."
        _agent_running = True
        print("✓ Lock acquired - starting agent processing")
    
    try:
        if kitchen_agent is None:
            print("⚠️  Kitchen Agent not available - skipping agent processing")
            response = "Kitchen Agent is not available. Order received but agent processing skipped."
        else:
            print(prompt)
            response = kitchen_agent.run(prompt)
            print("✓ Kitchen Agent response received")
            print(response)
    except Exception as e:
        print(f"❌ Error running Kitchen Agent: {e}")
        response = f"Error: {e}"
    finally:
        # Always release the lock when done
        with _agent_lock:
            _agent_running = False
        print("✓ Kitchen Agent processing completed - ready for next request")
    
    # response = "Kitchen Agent has been informed about the new order and will process it shortly."
    
    # Save response to file with timestamp
    try:
        # Create responses folder if it doesn't exist
        responses_dir = "responses"
        if not os.path.exists(responses_dir):
            os.makedirs(responses_dir)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{responses_dir}/{timestamp}.txt"
        
        # Write response to file
        with open(filename, 'w') as f:
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Event: new_order_recieved\n")
            f.write(f"{'='*60}\n\n")
            f.write(str(response))
        
        print(f"✓ Response saved to {filename}")
    except Exception as e:
        print(f"⚠️  Error saving response: {e}")


class EventBus:
    def __init__(self , event):
        print(f"🚀 EventBus initialized with event: {event}")
        self.event = event
 
    def process_event(self):
        print(f"⚡ EventBus.process_event() called for: {self.event}")
        # Simulate processing delay
        # print("event received:", self.event)
        if self.event == "new_order_recieved":
            print("✓ Event matched: new_order_recieved - calling handler...")
            new_order_recieved()
        else:
            print(f"⚠️  No handler for event: {self.event}")

 
# if __name__ == "__main__":
#     # Example usage
#     event_bus = EventBus(event="new_order_recieved")
#     event_bus.process_event()