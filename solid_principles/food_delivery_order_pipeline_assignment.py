# =============================================================================
# ASSIGNMENT: Food Delivery Order Pipeline
# =============================================================================
# Scenario:
# Build the backend pipeline for a food delivery app (think Swiggy/Zomato).
# When a customer places a food order, it goes through multiple stages:
# validation, pricing, assignment to a delivery agent, and notification.
#
# This assignment is harder because a single order flows through
# multiple independent systems — and each system must stay decoupled.
#
# What to implement:
# 1. A FoodOrder class (customer, restaurant, items, delivery address)
# 2. An OrderValidator that checks if the order is valid
#    (e.g. items not empty, address provided, restaurant is open)
# 3. A PricingEngine that calculates total with taxes and delivery fee
#    - Support at least two strategies: StandardPricing and PeakHourPricing
# 4. A DeliveryAssigner that assigns a delivery agent
#    - Support at least two strategies: NearestAgent and RandomAgent
# 5. A Notifier (reuse the idea from your previous assignment)
#    - Notify customer and restaurant separately
# 6. An OrderPipeline that runs all stages in sequence
#
# SOLID Principles to follow:
# S - OrderValidator only validates. PricingEngine only calculates price.
#     DeliveryAssigner only assigns agents. OrderPipeline only coordinates.
#     No class does two of these jobs.
#
# O - Adding a new pricing strategy (e.g. FestivalPricing) or a new
#     delivery strategy (e.g. PriorityAgent) should require zero edits
#     to OrderPipeline or any existing class.
#
# L - All PricingStrategy subclasses must return a valid numeric price.
#     All DeliveryStrategy subclasses must return a valid agent name.
#     No subclass should throw "not supported" for its core method.
#
# I - PricingStrategy should only have pricing methods. Don't mix
#     delivery logic into it. Keep each abstraction focused.
#
# D - OrderPipeline must receive all its dependencies (validator,
#     pricing engine, assigner, notifier) from outside via constructor.
#     It must not create any of them internally.
#
# Bonus:
# Add an OrderLogger that logs each stage result to a list (simulating
# a database). Plug it into the pipeline without modifying OrderPipeline.
# Hint: think about where logging fits without violating SRP.
#
# Expected usage:
#
# order = FoodOrder(
#     customer="Ayesha",
#     restaurant="Bombay Kitchen",
#     items=["Biryani", "Raita"],
#     address="Andheri West, Mumbai"
# )
#
# pipeline = OrderPipeline(
#     validator=OrderValidator(),
#     pricing=PricingEngine(PeakHourPricing()),
#     assigner=DeliveryAssigner(NearestAgent()),
#     notifier=MultiChannelNotifier([SmsNotifier(), EmailNotifier()])
# )
#
# pipeline.run(order)
#
# Output:
# [Validation] Order is valid.
# [Pricing] Total: ₹485 (Peak hour surcharge applied)
# [Delivery] Assigned to: Ramesh (2.1 km away)
# [Notification] SMS sent to Ayesha
# [Notification] Email sent to Bombay Kitchen

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Any
from random import choice, randint
from enum import Enum
from time import sleep


# =============================================================================
# ENUMS
# =============================================================================

# [OCP] — New agents added here without touching any strategy class
class DeliveryAgent(Enum):
    RAMESH = "Ramesh"
    SURESH = "Suresh"
    RAJESH = "Rajesh"
    MANISH = "Manish"

# [OCP] — New surcharge windows added here without touching PeakHourPricing
class PeakHourSurcharge(Enum):
    LUNCH      = 0.05   # 5%
    DINNER     = 0.10   # 10%
    LATE_NIGHT = 0.15   # 15%

# [OCP] — New strategy types registered here to extend MultiPricingStrategy
class PricingStrategyType(Enum):
    STANDARD  = "standard"
    PEAK_HOUR = "peak_hour"

