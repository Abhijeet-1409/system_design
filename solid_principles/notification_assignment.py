# =============================================================================
# ASSIGNMENT: Notification Service
# =============================================================================
# Scenario:
# Build a simple notification system for an e-commerce order.
#
# Requirements:
# Design classes that handle sending notifications when an order is placed.
# Your system should support email and SMS notifications, and be easy to
# extend with new channels (e.g. push notifications) later.
#
# What to implement:
# 1. An Order class with basic order info (id, item, amount)
# 2. A NotificationService that sends notifications
# 3. At least two notification channels: EmailNotifier and SmsNotifier
#
# SOLID Principles to follow:
# S - Single Responsibility : Each class does one thing. Order holds data.
#                             EmailNotifier only sends email.
#                             No class mixes concerns.
# O - Open/Closed           : Adding a PushNotifier later requires a new class,
#                             not editing existing ones.
# L - Liskov Substitution   : EmailNotifier and SmsNotifier should be
#                             interchangeable wherever a Notifier is expected.
# I - Interface Segregation : Don't force a notifier to implement methods it
#                             doesn't need (e.g. don't lump logToFile() into
#                             the notifier interface).
# D - Dependency Inversion  : NotificationService should depend on an
#                             abstraction (interface/abstract class),
#                             not on EmailNotifier directly.
#
# Bonus:
# Add a MultiChannelNotifier that sends via all registered channels at once
# without touching any existing notifier class.
# =============================================================================

from abc import ABC, abstractmethod

# A factory function to generate unique order IDs
# SRP: ID generation logic is isolated here, not mixed into the Order class
def create_counter():
    count = 0
    def counter():
        nonlocal count
        count += 1
        return count
    return counter

order_counter = create_counter()


# SRP: Item is only responsible for holding product data
class Item():
    def __init__(self, name: str, price: int):
        self.name = name
        self.price = price


# SRP: Order is only responsible for holding order data and computing its total
# It does NOT handle notifications, logging, or anything else
class Order():
    def __init__(self, item: Item, quantity: int):
        self.id = order_counter()
        self.item = item
        self.quantity = quantity

    def total_cost(self):
        return self.item.price * self.quantity

    def __repr__(self):
        return f"{self.id}"


# DIP: High-level modules (NotificationService) depend on this abstraction,
# not on concrete notifiers like EmailNotifier or SmsNotifier
# OCP: New notifiers can be added by implementing this interface,
# without modifying any existing class
# LSP: Any class implementing this can be used wherever Notifier is expected
class Notifier(ABC):
    @abstractmethod
    def notify(self, order: Order):
        pass


# ISP: Receipt-related behavior is extracted into its own interface
# so that notifiers that don't need it (Email, Push) are not forced to implement it
class Receipt(ABC):
    @abstractmethod
    def get_order_receipt(self, order: Order):
        pass


# SRP: Only responsible for SMS notification logic
# LSP: Can replace any Notifier without breaking behavior
# ISP: Implements Receipt separately because SMS genuinely supports it
class SmsNotifier(Notifier, Receipt):
    def get_order_receipt(self, order: Order):
        name = order.item.name
        price = order.item.price
        quantity = order.quantity
        total_cost = order.total_cost()
        receipt = f"""
        ========== RECEIPT ==========
        Item Name : {name}
        Price     : ₹{price}
        Quantity  : {quantity}
        -----------------------------
        Total Cost: ₹{total_cost}
        =============================
        """
        return receipt

    def notify(self, order: Order):
        receipt = self.get_order_receipt(order)
        print(f"Send sms notification for order with order id : {order} ...")
        print(f"""
        Sending order receipt ...
        {receipt}
        """)


# SRP: Only responsible for email notification logic
# ISP: Does NOT implement Receipt — it doesn't need it, and isn't forced to
# LSP: Can replace any Notifier without breaking behavior
class EmailNotifier(Notifier):
    def notify(self, order: Order):
        print(f"Send email notification for order with order id : {order} ...")


# SRP: Only responsible for push notification logic
# OCP: Added as a new class without touching any existing code — open/closed in action
# LSP: Can replace any Notifier without breaking behavior
class PushNotifier(Notifier):
    def notify(self, order: Order):
        print(f"Send web push notification for order with order id : {order} ...")


# SRP: Only responsible for delegating to multiple notifiers
# OCP: New channels can be added by passing them in — no code change needed here
# LSP: Is itself a Notifier, so it works anywhere a Notifier is expected (Composite pattern)
# DIP: Depends on the Notifier abstraction, not on concrete notifier classes
class MultiChannelNotifier(Notifier):
    def __init__(self, notifiers: list[Notifier] = None):  # Fixed mutable default arg
        self.notifiers = notifiers if notifiers is not None else []

    def notify(self, order: Order):
        print(f"Triggering all notifiers for order with order id : {order} ...")
        for notifier in self.notifiers:
            notifier.notify(order)


# SRP: Only responsible for triggering the notification — nothing else
# DIP: Depends on the Notifier abstraction (constructor injection),
# not on any specific notifier — you can swap any notifier in without changing this class
class NotificationService():
    def __init__(self, notifier: Notifier):
        self.notifier = notifier

    def send(self, order: Order):
        print(f"Sending all notification for order with order id : {order} ...")
        self.notifier.notify(order)


if __name__ == "__main__":
    orders = [
        Order(Item("Tshirt", 100), 2),
        Order(Item("Jeans", 150), 3),
        Order(Item("Glasses", 50), 1)
    ]

    # DIP in action: NotificationService doesn't know or care what's inside here
    # OCP in action: Adding PushNotifier required zero changes to existing classes
    multi_channel_notifier = MultiChannelNotifier([
        SmsNotifier(),
        EmailNotifier(),
        PushNotifier()
    ])

    order_notification = NotificationService(multi_channel_notifier)

    for order in orders:
        print("########################################\n")
        order_notification.send(order)
        print("\n#########################################")
        print("\n\n")