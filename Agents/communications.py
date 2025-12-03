import time
from .KitchenAgent import kitchen_agent 

           

def new_order_recieved():
    print("Informing Kitchen Agent about new order...")
    prompt = """
    A new order has been received and is pending assignment to kitchens. Please check the stream_orders database table for details 
    and proceed with kitchen assignments as per your logic and capacity.
    the orders details are in the stream_orders table. accordingly change the status of the order also.
    """
    kitchen_agent.run(prompt)


class EventBus:
    def __init__(self , event):
        self.event = event
 
    def process_event(self):
          # Simulate processing delay
        print("event received:", self.event)
        if self.event == "new_order_recieved":
            new_order_recieved()

 