# [OCP] — New menu items added here without touching any pricing or order class
class MenuItem(Enum):
    BIRYANI        = "Biryani"
    RAITA          = "Raita"
    BUTTER_CHICKEN = "Butter Chicken"
    NAAN           = "Naan"
    PANEER_TIKKA   = "Paneer Tikka"
    VEG_BIRYANI    = "Veg Biryani"
    DAL_MAKHANI    = "Dal Makhani"
    JEERA_RICE     = "Jeera Rice"
    GULAB_JAMUN    = "Gulab Jamun"
    RAS_MALAI      = "Ras Malai"


# =============================================================================
# CONFIGURATION — data only, no logic
# =============================================================================

# [OCP] — Adding a new item only requires a new entry here
MENU: Dict[MenuItem, int] = {
    MenuItem.BIRYANI:        300,
    MenuItem.RAITA:           50,
    MenuItem.BUTTER_CHICKEN: 350,
    MenuItem.NAAN:            40,
    MenuItem.PANEER_TIKKA:   250,
    MenuItem.VEG_BIRYANI:    280,
    MenuItem.DAL_MAKHANI:    200,
    MenuItem.JEERA_RICE:     150,
    MenuItem.GULAB_JAMUN:    100,
    MenuItem.RAS_MALAI:      120,
}

# [OCP] — New distance range → agent mappings added here
DELIVERY_AGENTS: Dict[Tuple[int, int], DeliveryAgent] = {
    (0,  5):  DeliveryAgent.RAMESH,
    (5,  10): DeliveryAgent.SURESH,
    (10, 15): DeliveryAgent.RAJESH,
    (15, 20): DeliveryAgent.MANISH,
}

# [OCP] — New peak windows added here without touching PeakHourPricing logic
PEAK_HOURS_SURCHARGES: Dict[Tuple[int, int], PeakHourSurcharge] = {
    (1130, 1400): PeakHourSurcharge.LUNCH,
    (1830, 2130): PeakHourSurcharge.DINNER,
    (2200, 2359): PeakHourSurcharge.LATE_NIGHT,
}

# [OCP] — Dependency map: adding FestivalPricing only needs a new entry here
PRICING_STRATEGIES_DEPENDENCY: Dict[PricingStrategyType, PricingStrategyType] = {
    PricingStrategyType.PEAK_HOUR: PricingStrategyType.STANDARD,
}

# [OCP] — Base arguments per strategy type — extend without editing factory
PRICING_STRATEGIES_BASE_ARGUMENTS: Dict[PricingStrategyType, Dict[str, Any]] = {
    PricingStrategyType.STANDARD: {
        "tax_rate":       0.05,
        "delivery_fee":   30,
        "gst_percentage": 0.18,
        "packaging_fee":  20,
        "platform_fee":   0.02,
    },
    PricingStrategyType.PEAK_HOUR: {
        "tax_rate":              0.05,
        "delivery_fee":          30,
        "gst_percentage":        0.18,
        "packaging_fee":         20,
        "platform_fee":          0.02,
        "default_surcharge":     0.02,
        "base_strategy":         None,   # filled by factory
        "peak_hours_surcharges": PEAK_HOURS_SURCHARGES,
    },
}


# =============================================================================
# UTILITIES
# =============================================================================

# [SRP] — Counter closure: one job, generate incrementing IDs
def create_counter():
    count = 0
    def counter():
        nonlocal count
        count += 1
        return count
    return counter

# [SRP] — Pure formatting utility, no side effects
def format_time(time: int) -> str:
    return f"{time // 100:02}:{time % 100:02}"

