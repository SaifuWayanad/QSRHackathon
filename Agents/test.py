from KitchenAgent import kitchen_agent



def new_order_recieved():
    print("Informing Kitchen Agent about new order...")
    prompt = """
    A new order has been received and is pending assignment to kitchens. Please check the stream_orders database table for details 
    and proceed with kitchen assignments as per your logic and capacity.
    the orders details are in the stream_orders table. accordingly change the status of the order also.
    """
    response = kitchen_agent.run(prompt)
    print("Kitchen Agent response:", response)

if __name__ == "__main__":
    new_order_recieved()