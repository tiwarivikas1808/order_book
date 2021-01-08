import enum
import queue
import time

from collections import defaultdict

class Side(enum.Enum):
    BUY = 0
    SELL = 1

def get_timestamp():
    return int(1e6 * time.time())

class OrderBook(object):
    def __init__(self):
        self.bid_prices = []
        self.bid_sizes = []
        self.offer_prices = []
        self.offer_sizes = []
        self.bids = defaultdict(list)
        self.offers = defaultdict(list)
        self.unprocessed_orders = queue.Queue()
        self.trades = queue.Queue()
        self.order_id = 0

    def new_order_id(self):
        self.order_id += 1
        return self.order_id

    @property
    def max_bid(self):
        if self.bids:
            return max(self.bids.keys())
        else:
            return 0.

    @property
    def min_offer(self):
        if self.offers:
            return min(self.offers.keys())
        else:
            return float('inf')

    def process_order(self, incoming_order):
        incoming_order.timestamp = get_timestamp()
        incoming_order.order_id = self.new_order_id()
        if incoming_order.side == Side.BUY:
            if incoming_order.price >= self.min_offer and self.offers:
                self.process_match(incoming_order)
            else:
                self.bids[incoming_order.price].append(incoming_order)
        else:
            if incoming_order.price <= self.max_bid and self.bids:
                self.process_match(incoming_order)
            else:
                self.offers[incoming_order.price].append(incoming_order)

    def process_match(self, incoming_order):
        levels = self.bids if incoming_order.side == Side.SELL else self.offers
        prices = sorted(levels.keys(), reverse=(incoming_order.side == Side.SELL))
        def price_doesnt_match(book_price):
            if incoming_order.side == Side.BUY:
                return incoming_order.price < book_price
            else:
                return incoming_order.price > book_price
        for (i, price) in enumerate(prices):
            if (incoming_order.size == 0) or (price_doesnt_match(price)):
                break
            orders_at_level = levels[price]
            for (j, book_order) in enumerate(orders_at_level):
                if incoming_order.size == 0:
                    break
                trade = self.execute_match(incoming_order, book_order)
                incoming_order.size = max(0, incoming_order.size-trade.size)
                book_order.size = max(0, book_order.size-trade.size)
                self.trades.put(trade)
            levels[price] = [o for o in orders_at_level if o.size > 0]
            if len(levels[price]) == 0:
                levels.pop(price)
        
        if incoming_order.size > 0:
            same_side = self.bids if incoming_order.side == Side.BUY else self.offers
            same_side[incoming_order.price].append(incoming_order)

    def execute_match(self, incoming_order, book_order):
        trade_size = min(incoming_order.size, book_order.size)
        return Trade(incoming_order.side, book_order.price, trade_size, incoming_order.order_id, book_order.order_id)

    def book_summary(self):
        self.bid_prices = sorted(self.bids.keys(), reverse=True)
        self.offer_prices = sorted(self.offers.keys())
        self.bid_sizes = [sum(o.size for o in self.bids[p]) for p in self.bid_prices]
        self.offer_sizes = [sum(o.size for o in self.offers[p]) for p in self.offer_prices]

    def show_book(self):
        self.book_summary()
        print('Selling side:')
        if len(self.offer_prices) == 0:
            print('EMPTY')
        for i, price in reversed(list(enumerate(self.offer_prices))):
            print('{0}) Price={1}, Total units={2}'.format(i+1, self.offer_prices[i], self.offer_sizes[i]))
        print('Buying side:')
        if len(self.bid_prices) == 0:
            print('EMPTY')
        for i, price in enumerate(self.bid_prices):
            print('{0}) Price={1}, Total units={2}'.format(i+1, self.bid_prices[i], self.bid_sizes[i]))
        print()


class Order(object):
    def __init__(self, side, price, size, timestamp=None, order_id=None):
        self.side = side
        self.price = price
        self.size = size
        self.timestamp = timestamp
        self.order_id = order_id

    def __repr__(self):
        return '{0} {1} units at {2}'.format(self.side, self.size, self.price)

    
class Trade(object):
    def __init__(self, incoming_side, incoming_price, trade_size, incoming_order_id, book_order_id):
        self.side = incoming_side
        self.price = incoming_price
        self.size = trade_size
        self.incoming_order_id = incoming_order_id
        self.book_order_id = book_order_id

    def __repr__(self):
        return 'Executed: {0} {1} units at {2}'.format(self.side, self.size, self.price)


if __name__ == '__main__':
    print('Example 1 is here:')
    ob = OrderBook()
    orders = [Order(Side.BUY, 1., 2),
            Order(Side.BUY, 2., 3, 2),
            Order(Side.BUY, 1., 4, 3)]
    print('We receive these orders:-')
    for order in orders:
        print(order)
        ob.unprocessed_orders.put(order)
    while not ob.unprocessed_orders.empty():
        ob.process_order(ob.unprocessed_orders.get())
    print()
    print('The Resulting order book is :-')
    ob.show_book()

    print('Example 2 is here:')
    ob = OrderBook()
    orders = [Order(Side.BUY, 12.23, 10),
            Order(Side.BUY, 12.31, 20),
            Order(Side.SELL, 13.55, 5),
            Order(Side.BUY, 12.23, 5),
            Order(Side.BUY, 12.25, 15),
            Order(Side.SELL, 13.31, 5),
            Order(Side.BUY, 12.25, 30),
            Order(Side.SELL, 13.31, 5)]
    print('We receive these orders:-')
    for order in orders:
        print(order)
        ob.unprocessed_orders.put(order)
    while not ob.unprocessed_orders.empty():
        ob.process_order(ob.unprocessed_orders.get())
    print()
    print('The Resulting order book is :-')
    ob.show_book()

    offer_order = Order(Side.SELL, 12.25, 100)
    print('Here is the sell order {}'.format(offer_order))
    print('By removing the first two buy orders which creates a new price level on the Sell Side :-')
    ob.unprocessed_orders.put(offer_order)
    ob.process_order(ob.unprocessed_orders.get())
    ob.show_book()