# [SRP] — Pure time arithmetic utility: adds minutes to a 24hr int safely
def add_minutes(time: int, minutes: int) -> int:
    total_minutes = (time // 100) * 60 + (time % 100) + minutes
    return (total_minutes // 60) * 100 + (total_minutes % 60)

order_id_generator = create_counter()
bill_id_generator  = create_counter()


# =============================================================================
# DATACLASSES — pure data containers, no business logic
# =============================================================================

# [SRP] — Holds restaurant data only
@dataclass
class Restaurant:
    name:             str
    start_time:       int    # 24hr int, e.g. 1100 = 11:00 AM
    end_time:         int
    email:            str
    open_on_weekends: bool

# [SRP] — Holds order data only. Knows nothing about pricing or delivery
@dataclass
class FoodOrder:
    customer:      str
    restaurant:    Restaurant
    items:         List[MenuItem]
    address:       str
    day_of_week:   str
    time_of_order: int
    distance_km:   float
    id:            int = field(default_factory=order_id_generator)

# [SRP] — Holds billing breakdown only
@dataclass
class Bill:
    order_id:     int
    base_price:   float
    tax:          float
    gst:          float
    delivery_fee: float
    packaging_fee: float
    platform_fee: float
    total_price:  float
    id:           int = field(default_factory=bill_id_generator)

# [LSP] — PeakBill extends Bill honestly: it has everything Bill has + surcharge
#          Wherever a Bill is expected, PeakBill substitutes safely
@dataclass
class PeakBill(Bill):
    peak_hour_surcharge: float = field(kw_only=True)

# [SRP] — Parameter object: bundles notification data so notify() stays clean
#          Notifiers don't need 5 separate parameters — one context object
@dataclass
class NotificationContext:
    order:          FoodOrder
    delivery_agent: DeliveryAgent
    bill:           Optional[Bill] = field(default=None)

# [SRP] — Parameter object: bundles pricing config so strategy constructors stay clean
@dataclass
class PricingContext:
    tax_rate:              float
    delivery_fee:          int
    gst_percentage:        float
    packaging_fee:         int
    platform_fee:          float
    default_surcharge:     Optional[float]                              = field(default=None)
    base_strategy:         Optional[PricingStrategy]                    = field(default=None)
    peak_hours_surcharges: Optional[Dict[Tuple[int, int], PeakHourSurcharge]] = field(default=None)


# =============================================================================
# EXCEPTIONS
# =============================================================================

# [SRP] — Each exception describes exactly one failure type
class BaseFoodDeliveryException(Exception):
    def __init__(self, message="Base food delivery exception"):
        super().__init__(message)

class ValidationException(BaseFoodDeliveryException):
    def __init__(self, message="Order validation failed"):
        super().__init__(message)

class DeliveryException(BaseFoodDeliveryException):
    def __init__(self, message="Delivery assignment failed"):
        super().__init__(message)


# =============================================================================
# ABSTRACTIONS
# =============================================================================

# [DIP] — OrderValidator depends on this, not on a concrete implementation
# [ISP] — Only validation method here — no pricing, no delivery mixed in
class Validator(ABC):
    @abstractmethod
    def validate(self, order: FoodOrder):
        pass

# [DIP] — PricingEngine depends on this abstraction, not on StandardPricing
# [ISP] — Only pricing method here
# [OCP] — New strategies extend this without modifying it
class PricingStrategy(ABC):
    @abstractmethod
    def calculate_price(self, order: FoodOrder):
        pass

# [DIP] — DeliveryAssigner depends on this, not on NearestAgentStrategy
# [ISP] — Only delivery assignment method here
# [OCP] — New strategies extend this without modifying it
class DeliveryStrategy(ABC):
    @abstractmethod
    def assign_agent(self, order: FoodOrder):
        pass

# [DIP] — OrderPipeline depends on this, not on EmailNotifier or SmsNotifier
# [ISP] — Only notification method here
# [OCP] — New notifiers extend this without modifying it
class Notifier(ABC):
    @abstractmethod
    def notify(self, ctx: NotificationContext):
        pass

# [ISP] — Separates restaurant notification contract from customer notification
#          Forces subclasses to be explicit about which channel they serve
class RestaurantNotifier(Notifier, ABC):
    @abstractmethod
    def notify(self, ctx: NotificationContext):
        pass

# [ISP] — Same separation on the customer side
class CustomerNotifier(Notifier, ABC):
    @abstractmethod
    def notify(self, ctx: NotificationContext):
        pass

# [DIP] — OrderLogger depends on this, not on MySQLDatabase directly
# [ISP] — Only insert method — no query, no delete forced on implementors
class Database(ABC):
    @abstractmethod
    def insert(self, message: str):
        pass

# [DIP] — OrderPipeline depends on this abstraction for logging
# [ISP] — Only log method here
class Logger(ABC):
    @abstractmethod
    def log(self, stage: str, message: str):
        pass


# =============================================================================
# VALIDATOR
# =============================================================================

# [SRP] — One job: validate a FoodOrder. No pricing, no notification logic
# [LSP] — Safely substitutable wherever Validator is expected
class OrderValidator(Validator):
    def validate(self, order: FoodOrder):
        if not order.items:
            raise ValidationException("Order must contain at least one item.")

        if not order.address.strip():
            raise ValidationException("Delivery address is required.")

        restaurant = order.restaurant
        if not (restaurant.start_time <= order.time_of_order < restaurant.end_time):
            raise ValidationException(f"{restaurant.name} is closed at the time of order.")

        if order.day_of_week in ["Saturday", "Sunday"] and not restaurant.open_on_weekends:
            raise ValidationException(f"{restaurant.name} is closed on weekends.")

        if order.distance_km > 20:
            raise ValidationException("Delivery address is too far from the restaurant.")

        return (True, "Order is valid.")


# =============================================================================
# PRICING STRATEGIES
# =============================================================================

# [SRP] — Knows only standard pricing math. No surcharge logic, no delivery logic
# [LSP] — Returns a valid Bill for any FoodOrder — no surprises
# [OCP] — Extended by PeakHourPricing via composition, not modified
class StandardPricing(PricingStrategy):
    def __init__(self, ctx: PricingContext):
        self.tax_rate       = ctx.tax_rate
        self.delivery_fee   = ctx.delivery_fee
        self.gst_percentage = ctx.gst_percentage
        self.packaging_fee  = ctx.packaging_fee
        self.platform_fee   = ctx.platform_fee

    def calculate_price(self, order: FoodOrder) -> Bill:
        base_price   = sum(MENU[item] for item in order.items)
        tax          = base_price * self.tax_rate
        gst          = base_price * self.gst_percentage
        platform_fee = base_price * self.platform_fee
        total        = base_price + tax + gst + self.delivery_fee + self.packaging_fee + platform_fee
        return Bill(
            order_id=order.id,
            base_price=base_price,
            tax=tax,
            gst=gst,
            delivery_fee=self.delivery_fee,
            packaging_fee=self.packaging_fee,
            platform_fee=platform_fee,
            total_price=round(total, 2),
        )

# [SRP] — Knows only peak-hour surcharge logic. Delegates base calculation to
#          its injected base_strategy
# [OCP] — Composition over inheritance: wraps any PricingStrategy as its base.
#          Adding FestivalPricing follows the same pattern — no edits here
# [DIP] — Depends on PricingStrategy abstraction for base_strategy, not
#          on StandardPricing directly
class PeakHourPricing(PricingStrategy):
    def __init__(self, ctx: PricingContext):
        ctx_dict = asdict(ctx)
        missing  = [k for k, v in ctx_dict.items() if v is None]
        if missing:
            raise ValueError(f"Missing PricingContext fields: {', '.join(missing)}")
        if not ctx.peak_hours_surcharges:
            raise ValueError("peak_hours_surcharges cannot be empty")
        self.base_strategy         = ctx.base_strategy
        self.peak_hours_surcharges = ctx.peak_hours_surcharges
        self.default_surcharge     = ctx.default_surcharge

    def calculate_price(self, order: FoodOrder) -> Bill:
        base_bill  = self.base_strategy.calculate_price(order)
        base_total = base_bill.total_price
        bill_dict  = asdict(base_bill)

        for (start, end), surcharge in self.peak_hours_surcharges.items():
            if start <= order.time_of_order < end:
                bill_dict["peak_hour_surcharge"] = round(base_total * surcharge.value, 2)
                bill_dict["total_price"]         = round(base_total * (1 + surcharge.value), 2)
                return PeakBill(**bill_dict)

        # Non-peak: apply default surcharge
        bill_dict["peak_hour_surcharge"] = round(base_total * self.default_surcharge, 2)
        bill_dict["total_price"]         = round(base_total * (1 + self.default_surcharge), 2)
        return PeakBill(**bill_dict)

# [OCP] — Selects the right strategy based on time. Adding a new strategy type
#          requires adding a new entry in the config + one new case in the match
#          inside create_pricing_strategies() — this class itself stays closed
# [DIP] — Depends on PricingStrategy abstraction for all inner strategies
class MultiPricingStrategy(PricingStrategy):
    def __init__(self, pricing_strategies: Dict[PricingStrategyType, PricingStrategy]):
        if not pricing_strategies:
            raise ValueError("Pricing strategies map cannot be empty")
        self.pricing_strategies  = pricing_strategies
        self.peak_hours_surcharges = PEAK_HOURS_SURCHARGES

    def calculate_price(self, order: FoodOrder) -> Bill:
        for (start, end) in self.peak_hours_surcharges:
            if start <= order.time_of_order <= end:
                return self.pricing_strategies[PricingStrategyType.PEAK_HOUR].calculate_price(order)
        return self.pricing_strategies[PricingStrategyType.STANDARD].calculate_price(order)

# [SRP] — One job: coordinate pricing. Knows nothing about HOW price is calculated
# [DIP] — Depends on PricingStrategy abstraction — swappable without touching this
class PricingEngine:
    def __init__(self, strategy: PricingStrategy):
        self.strategy = strategy

    def calculate_total_price(self, order: FoodOrder):
        bill = self.strategy.calculate_price(order)
        return (bill, f"Total price for order #{order.id}: ₹{bill.total_price:.2f}")


# =============================================================================
# DELIVERY STRATEGIES
# =============================================================================

# [SRP] — Assigns nearest agent by distance range. Nothing else
# [LSP] — Always returns a valid DeliveryAgent or raises — never returns None
class NearestAgentStrategy(DeliveryStrategy):
    def assign_agent(self, order: FoodOrder) -> DeliveryAgent:
        for (min_dist, max_dist), agent in DELIVERY_AGENTS.items():
            if min_dist <= order.distance_km < max_dist:
                return agent
        raise DeliveryException("No delivery agent available for the given distance.")

# [SRP] — Assigns a random agent. Simulates 30% unavailability
# [LSP] — Always returns a valid DeliveryAgent or raises — never returns None
class RandomAgentStrategy(DeliveryStrategy):
    def assign_agent(self, order: FoodOrder) -> DeliveryAgent:
        if randint(1, 10) <= 3:
            raise DeliveryException("No delivery agents available at the moment.")
        return choice(list(DELIVERY_AGENTS.values()))

# [OCP] — Picks randomly from a list of strategies. Adding a new strategy
#          needs zero edits here — just add it to the list at construction time
# [DIP] — Depends on DeliveryStrategy abstraction, not on any concrete class
class MultiAgentStrategy(DeliveryStrategy):
    def __init__(self, agent_strategies: List[DeliveryStrategy]):
        if not agent_strategies:
            raise ValueError("Agent strategies list cannot be empty")
        self.agent_strategies = agent_strategies

    def assign_agent(self, order: FoodOrder) -> DeliveryAgent:
        strategy = choice(self.agent_strategies)
        return strategy.assign_agent(order)

# [SRP] — One job: coordinate delivery assignment + simulate delay
# [DIP] — Depends on DeliveryStrategy abstraction
#          simulate is injected as a callable — pass lambda: None in tests
class DeliveryAssigner:
    def __init__(
        self,
        strategy: DeliveryStrategy,
        simulate: callable = lambda: sleep(2)
    ):
        self.strategy = strategy
        self.simulate = simulate

    def assign_delivery_agent(self, order: FoodOrder):
        self.simulate()
        agent = self.strategy.assign_agent(order)
        return (agent, f"Assigned to: {agent.value}")


# =============================================================================
# NOTIFIERS
# =============================================================================

# [SRP] — Only knows how to format and send a restaurant email
# [LSP] — Safely substitutable wherever RestaurantNotifier is expected
class EmailNotifier(RestaurantNotifier):
    def notify(self, ctx: NotificationContext):
        order       = ctx.order
        pickup_time = add_minutes(order.time_of_order, 30)

        order_items = "\n".join(
            f"    {idx}. {item.value}"
            for idx, item in enumerate(order.items, start=1)
        )

        email = (
            f"\n{'=' * 60}\n"
            f"FROM    : noreply@pandafooddelivery.com\n"
            f"TO      : {order.restaurant.email}\n"
            f"SUBJECT : New Order #{order.id} Received\n"
            f"{'=' * 60}\n\n"
            f"Dear {order.restaurant.name},\n\n"
            f"A new order has been placed. Please prepare it for pickup.\n\n"
            f"Customer        : {order.customer}\n"
            f"Delivery Address: {order.address}\n"
            f"Pickup Time     : {format_time(pickup_time)}\n"
            f"Delivery Agent  : {ctx.delivery_agent.value}\n\n"
            f"Items Ordered:\n{order_items}\n\n"
            f"Regards,\nPanda Food Delivery Team\n"
            f"{'=' * 60}"
        )

        return [(email, f"Email sent to {order.restaurant.name}")]


# [SRP] — Only knows how to format and send a customer SMS with bill breakdown
# [LSP] — Safely substitutable wherever CustomerNotifier is expected
class SmsNotifier(CustomerNotifier):
    def notify(self, ctx: NotificationContext):
        order         = ctx.order
        agent         = ctx.delivery_agent
        bill          = ctx.bill
        bill_dict     = asdict(bill)
        total_amount  = bill_dict.pop("total_price")
        bill_dict.pop("id",       None)
        bill_dict.pop("order_id", None)

        order_lines = "\n".join(
            f"  {idx}. {item.value}"
            for idx, item in enumerate(order.items, start=1)
        )

        bill_lines = "\n".join(
            f"  {key.replace('_', ' ').title():<28} ₹{value:>8.2f}"
            for key, value in bill_dict.items()
        )

        delivery_time = add_minutes(order.time_of_order, 45)

        sms = (
            f"\n{'=' * 50}\n"
            f"Hello {order.customer},\n\n"
            f"Your order from {order.restaurant.name} is confirmed!\n\n"
            f"Order #         : {order.id}\n"
            f"Order Time      : {format_time(order.time_of_order)}\n"
            f"Est. Delivery   : {format_time(delivery_time)}\n"
            f"Delivery Agent  : {agent.value}\n\n"
            f"Items:\n{order_lines}\n\n"
            f"{'- ' * 25}\n"
            f"Bill Breakdown:\n{bill_lines}\n"
            f"{'- ' * 25}\n"
            f"  {'Total Amount':<28} ₹{total_amount:>8.2f}\n"
            f"{'=' * 50}\n\n"
            f"Thank you for ordering with Panda Food Delivery!"
        )

        return [(sms, f"SMS sent to {order.customer}")]


# [OCP] — New channel? Add a new Notifier subclass and pass it in the list.
#          Zero edits to existing notifiers or OrderPipeline
# [DIP] — Depends on Notifier abstraction — works with any Notifier subclass
class MultiChannelNotifier(Notifier):
    def __init__(self, notifiers: List[Notifier]):
        self.notifiers = notifiers

    def notify(self, ctx: NotificationContext):
        results = []
        for notifier in self.notifiers:
            results.extend(notifier.notify(ctx))
        return results


# =============================================================================
# LOGGER
# =============================================================================

# [SRP] — Simulates a database. One job: store log messages in a list
# [OCP] — New database backends (PostgresDatabase, etc.) extend Database
#          without modifying OrderLogger
class MySQLDatabase(Database):
    def __init__(self):
        self.storage: List[str] = []

    def insert(self, message: str):
        self.storage.append(message)
        return (True, "Logged.")

    def get_all(self) -> List[str]:
        return list(self.storage)

# [SRP] — One job: format and persist log entries via injected Database
# [DIP] — Depends on Database abstraction — swap storage without touching this
# Bonus: plugged into OrderPipeline as an optional dependency — pipeline never
#        changes whether logger is present or not (optional injection)
class OrderLogger(Logger):
    def __init__(self, database: Database):
        self.database = database

    def log(self, stage: str, message: str):
        self.database.insert(f"[{stage}] {message}")


# =============================================================================
# PIPELINE
# =============================================================================

# [SRP] — One job: run the pipeline stages in sequence. Contains zero business
#          logic — delegates everything to injected dependencies
# [DIP] — Every dependency injected via constructor. Creates nothing internally
# [OCP] — Adding a new stage means adding a new dependency + one call in run().
#          Existing stages are untouched
# Bonus: logger is Optional — pipeline works with or without it. No if-chains
#        per stage were needed because logger.log() is one clean call
class OrderPipeline:
    def __init__(
        self,
        validator:         Validator,
        pricing_engine:    PricingEngine,
        delivery_assigner: DeliveryAssigner,
        notifier:          Notifier,
        logger:            Optional[Logger] = None,
    ):
        self.validator         = validator
        self.pricing_engine    = pricing_engine
        self.delivery_assigner = delivery_assigner
        self.notifier          = notifier
        self.logger            = logger

    def _log(self, stage: str, message: str):
        # [SRP] — centralised log call so pipeline body stays clean
        if self.logger:
            self.logger.log(stage, message)

    def run(self, order: FoodOrder):
        print(f"\n{'=' * 60}")
        print(f"Processing order #{order.id} for {order.customer}...")
        print(f"{'=' * 60}")
        try:
            _, validation_msg = self.validator.validate(order)
            print(f"[Validation] {validation_msg}")
            self._log("Validation", validation_msg)

            bill, pricing_msg = self.pricing_engine.calculate_total_price(order)
            print(f"[Pricing] {pricing_msg}")
            self._log("Pricing", pricing_msg)

            agent, delivery_msg = self.delivery_assigner.assign_delivery_agent(order)
            print(f"[Delivery] {delivery_msg}")
            self._log("Delivery", delivery_msg)

            notification_results = self.notifier.notify(
                NotificationContext(order, agent, bill)
            )
            for content, summary in notification_results:
                print(f"[Notification] {summary}")
                print(content)
                self._log("Notification", summary)

        except BaseFoodDeliveryException as e:
            error_msg = f"Pipeline error: {e}"
            print(error_msg)
            self._log("Error", str(e))

        except ValueError as e:
            error_msg = f"Value error: {e}"
            print(error_msg)
            self._log("Error", str(e))


# =============================================================================
# FACTORY — builds the full pricing engine from config, no globals mutated
# =============================================================================

# [OCP] — To add FestivalPricing:
#          1. Add PricingStrategyType.FESTIVAL to the enum
#          2. Add its args to PRICING_STRATEGIES_BASE_ARGUMENTS
#          3. Add its dependency to PRICING_STRATEGIES_DEPENDENCY
#          4. Add a new case in the match block below
#          Nothing else changes.
def create_pricing_strategies() -> Dict[PricingStrategyType, PricingStrategy]:
    base: Dict[PricingStrategyType, PricingStrategy] = {
        PricingStrategyType.STANDARD: StandardPricing(
            PricingContext(**PRICING_STRATEGIES_BASE_ARGUMENTS[PricingStrategyType.STANDARD])
        )
    }

    dependent: Dict[PricingStrategyType, PricingStrategy] = {}
    for strategy_type, base_type in PRICING_STRATEGIES_DEPENDENCY.items():
        match strategy_type:
            case PricingStrategyType.PEAK_HOUR:
                args = PRICING_STRATEGIES_BASE_ARGUMENTS[strategy_type].copy()
                args["base_strategy"] = base[base_type]
                dependent[strategy_type] = PeakHourPricing(PricingContext(**args))

    return {**base, **dependent}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    # Build pricing engine via factory — no globals, no mutation
    all_pricing_strategies = create_pricing_strategies()
    pricing_engine         = PricingEngine(MultiPricingStrategy(all_pricing_strategies))

    # [DIP] — All dependencies constructed here and injected — nothing created inside
    database               = MySQLDatabase()
    logger                 = OrderLogger(database)
    validator              = OrderValidator()
    delivery_assigner      = DeliveryAssigner(
                                MultiAgentStrategy([NearestAgentStrategy(), RandomAgentStrategy()])
                             )
    multi_channel_notifier = MultiChannelNotifier([SmsNotifier(), EmailNotifier()])

    pipeline = OrderPipeline(
        validator         = validator,
        pricing_engine    = pricing_engine,
        delivery_assigner = delivery_assigner,
        notifier          = multi_channel_notifier,
        logger            = logger,
    )

    data = [
        FoodOrder(
            customer="Ayesha",
            restaurant=Restaurant("Bombay Kitchen", 1100, 2300, "orders@bombaykitchen.com", True),
            items=[MenuItem.BIRYANI, MenuItem.RAITA],
            address="Andheri West, Mumbai",
            day_of_week="Friday",
            time_of_order=1830,
            distance_km=3.5,
        ),
        FoodOrder(
            customer="Amit Sharma",
            restaurant=Restaurant("Biryani House", 1100, 2300, "contact@biryanihouse.com", True),
            items=[MenuItem.BIRYANI, MenuItem.RAITA],
            address="Andheri West, Mumbai",
            day_of_week="Saturday",
            time_of_order=1330,
            distance_km=4.5,
        ),
        FoodOrder(
            customer="Priya Verma",
            restaurant=Restaurant("Punjab Grill", 1200, 2200, "support@punjabgrill.com", True),
            items=[MenuItem.BUTTER_CHICKEN, MenuItem.NAAN, MenuItem.DAL_MAKHANI],
            address="Powai, Mumbai",
            day_of_week="Friday",
            time_of_order=2000,
            distance_km=8.2,
        ),
        FoodOrder(
            customer="Rahul Gupta",
            restaurant=Restaurant("Veg Delight", 1000, 2100, "hello@vegdelight.com", False),
            items=[MenuItem.VEG_BIRYANI, MenuItem.PANEER_TIKKA, MenuItem.RAS_MALAI],
            address="Bandra East, Mumbai",
            day_of_week="Wednesday",
            time_of_order=1430,
            distance_km=6.8,
        ),
        FoodOrder(
            customer="Sneha Patil",
            restaurant=Restaurant("Royal Tandoor", 1100, 2330, "orders@royaltandoor.com", True),
            items=[MenuItem.JEERA_RICE, MenuItem.DAL_MAKHANI, MenuItem.GULAB_JAMUN],
            address="Thane West, Mumbai",
            day_of_week="Sunday",
            time_of_order=1900,
            distance_km=12.4,
        ),
    ]

    for food_order in data:
        pipeline.run(food_order)

    # Display all logs at the end
    logs = database.get_all()
    if logs:
        print(f"\n{'=' * 60}")
        print("SYSTEM LOGS")
        print(f"{'=' * 60}")
        for entry in logs:
            print(entry)
        print(f"{'=' * 60}")