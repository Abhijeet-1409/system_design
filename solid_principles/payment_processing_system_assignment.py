# =============================================================================
# ASSIGNMENT: Payment Processing System
# =============================================================================
# Scenario:
# Build a payment processing system for the same e-commerce platform.
# When a customer checks out, the system should process payment through
# their chosen payment method.
#
# Requirements:
# Design classes that handle payment processing for an order.
# Your system should support Credit Card and UPI payments, and be easy
# to extend with new methods (e.g. NetBanking, Wallet) later.
#
# What to implement:
# 1. A Cart class with items and total amount
# 2. A PaymentProcessor that processes payment for a cart
# 3. At least two payment methods: CreditCardPayment and UPIPayment
# 4. A Receipt class that generates a receipt after successful payment
#
# SOLID Principles to follow:
# S - Each class has one job. Cart holds items. Receipt only formats
#     receipt data. PaymentProcessor only coordinates — it does not
#     know HOW to charge a card or UPI.
#
# O - Adding NetBankingPayment later should need zero edits to
#     PaymentProcessor or any existing payment class.
#
# L - CreditCardPayment and UPIPayment must be safely swappable
#     wherever a PaymentMethod is expected. No method should raise
#     NotImplementedError or behave unexpectedly.
#
# I - A PaymentMethod should only have payment-related methods.
#     Don't force it to implement receipt generation or cart logic.
#
# D - PaymentProcessor must depend on a PaymentMethod abstraction,
#     not on CreditCardPayment directly. The concrete class is
#     injected from outside.
#
# Bonus:
# Add a SplitPayment method that charges two different payment
# methods (e.g. half on card, half on UPI) — without modifying
# any existing class.
#
# Expected usage:
#
# cart = Cart()
# cart.add_item("Shoes", 2000)
# cart.add_item("Belt", 500)
#
# processor = PaymentProcessor(CreditCardPayment("4111-XXXX", "Ravi"))
# receipt = processor.process(cart)
# receipt.print_receipt()
#
# Output:
# Processing ₹2500 via Credit Card (4111-XXXX)
# Payment successful.
# ----------------------------
# Receipt for Ravi
# Items: Shoes, Belt
# Total: ₹2500
# Paid via: Credit Card
# ----------------------------

# =============================================================================
# ASSIGNMENT: Payment Processing System — Final Solution
# =============================================================================

from abc import ABC, abstractmethod
from time import sleep
from random import randint
from functools import reduce
from enum import Enum


# -----------------------------------------------------------------------------
# ENUMS & EXCEPTIONS
# -----------------------------------------------------------------------------

# [OCP] — New payment labels can be added here without touching any class
class PaymentLabel(Enum):
    CREDIT_CARD = "Credit Card"
    UPI         = "UPI"
    NET_BANKING = "Net Banking"
    WALLET      = "Wallet"
    SPLIT       = "Split"


# [SRP] — Each exception has one job: describe one specific failure
class EmptyCartException(Exception):
    def __init__(self):
        super().__init__("Cart is empty")

class PaymentFailureException(Exception):
    def __init__(self):
        super().__init__("Payment Failure")

class SplitPaymentException(Exception):
    def __init__(self):
        super().__init__("Split payment requires at least 2 payment methods")


# -----------------------------------------------------------------------------
# SIMULATOR
# -----------------------------------------------------------------------------

# [SRP] — PaymentSimulator has one job: simulate network delay and random failure
#         It is NOT part of PaymentMethod — simulation is infrastructure concern,
#         not a payment concern
class PaymentSimulator:
    def simulate(self):
        sleep(3)
        if not randint(1, 10) > 5:
            raise PaymentFailureException()
        return True


# -----------------------------------------------------------------------------
# CART
# -----------------------------------------------------------------------------

# [SRP] — CartItem has one job: hold item data and calculate its own cost
class CartItem:
    def __init__(self, name: str, price: int, quantity: int):
        self.name     = name
        self.price    = price
        self.quantity = quantity

    def get_cost(self) -> int:
        return self.price * self.quantity


# [SRP] — Cart has one job: hold items and calculate total cost
#          It knows nothing about payments, receipts, or checkout
class Cart:
    def __init__(self, items: list[CartItem] | None = None):
        self.items = items if items is not None else []

    def add_item(self, name: str, price: int, quantity: int):
        self.items.append(CartItem(name, price, quantity))

    def _accumulate_cost(self, total: int, item: CartItem) -> int:
        return total + item.get_cost()

    def get_total_cost(self) -> int:
        if not self.items:
            raise EmptyCartException()
        return reduce(self._accumulate_cost, self.items, 0)


# -----------------------------------------------------------------------------
# ABSTRACTIONS
# -----------------------------------------------------------------------------

