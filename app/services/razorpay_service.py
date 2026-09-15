import logging
from typing import Dict, Any, Optional
from app.settings import settings

logger = logging.getLogger("application")

_razorpay_client = None

def get_razorpay_client():
    global _razorpay_client
    if _razorpay_client is None:
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_SECRET:
            try:
                import razorpay
                _razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET))
            except ImportError:
                logger.error("razorpay-python package is missing in environment")
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {e}")
    return _razorpay_client


def create_astrologer_linked_account(
    astro_name: str,
    email: str,
    phone: str,
    account_number: str,
    ifsc_code: str
) -> Optional[str]:
    """
    Creates a Linked Account in Razorpay Route for the astrologer.
    Returns the Razorpay Account ID (e.g. 'acc_1234567890') if successful.
    """
    client = get_razorpay_client()
    if not client:
        logger.warning("Razorpay client not configured. Cannot create linked account.")
        return None

    try:
        account_data = {
            "name": astro_name,
            "email": email,
            "phone": phone,
            "type": "route",
            "legal_business_name": astro_name,
            "profile": {
                "category": "services",
                "sub_category": "astrology",
                "addresses": {
                    "registered": {
                        "street1": "Astrologer Address",
                        "city": "Mumbai",
                        "state": "MH",
                        "postal_code": "400001",
                        "country": "IN"
                    }
                }
            },
            "settlements": {
                "account_number": account_number,
                "ifsc_code": ifsc_code
            }
        }
        response = client.account.create(account_data)
        account_id = response.get("id")
        logger.info(f"Created Razorpay Route linked account {account_id} for astrologer {astro_name}")
        return account_id
    except Exception as e:
        logger.error(f"Error creating Razorpay Route linked account for {astro_name}: {e}")
        return None


def create_split_payment_order(
    amount_in_rupees: int,
    receipt_id: str,
    astro_razorpay_account_id: str,
    platform_commission_pct: float = 20.0
) -> Dict[str, Any]:
    """
    Creates a Razorpay order with automatic funds transfer (Route) to the Astrologer's bank account.
    """
    client = get_razorpay_client()
    total_paise = amount_in_rupees * 100
    astro_share_paise = int(total_paise * (1.0 - (platform_commission_pct / 100.0)))

    order_data = {
        "amount": total_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "transfers": [
            {
                "account": astro_razorpay_account_id,
                "amount": astro_share_paise,
                "currency": "INR",
                "on_hold": 0  # Direct settlement to astrologer's bank account
            }
        ]
    }

    if not client:
        logger.warning("Razorpay client not configured. Simulating split payment order.")
        return {
            "simulated": True,
            "id": f"order_sim_{receipt_id}",
            "amount": total_paise,
            "currency": "INR",
            "transfers": order_data["transfers"]
        }

    order = client.order.create(data=order_data)
    return order
