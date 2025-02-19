import requests
import uuid
from typing import Dict, Any
from app.core.config import settings

class PayPalService:
    def __init__(self):
        self.base_url = settings.PAYPAL_BASE_URL  # e.g., 'https://api-m.sandbox.paypal.com'
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> str:
        """
        Obtain OAuth 2.0 access token from PayPal
        """
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(
            url, 
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET), 
            headers=headers, 
            data=data
        )
        response.raise_for_status()
        return response.json()['access_token']

    def create_order(self, 
                 amount: float, 
                 currency: str = 'USD', 
                 invoice_id: str = None,
                 items: list = None) -> Dict[str, Any]:
        """
        Create a PayPal order
        
        :param amount: Total order amount
        :param currency: Currency code
        :param invoice_id: Optional invoice identifier
        :param items: Optional list of order items
        :return: Order creation details
        "order_id": "64356144SN997962G"

        """
        url = f"{self.base_url}/v2/checkout/orders"
        
        # Default items if not provided
        if not items:
            items = [{
                "name": "Charging Station Booking",
                "description": "Booking Service",
                "quantity": "1",
                "unit_amount": {
                    "currency_code": currency,
                    "value": str(amount)
                },
                "tax": {
                    "currency_code": currency,
                    "value": "0.00"
                },
                "total_amount": {
                    "currency_code": currency,
                    "value": str(amount)
                }
            }]
        else:
            # Ensure each item has the required fields
            for item in items:
                if 'total_amount' not in item:
                    # Calculate total amount if not provided
                    quantity = float(item.get('quantity', 1))
                    unit_value = float(item['unit_amount']['value'])
                    item['total_amount'] = {
                        "currency_code": currency,
                        "value": str(quantity * unit_value)
                    }
        
        payload = {
            "intent": "CAPTURE",
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "landing_page": "LOGIN",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                        "return_url": settings.PAYPAL_RETURN_URL,
                        "cancel_url": settings.PAYPAL_CANCEL_URL
                    }
                }
            },
            "purchase_units": [{
                "invoice_id": invoice_id or str(uuid.uuid4()),
                "amount": {
                    "currency_code": currency,
                    "value": str(amount),
                    "breakdown": {
                        "item_total": {
                            "currency_code": currency,
                            "value": str(amount)
                        }
                    }
                },
                "items": items
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "PayPal-Request-Id": str(uuid.uuid4()),
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def confirm_order(self, order_id: str, payment_source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm the payment source for a PayPal order
        
        :param order_id: PayPal Order ID
        :param payment_source: Payment source details
        :return: Confirmation result
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/confirm-payment-source"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        payload = {
            "payment_source": payment_source
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Capture a previously created PayPal order
        
        :param order_id: PayPal Order ID
        :return: Capture result
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_order(self, order_id: str) -> Dict[str, Any]:
        """
        Check the status of a PayPal order
        
        :param order_id: PayPal Order ID
        :return: Order details
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

# import requests
# import uuid
# import json
# from typing import Dict, Any
# from app.core.config import settings

# class PayPalService:
#     def __init__(self):
#         self.base_url = settings.PAYPAL_BASE_URL  # e.g., 'https://api-m.sandbox.paypal.com'
#         self.client_id = settings.PAYPAL_CLIENT_ID
#         self.client_secret = settings.PAYPAL_CLIENT_SECRET
#         self.access_token = self._get_access_token()

#     def _get_access_token(self) -> str:
#         """
#         Obtain OAuth 2.0 access token from PayPal
#         """
#         url = f"{self.base_url}/v1/oauth2/token"
#         headers = {
#             "Accept": "application/json",
#             "Accept-Language": "en_US"
#         }
#         data = {"grant_type": "client_credentials"}
        
#         try:
#             response = requests.post(
#                 url, 
#                 auth=(self.client_id, self.client_secret), 
#                 headers=headers, 
#                 data=data
#             )
            
#             # Print detailed error information if request fails
#             if response.status_code != 200:
#                 print("Access Token Request Failed")
#                 print("Status Code:", response.status_code)
#                 print("Response Headers:", response.headers)
#                 print("Response Body:", response.text)
#                 raise ValueError(f"Failed to obtain access token: {response.text}")
            
#             return response.json()['access_token']
        
#         except requests.RequestException as e:
#             print(f"Request Exception when getting access token: {e}")
#             raise
#         except KeyError:
#             print("Invalid response format when getting access token")
#             raise

#     def create_order(self, 
#                      amount: float, 
#                      currency: str = 'USD', 
#                      invoice_id: str = None,
#                      items: list = None) -> Dict[str, Any]:
#         """
#         Create a PayPal order
#         """
#         url = f"{self.base_url}/v2/checkout/orders"
        
#         # Default items if not provided
#         if not items:
#             items = [{
#                 "name": "Charging Station Booking",
#                 "description": "Booking Service",
#                 "quantity": "1",
#                 "unit_amount": {
#                     "currency_code": currency,
#                     "value": f"{amount:.2f}"
#                 },
#                 "category": "DIGITAL_GOODS"
#             }]
        
#         payload = {
#             "intent": "CAPTURE",
#             "payment_source": {
#                 "paypal": {
#                     "experience_context": {
#                         "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
#                         "landing_page": "LOGIN",
#                         "shipping_preference": "NO_SHIPPING",
#                         "user_action": "PAY_NOW",
#                         "return_url": settings.PAYPAL_RETURN_URL,
#                         "cancel_url": settings.PAYPAL_CANCEL_URL
#                     }
#                 }
#             },
#             "purchase_units": [{
#                 "invoice_id": invoice_id or str(uuid.uuid4()),
#                 "amount": {
#                     "currency_code": currency,
#                     "value": f"{amount:.2f}",
#                     "breakdown": {
#                         "item_total": {
#                             "currency_code": currency,
#                             "value": f"{amount:.2f}"
#                         }
#                     }
#                 },
#                 "items": items
#             }]
#         }
        
#         headers = {
#             "Content-Type": "application/json",
#             "PayPal-Request-Id": str(uuid.uuid4()),
#             "Authorization": f"Bearer {self.access_token}"
#         }
        
#         try:
#             # Print payload for debugging
#             print("PayPal Order Payload:", json.dumps(payload, indent=2))
            
#             response = requests.post(url, json=payload, headers=headers)
            
#             # Print detailed error information if request fails
#             if response.status_code != 201:
#                 print("Order Creation Failed")
#                 print("Status Code:", response.status_code)
#                 print("Response Headers:", response.headers)
#                 print("Response Body:", response.text)
#                 raise ValueError(f"Failed to create PayPal order: {response.text}")
            
#             return response.json()
        
#         except requests.RequestException as e:
#             print(f"Request Exception when creating order: {e}")
#             raise