# [DIP] — High-level classes (PaymentProcessor) depend on this abstraction,
#          not on any concrete payment class
# [ISP] — Only payment-related methods here. No receipt, no cart logic forced
#          on implementors
# [OCP] — New payment methods extend this without modifying it
class PaymentMethod(ABC):

    # [LSP] — Every subclass must implement this and actually process payment.
    #          No subclass may raise "not supported" here
    @abstractmethod
    def initiate_payment(self, amount: int) -> None:
        pass

    # [SRP] — label is identity of the payment method, belongs here naturally
    @property
    @abstractmethod
    def label(self) -> str:
        pass


# [DIP] — CheckoutService depends on this abstraction, not on SimpleReceipt
# [ISP] — Only receipt-related method here. Not mixed with payment or cart logic
class Receipt(ABC):
    @abstractmethod
    def print_receipt(self, name: str, cart: Cart, payment_label: str) -> None:
        pass


# -----------------------------------------------------------------------------
# PAYMENT METHOD IMPLEMENTATIONS
# -----------------------------------------------------------------------------

# [OCP] — Added without modifying PaymentMethod or any other existing class
# [LSP] — Safely substitutable wherever PaymentMethod is expected
class CreditCardPayment(PaymentMethod):
    def __init__(
        self,
        card_holder_name: str,
        card_number: str,
        expiry_date: str,
        cvv: int,
        bank_name: str,
        available_limit: float
    ):
        self.card_holder_name = card_holder_name
        self.card_number      = card_number
        self.expiry_date      = expiry_date
        self.cvv              = cvv
        self.bank_name        = bank_name
        self.available_limit  = available_limit

    def initiate_payment(self, amount: int) -> None:
        print(
            f"Initiating payment of ₹{amount} via Credit Card "
            f"ending with {self.card_number[-4:]}"
        )

    @property
    def label(self) -> str:
        return PaymentLabel.CREDIT_CARD.value

    def __repr__(self):
        return "Credit Card"


# [OCP] — Added without modifying PaymentMethod or any other existing class
# [LSP] — Safely substitutable wherever PaymentMethod is expected
class UpiPayment(PaymentMethod):
    def __init__(
        self,
        upi_id: str,
        mobile_number: str,
        provider: str,
        linked_bank: str
    ):
        self.upi_id        = upi_id
        self.mobile_number = mobile_number
        self.provider      = provider
        self.linked_bank   = linked_bank

    def initiate_payment(self, amount: int) -> None:
        print(f"Initiating payment of ₹{amount} via UPI — {self.provider}")

    @property
    def label(self) -> str:
        return PaymentLabel.UPI.value

    def __repr__(self):
        return "UPI"


# [OCP] — Added without modifying PaymentMethod or any other existing class
# [LSP] — Safely substitutable wherever PaymentMethod is expected
class NetBankingPayment(PaymentMethod):
    def __init__(
        self,
        bank_name: str,
        account_holder: str,
        account_number: str,
        ifsc_code: str,
        username: str
    ):
        self.bank_name        = bank_name
        self.account_holder   = account_holder
        self.account_number   = account_number
        self.ifsc_code        = ifsc_code
        self.username         = username

    def initiate_payment(self, amount: int) -> None:
        print(f"Initiating payment of ₹{amount} via Net Banking — {self.bank_name}")

    @property
    def label(self) -> str:
        return PaymentLabel.NET_BANKING.value

    def __repr__(self):
        return "Net Banking"


# [OCP] — Added without modifying PaymentMethod or any other existing class
# [LSP] — Safely substitutable wherever PaymentMethod is expected
class WalletPayment(PaymentMethod):
    def __init__(
        self,
        wallet_name: str,
        mobile_number: str,
        wallet_id: str,
        balance: float
    ):
        self.wallet_name   = wallet_name
        self.mobile_number = mobile_number
        self.wallet_id     = wallet_id
        self.balance       = balance

    def initiate_payment(self, amount: int) -> None:
        print(f"Initiating payment of ₹{amount} via Wallet — {self.wallet_name}")

    @property
    def label(self) -> str:
        return PaymentLabel.WALLET.value

    def __repr__(self):
        return "Wallet"


# [OCP] — Bonus: added without modifying ANY existing class
# [LSP] — Safely substitutable wherever PaymentMethod is expected.
#          PaymentProcessor has no idea this is a split — it just calls
#          initiate_payment like any other method
# [SRP] — SplitPayment only knows how to divide and delegate.
#          It does not simulate, receipt, or checkout
class SplitPayment(PaymentMethod):
    def __init__(self, payment_methods: list[PaymentMethod]):
        if len(payment_methods) < 2:
            raise SplitPaymentException()
        self.payment_methods = payment_methods

    def initiate_payment(self, amount: int) -> None:
        # [SRP] — integer division keeps amount as int, consistent with type contract
        split_amount = amount // len(self.payment_methods)
        print(
            f"Splitting ₹{amount} across {len(self.payment_methods)} methods "
            f"— ₹{split_amount} each:"
        )
        for method in self.payment_methods:
            method.initiate_payment(split_amount)

    @property
    def label(self) -> str:
        # Describes all inner methods for the receipt
        inner_labels = " + ".join(m.label for m in self.payment_methods)
        return f"{PaymentLabel.SPLIT.value} ({inner_labels})"

    def __repr__(self):
        return "Split Payment"


