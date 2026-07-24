import logging
import sys
from services.order_service import OrderService

logging.basicConfig(level=logging.ERROR, stream=sys.stdout)
service = OrderService()
try:
    print(service.get_order_status("2000096577"))
except Exception as e:
    import traceback
    traceback.print_exc()
