#server/orders/paystack_service.py
import requests
import hmac
import hashlib
from django.conf import settings
from decimal import Decimal


class PaystackService:
    """Service for interacting with Paystack API"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def _configuration_error(self):
        if self.secret_key:
            return None
        return {
            'success': False,
            'error': 'Paystack secret key is not configured. Set PAYSTACK_SECRET_KEY to enable platform payments.',
        }
    
    def initialize_transaction(self, email, amount, reference, callback_url=None, metadata=None):
        """
        Initialize a Paystack transaction
        
        Args:
            email: Customer email
            amount: Amount in kobo (Naira * 100)
            reference: Unique transaction reference
            callback_url: URL to redirect after payment
            metadata: Additional data to attach to transaction
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/transaction/initialize"
        
                                                         
        if isinstance(amount, (int, float, Decimal)):
            amount_in_kobo = int(float(amount) * 100)
        else:
            amount_in_kobo = int(amount)
        
        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'currency': 'NGN',
        }
        
        if callback_url:
            payload['callback_url'] = callback_url
        
        if metadata:
            payload['metadata'] = metadata
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=self.headers,
                timeout=30               
            )
            response.raise_for_status()
            
            data = response.json()
            
                                                      
            if not data.get('status'):
                return {
                    'success': False,
                    'error': data.get('message', 'Unknown error from Paystack')
                }
            
            return {
                'success': True,
                'data': data
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout. Please try again.'
            }
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('message', str(e))
                except:
                    pass
            
            return {
                'success': False,
                'error': error_message
            }
    
    def verify_transaction(self, reference):
        """
        Verify a Paystack transaction
        
        Args:
            reference: Transaction reference to verify
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            response = getattr(e, 'response', None)
            return {
                'success': False,
                'error': str(e),
                'response': response.json() if response is not None and hasattr(response, 'json') else None
            }
    
    def list_transactions(self, page=1, per_page=50):
        """
        List all transactions
        
        Args:
            page: Page number
            per_page: Number of transactions per page
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/transaction"
        params = {
            'page': page,
            'perPage': per_page
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def fetch_transaction(self, transaction_id):
        """
        Fetch details of a specific transaction
        
        Args:
            transaction_id: Transaction ID
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/transaction/{transaction_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def charge_authorization(self, authorization_code, email, amount, reference):
        """
        Charge a customer using a saved authorization
        
        Args:
            authorization_code: Authorization code from previous transaction
            email: Customer email
            amount: Amount in kobo
            reference: Unique transaction reference
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/transaction/charge_authorization"
        
                                
        if isinstance(amount, (int, float, Decimal)):
            amount_in_kobo = int(float(amount) * 100)
        else:
            amount_in_kobo = int(amount)
        
        payload = {
            'authorization_code': authorization_code,
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'currency': 'NGN'
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_refund(self, transaction_reference, amount=None):
        """
        Create a refund for a transaction
        
        Args:
            transaction_reference: Reference of transaction to refund
            amount: Amount to refund (in kobo). If not provided, full amount is refunded
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/refund"
        
        payload = {
            'transaction': transaction_reference
        }
        
        if amount:
            if isinstance(amount, (int, float, Decimal)):
                amount_in_kobo = int(float(amount) * 100)
            else:
                amount_in_kobo = int(amount)
            payload['amount'] = amount_in_kobo
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_refunds(self, reference=None):
        """
        List all refunds
        
        Args:
            reference: Filter by transaction reference (optional)
        
        Returns:
            dict: Response from Paystack API
        """
        config_error = self._configuration_error()
        if config_error:
            return config_error

        url = f"{self.base_url}/refund"
        
        params = {}
        if reference:
            params['reference'] = reference
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def verify_webhook_signature(request_body, signature):
        """
        Verify that webhook request is from Paystack
        
        Args:
            request_body: Raw request body
            signature: X-Paystack-Signature header value
        
        Returns:
            bool: True if signature is valid
        """
        webhook_secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', '')
        if not webhook_secret or not signature:
            return False

        computed_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            request_body,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