# -----------------------------------------------------------------------------
# PROCESSOR
# -----------------------------------------------------------------------------

# [SRP] — PaymentProcessor has one job: coordinate payment initiation and
#          simulation. It does not generate receipts or handle checkout flow
# [DIP] — Depends on PaymentMethod abstraction, not any concrete class.
#          PaymentSimulator injected from outside, not created internally
class PaymentProcessor:
    def __init__(self, payment_method: PaymentMethod, payment_simulator: PaymentSimulator):
        self.payment_method    = payment_method
        self.payment_simulator = payment_simulator

    def process(self, cart: Cart) -> None:
        # amount extracted once here — payment methods receive a number,
        # not a Cart object. They have no reason to know Cart exists
        amount = cart.get_total_cost()
        self.payment_method.initiate_payment(amount)
        self.payment_simulator.simulate()
        print("Payment successful.")

    # [Law of Demeter] — Exposes label through its own method so callers
    #                    never reach inside to access payment_method directly
    def get_payment_label(self) -> str:
        return self.payment_method.label


# -----------------------------------------------------------------------------
# RECEIPT
# -----------------------------------------------------------------------------

# [SRP] — SimpleReceipt has one job: format and print receipt data
#          It knows nothing about payments, cart logic, or checkout flow
# [OCP] — New receipt formats (e.g. DetailedReceipt) extend Receipt without
#          modifying SimpleReceipt
class SimpleReceipt(Receipt):
    def print_receipt(self, name: str, cart: Cart, payment_label: str) -> None:
        items_str = ", ".join(
            f"{item.name} x{item.quantity}" for item in cart.items
        )
        print(f"""
        ========== RECEIPT ==========
        Customer  : {name}
        Items     : {items_str}
        Total     : ₹{cart.get_total_cost()}
        Paid via  : {payment_label}
        =============================""")


# -----------------------------------------------------------------------------
# CHECKOUT SERVICE
# -----------------------------------------------------------------------------

# [SRP] — CheckoutService has one job: coordinate the full checkout flow.
#          It contains no payment logic, no receipt formatting, no simulation
# [DIP] — Depends on PaymentProcessor and Receipt abstractions.
#          Both injected from outside
class CheckoutService:
    def __init__(self, payment_processor: PaymentProcessor, receipt_generator: Receipt):
        self.payment_processor  = payment_processor
        self.receipt_generator  = receipt_generator

    def checkout(self, name: str, cart: Cart) -> None:
        print(f"Initiating checkout for {name}...")
        try:
            # [Law of Demeter] — asks processor for label, never reaches inside it
            payment_label = self.payment_processor.get_payment_label()
            self.payment_processor.process(cart)
            print("Generating receipt...")
            self.receipt_generator.print_receipt(name, cart, payment_label)

        except EmptyCartException as e:
            print(f"Checkout failed: {e}")
        except PaymentFailureException as e:
            print(f"Checkout failed: {e}")
        except Exception as e:
            print(f"Unexpected error during checkout: {e}")
        finally:
            print("Checkout process completed.")


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    data = [
        ("Ravi", Cart([CartItem("Shoes", 2000, 1), CartItem("Belt", 500, 1)]),
            CreditCardPayment("Ravi Kumar", "4111-XXXX-XXXX-1234", "12/25", 123, "HDFC Bank", 5000)),

        ("Priya", Cart([CartItem("Watch", 3000, 1)]),
            UpiPayment("priya@upi", "9876543210", "Google Pay", "ICICI Bank")),

        ("Amit", Cart(),  # empty cart — tests EmptyCartException
            CreditCardPayment("Amit Singh", "4111-XXXX-XXXX-5678", "11/24", 456, "SBI Bank", 10000)),

        ("Sneha", Cart([CartItem("Bag", 1500, 2)]),
            NetBankingPayment("Axis Bank", "Sneha Sharma", "1234567890", "UTIB0000123", "sneha_axis")),

        ("Rahul", Cart([CartItem("Headphones", 2500, 1)]),
            WalletPayment("Paytm Wallet", "9123456780", "rahul_paytm_001", 3000)),

        # [OCP] — SplitPayment added here. Zero changes to any existing class above
        ("Karan", Cart([CartItem("Laptop", 50000, 1)]),
            SplitPayment([
                CreditCardPayment("Karan Mehta", "4111-XXXX-XXXX-9999", "10/26", 789, "HDFC Bank", 30000),
                UpiPayment("karan@upi", "9988776655", "PhonePe", "Kotak Bank")
            ])),
    ]

    # [SRP] — stateless objects created once outside the loop, not per customer
    receipt_generator  = SimpleReceipt()
    payment_simulator  = PaymentSimulator()

    for name, cart, payment_method in data:
        print("\n" + "=" * 50)
        payment_processor = PaymentProcessor(payment_method, payment_simulator)
        checkout_service  = CheckoutService(payment_processor, receipt_generator)
        checkout_service.checkout(name, cart)