"""
https://poloniex.com/support/api/
"""
import requests
import json
import hmac
import hashlib
from . import utils
from urllib.parse import urlencode
from time import time
from . import settings

MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24
MONTH = DAY * 30


def sign(secret, data):
    """
    Create signature from data
    :param secret:
    :param data:
    :return: signature
    """
    return hmac.new(
        secret.encode('utf-8'),
        urlencode(data).encode('utf-8'),
        hashlib.sha512
    ).hexdigest()


@utils.rate_limited(settings.api_rate_limit)
def block():
    """Limit code execution to `api_rate_limit` times per second"""


class PoloniexError(Exception):
    """General Poloniex Error"""


class SecretKeyError(PoloniexError):
    """Attempt to access private api without providing secrets module"""


class Poloniex:
    trading_url = settings.trading_url
    public_url = settings.public_url
    secret_json_path = settings.secret_json_path
    get = requests.get
    post = requests.post
    rate_limit = True
    px_key = None
    px_secret = None

    def _public_api(self, **kwargs):
        """
        Package parameters using urlencode and send GET request to public API.

        :param kwargs: api parameters
        :return: response decoded from json
        """
        url = self.public_url + urlencode(kwargs)
        self._rate_limit_block()
        response = self.__class__.get(url)
        return response.json()

    def _trading_api(self, **kwargs):
        """
        Package parameters into signed payload and post it to private
        trading API.

        :param kwargs: api parameters
        :return: response decoded from json
        """
        self._check_secrets()
        kwargs['nonce'] = int(time() * 1000)
        payload = {
            'url': self.trading_url,
            'headers': {
                'Sign': sign(self.px_secret, kwargs),
                'Key': self.px_key,
            },
            'data': kwargs
        }
        self._rate_limit_block()
        response = self.__class__.post(**payload)
        return response.json()

    def _rate_limit_block(self):
        """
        Based on `rate_limit` flag block the execution to respect rate
        limit specified in settings. This rate limit will apply to all
        class instances.
        """
        if self.rate_limit:
            block()

    def _check_secrets(self):
        """
        Check internal px_key and px_secret values. If they are not empty,
        move on. If they are not specified try to load them from json file.
        The path to the file is specified in settings.
        Default is `~/poloniex/secret.json`. It means that there is a secrets
        json file that has `key` and `secret` defined. For example:
        {
            "key": "test",
            "secret": "secret"
        }

        :return: None
        """
        if self.px_key and self.px_secret:
            return

        with open(self.secret_json_path) as f:
            data = json.load(f)

        key, secret = data.get('key'), data.get('secret')
        if not key:
            raise SecretKeyError(
                'poloniex secrets module is missing key value'
            )

        if not secret:
            raise SecretKeyError(
                'poloniex secrets module is missing secret value'
            )

        self.px_key, self.px_secret = key, secret

    # Public APIs #

    def ticker(self):
        """
        Returns the ticker for all markets.

        :rtype: dict
        :return: {"BTC_LTC":
                    {"last": "0.0251", "lowestAsk": "0.02589999",
                     "highestBid": "0.0251", "percentChange": "0.02390438",
                     "baseVolume":"6.16485315", "quoteVolume":"245.82513926"
                     },
                  "BTC_NXT":
                    {"last": "0.00005730", "lowestAsk": "0.00005710",
                     "highestBid": "0.00004903", "percentChange": "0.16701570",
                     "baseVolume": "0.45347489", "quoteVolume": "9094"
                     },
                  ...
                  }
        """
        return self._public_api(
            command='returnTicker'
        )

    def volume24(self):
        """
        Returns the 24-hour volume for all markets,
        plus totals for primarycurrencies.

        :rtype: dict
        :return: {"BTC_LTC": {"BTC":"2.23248854","LTC":"87.10381314"},
                  "BTC_NXT": {"BTC":"0.981616","NXT":"14145"},
                  ...
                  "totalBTC": "81.89657704",
                  "totalLTC":"78.52083806"
                  }
        """
        return self._public_api(
            command='return24hVolume'
        )

    def order_book(self, pair='all', depth=20):
        """
        Returns the order book for a given market, as well as a sequence number
        for use with the Push API and an indicator specifying whether the
        market is frozen. You may set pair to "all" to get the order
        books of all markets.

        :param str pair: trade pair like BTC_NXT
        :param int depth: number of open orders
        :rtype: dict
        :return: {"BTC_NXT":
                    {"asks":[[0.00007600,1164],[0.00007620,1300], ... ],
                     "bids":[[0.00006901,200],[0.00006900,408], ... ],
                     "isFrozen": 0,
                     "seq": 149
                     },
                  "BTC_XMR":...
                 }
        """
        return self._public_api(
            command='returnOrderBook', currencyPair=pair, depth=depth
        )

    def public_trade_history(self, pair, start=0, end=0):
        """
        Returns the past 200 trades for a given market, or up to 50,000 trades
        between a range specified in UNIX timestamps by the "start" and "end"

        :param str pair: trade pair like BTC_NXT
        :param int start: UNIX timestamp for start period
        :param int end: UNIX timestamp for the end of the period
        :rtype: dict
        :return: [{"date": "2014-02-10 04:23:23", "type": "buy",
                   "rate": "0.00007600", "amount": "140", "total": "0.01064"},
                  {"date": "2014-02-10 01:19:37", "type": "buy",
                   "rate": "0.00007600", "amount": "655", "total": "0.04978"},
                  ...]
        """
        kwargs = {
            'command': 'returnTradeHistory',
            'currencyPair': str(pair).upper()
        }
        if start:
            kwargs['start'] = start
        if end:
            kwargs['end'] = end

        return self._public_api(**kwargs)

    def chart_data(self, pair, start=0, end=0, period=1800):
        """
        Returns candlestick chart data. Default time range is from now
        to 1 day ego. Default period is 1800.

        :param str pair: trade pair like BTC_NXT
        :param int start: positive int representing UNIX timestamp
        :param int end: positive int representing UNIX timestamp
        :param int period: one of [300, 900, 1800, 7200, 14400, 86400]
        :rtype: dict
        :return: [{"date": 1405699200, "high": 0.0045388, "low":0.00403001,
                   "open":0.00404545, "close":0.00427592, "volume": 44.11655644,
                   "quoteVolume": 10259.29079097, "weightedAverage": 0.00430015
                   },
                   ...]
        """
        if period not in [300, 900, 1800, 7200, 14400, 86400]:
            raise PoloniexError('{} invalid candle period'.format(period))

        return self._public_api(
            command='returnChartData',
            currencyPair=str(pair).upper(),
            start=start > 0 and start or int(time()) - DAY,
            end=end > 0 and end or int(time())
        )

    def currencies(self):
        """
        Returns information about currencies.

        :rtype: dict
        :return: {"1CR": {"maxDailyWithdrawal": 10000, "txFee": 0.01,
                          "minConf": 3, "disabled": 0},
                  "ABY": {"maxDailyWithdrawal": 10000000, "txFee": 0.01,
                          "minConf": 8, "disabled": 0},
                   ...
                   }
        """
        return self._public_api(
            command='returnCurrencies'
        )

    def loan_orders(self, currency):
        """
        Returns the list of loan offers and demands for a given currency,
        specified by the "currency" parameter.

        :param str currency: like BTC, LTC, ...
        :rtype: dict
        :return: {"offers":[{"rate": "0.00200000", "amount": "64.66305732",
                             "rangeMin": 2, "rangeMax":8}, ...],
                  "demands":[{"rate": "0.00170000", "amount": "26.54848841",
                              "rangeMin": 2, "rangeMax": 2}, ... ]
                  }
        """
        return self._public_api(
            command='returnLoanOrders',
            currency=currency,
            limit=5000
        )

    # Trading APIs #

    def balances(self):
        """
        Returns all of your available balances.

        :rtype: dict
        :return: {"BTC": "0.59098578", "LTC": "3.31117268", ... }
        """
        result = self._trading_api(command='returnBalances')
        return result

    def complete_balances(self, account='all'):
        """
        Returns all of your balances, including available balance,
        balance on orders, and the estimated BTC value of your balance.
        By default, this call is limited to your exchange account;
        set the "account" parameter to "all" to include your
        margin and lending accounts.

        :param str account: possible values are all, margin, lending
        :rtype: dict
        :return: {"LTC": {"available": "5.015", "onOrders": "1.0025",
                          "btcValue": "0.078"},
                  "NXT: {...} ... }
        """
        result = self._trading_api(
            command='returnCompleteBalances',
            account=str(account)
        )
        return result

    def deposit_addresses(self):
        """
        Returns all of your deposit addresses.

        :rtype: dict
        :return: {"BTC": "19YqztHmspv2egyD6jQM3yn81x5t5krVdJ",
                  "LTC": "LPgf9kjv9H1Vuh4XSaKhzBe8JHdou1WgUB",
                  ...
                  "ITC": "Press Generate.." ... }
        """
        result = self._trading_api(
            command='returnDepositAddresses'
        )
        return result

    def generate_new_address(self, currency):
        """
        Generates a new deposit address for the currency specified by the
        "currency" parameter. Only one address per currency per day may
        be generated, and a new address may not be generated before the
        previously-generated one has been used.

        :param str currency: values like BTC, LTC
        :rtype: dict
        :return: {"success": 1,"response": "CKXbbs8FAVbtEa397gJHSutmrdrBrhUMxe"}
        """
        result = self._trading_api(
            command='generateNewAddress',
            currency=str(currency).upper()
        )
        return result

    def deposits_withdrawals(self, start=0, end=0):
        """
        Returns your deposit and withdrawal history within a range,
        specified by the "start" and "end" parameters,
        both of which should be given as UNIX timestamps.

        :param int start: positive int representing UNIX timestamp
        :param int end: positive int representing UNIX timestamp
        :rtype: dict
        :return: {"deposits": [{"currency": "BTC","address": "...",
                                "amount": "0.01006132", "confirmations": 10,
                                "txid": "17f819a91369a9ff6c4a34216d434597cfc1b4a3d0489b46bd6f924137a47701",
                                "timestamp":1399305798,"status":"COMPLETE"},
                               {"currency": "BTC", "address": "...",
                                "amount":"0.00404104","confirmations":10,
                                "txid": "7acb90965b252e55a894b535ef0b0b65f45821f2899e4a379d3e43799604695c",
                                "timestamp": 1399245916, "status": "COMPLETE"}
                                ],
                 "withdrawals": [{"withdrawalNumber": 134933, "currency": "BTC",
                                  "address": "1N2i5n8DwTGzUq2Vmn9TUL8J1vdr1XBDFg",
                                  "amount": "5.00010000", "timestamp": 1399267904,
                                  "status": "COMPLETE: 36e483efa6aff9fd53a235177579d98451c4eb237c210e66cd2b9a2d4a988f8e",
                                  "ipAddress": "..."}
                                ]
                 }
        """
        return self._trading_api(
            command='returnDepositsWithdrawals',
            start=start > 0 and start or int(time()) - MONTH,
            end=end > 0 and end or time()
        )

    def open_orders(self, pair='all'):
        """
        Returns your open orders for a given market, specified by the "pair"
        parameter, e.g. "BTC_XCP". Set "pair" to "all" to return open orders
        for all markets.

        :param str pair: currency pair like BTC_XCP
        :rtype: list
        :return: [{"orderNumber": "120466", "type": "sell", "rate": "0.025",
                   "amount": "100", "total": "2.5"},
                  {"orderNumber": "120467", "type": "sell", "rate": "0.04",
                   "amount": "100", "total": "4"},
                   ...
                 ]
        :rtype: dict
        :return: {"BTC_1CR":[],
                  "BTC_AC": [{"orderNumber": "120466", "type": "sell",
                              "rate": "0.025", "amount": "100", "total": "2.5"},
                             {"orderNumber": "120467", "type": "sell",
                              "rate": "0.04", "amount": "100", "total": "4"}],
                  ...
                  }
        """
        result = self._trading_api(
            command='returnOpenOrders',
            currencyPair=str(pair).upper()
        )
        return result

    def trade_history(self, pair='all', start=0, end=0, limit=0):
        """
        Returns your trade history for a given market, specified by the "pair"
        parameter. You may specify "all" as the pair to receive your trade
        history for all markets. You may optionally specify a range via
        "start" and/or "end" POST parameters, given in UNIX timestamp format;
        if you do not specify a range, it will be limited to one day.
        You may optionally limit the number of entries returned using the
        "limit" parameter, up to a maximum of 10,000. If the "limit" parameter
        is not specified, no more than 500 entries will be returned.

        :param str pair: currency pair like BTC_XCP
        :param int start: positive int representing UNIX timestamp
        :param int end: positive int representing UNIX timestamp
        :param int limit: number of entries
        :rtype: list
        :return: [{ "globalTradeID": 25129732, "tradeID": "6325758",
                    "date": "2016-04-05 08:08:40", "rate": "0.02565498",
                    "amount": "0.10000000", "total": "0.00256549",
                    "fee": "0.00200000", "orderNumber": "34225313575",
                    "type": "sell", "category": "exchange"
                  },
                  { "globalTradeID": 25129628, "tradeID": "6325741",
                    "date": "2016-04-05 08:07:55", "rate": "0.02565499",
                    "amount": "0.10000000", "total": "0.00256549",
                    "fee": "0.00200000", "orderNumber": "34225195693",
                    "type": "buy", "category": "exchange"
                    },
                    ...
                    ]
        :rtype: dict
        :return: {"BTC_MAID": [{ "globalTradeID": 29251512, "tradeID": "1385888",
                                 "date": "2016-05-03 01:29:55", "rate": "0.00014243",
                                 "amount": "353.74692925", "total": "0.05038417",
                                 "fee": "0.00200000", "orderNumber": "12603322113",
                                 "type": "buy", "category": "settlement"
                                },
                                { "globalTradeID": 29251511, "tradeID": "1385887",
                                  "date": "2016-05-03 01:29:55", "rate": "0.00014111",
                                  "amount": "311.24262497", "total": "0.04391944",
                                  "fee": "0.00200000", "orderNumber": "12603319116",
                                  "type": "sell", "category": "marginTrade"
                                },
                                ...
                               ],
                 "BTC_LTC": [ ... ],
                 ...
                 }
        """
        if limit > 10000:
            limit = 500
        kwargs = {'currencyPair': str(pair).upper()}
        if limit > 0:
            kwargs['limit'] = limit
        if start > 0:
            kwargs['start'] = start
        if end > 0 and start < end:
            kwargs['end'] = end
        result = self._trading_api(
            command='returnTradeHistory', **kwargs
        )
        return result

    def order_trades(self, order_number):
        """
        Returns all trades involving a given order, specified by the
        "order_number" parameter. If no trades for the order have occurred or
        you specify an order that does not belong to you, you will receive
        an error.

        :param order_number:
        :rtype: list
        :return: [{"globalTradeID": 20825863, "tradeID": 147142,
                   "currencyPair": "BTC_XVC", "type": "buy",
                   "rate": "0.00018500", "amount": "455.34206390",
                   "total": "0.08423828", "fee": "0.00200000",
                   "date": "2016-03-14 01:04:36"},
                   ...
                   ]
        """
        result = self._trading_api(
            command='returnOrderTrades', orderNumber=str(order_number)
        )
        return result

    def buy(self, pair, rate, amount, fill_or_kill=False,
            immediate_or_cancel=False, post_only=False):
        """
        Places a limit buy order in a given market. Required parameters
        are "pair", "rate", and "amount".
        The order number is part of successful return result.

        :param string pair: currency pair like BTX_LTX
        :param float rate: buying price
        :param float amount: Amount of coins to buy
        :param bool fill_or_kill: order will either fill in its
                                  entirety or be completely aborted.
        :param bool immediate_or_cancel: order can be partially or completely
                                         filled, but any portion of the order
                                         that cannot be filled immediately will
                                         be canceled rather than left on the
                                         order book.
        :param bool post_only: order will only be placed if no portion of it
                               fills immediately; this guarantees you will
                               never pay the taker fee on any part of the
                               order that fills.
        :rtype: dict
        :return: {"orderNumber": 31226040,
                  "resultingTrades": [{"amount": "338.8732",
                                       "date":"2014-10-18 23:03:21",
                                       "rate":"0.00000173",
                                       "total": "0.00058625",
                                       "tradeID": "16164",
                                       "type": "buy"}]
                 }
        """
        result = self._trading_api(
            command='buy', currencyPair=str(pair).upper(),
            rate=rate, amount=amount,
            fillOrKill=int(fill_or_kill),
            immediateOrCancel=int(immediate_or_cancel),
            postOnly=int(post_only)
        )
        return result

    def sell(self, pair, rate, amount, fill_or_kill=False,
             immediate_or_cancel=False, post_only=False):
        """
        Places a sell order in a given market. Required parameters
        are "pair", "rate", and "amount".
        The order number is part of successful return result.

        :param string pair: currency pair like BTX_LTX
        :param float rate: selling price
        :param float amount: Amount of coins to sell
        :param bool fill_or_kill: order will either fill in its
                                  entirety or be completely aborted.
        :param bool immediate_or_cancel: order can be partially or completely
                                         filled, but any portion of the order
                                         that cannot be filled immediately will
                                         be canceled rather than left on the
                                         order book.
        :param bool post_only: order will only be placed if no portion of it
                               fills immediately; this guarantees you will
                               never pay the taker fee on any part of the
                               order that fills.
        :rtype: dict
        :return: {"orderNumber": 31226040,
                  "resultingTrades": [{"amount": "338.8732",
                                       "date":"2014-10-18 23:03:21",
                                       "rate":"0.00000173",
                                       "total": "0.00058625",
                                       "tradeID": "16164",
                                       "type": "sell"}]
                 }
        """
        result = self._trading_api(
            command='sell', currencyPair=str(pair).upper(),
            rate=rate, amount=amount,
            fillOrKill=int(fill_or_kill),
            immediateOrCancel=int(immediate_or_cancel),
            postOnly=int(post_only)
        )
        return result

    def cancel_order(self, order_number):
        """
        Cancels an order you have placed in a given market.
        Required parameter is "order_number".

        :param int order_number: order number from sell or buy calls
        :rtype: dict
        :return: {"success": 1}
        """
        result = self._trading_api(
            command='cancelOrder', orderNumber=str(order_number)
        )
        return result

    def move_order(self, order_number, rate, amount=0,
                   immediate_or_cancel=False, post_only=False):
        """
        Cancels an order and places a new one of the same type in a single
        atomic transaction, meaning either both operations will succeed or
        both will fail. Required parameters are "order_number" and "rate";
        you may optionally specify "amount" if you wish to change the amount
        of the new order.

        :param int order_number: order number from sell or buy calls
        :param float rate: price the order is buying at
        :param float amount: Amount of coins to buy
        :param bool immediate_or_cancel: order can be partially or completely
                                         filled, but any portion of the order
                                         that cannot be filled immediately will
                                         be canceled rather than left on the
                                         order book.
        :param bool post_only: order will only be placed if no portion of it
                               fills immediately; this guarantees you will
                               never pay the taker fee on any part of the
                               order that fills.
        :rtype: dict
        :return: {"success": 1, "orderNumber": "239574176",
                  "resultingTrades": {"BTC_BTS": [] }
                  }
        """
        kwargs = {
            'command': 'moveOrder', 'orderNumber': str(order_number),
            'rate': str(rate),
            'immediateOrCancel': int(immediate_or_cancel),
            'post_only': int(post_only)
        }
        if amount > 0:
            kwargs['amount'] = amount
        result = self._trading_api(**kwargs)
        return result

    def withdraw(self, currency, amount, address, payment_id=None):
        """
        Immediately places a withdrawal for a given currency, with no email
        confirmation. In order to use this method, the withdrawal privilege
        must be enabled for your API key. Required parameters are "currency",
        "amount", and "address". For XMR withdrawals, you may optionally
        specify "payment_id"

        :param string currency: coins to withdraw like BTX or LTX
        :param amount: amount to withdraw
        :param address: withdraw to
        :param string payment_id: optional to use with XMR
        :rtype: dict
        :return: {"response": "Withdrew 2398 NXT."}
        """
        kwargs = {
            'currency': str(currency).upper(),
            'amount': amount,
            'address': str(address)
        }
        if payment_id:
            kwargs['paymentId'] = payment_id

        result = self._trading_api(command='withdraw', **kwargs)
        return result

    def fee_info(self):
        """
        If you are enrolled in the maker-taker fee schedule, returns your
        current trading fees and trailing 30-day volume in BTC.
        This information is updated once every 24 hours.

        :rtype: dict
        :return: {"makerFee": "0.00140000", "takerFee": "0.00240000",
                  "thirtyDayVolume": "612.00248891", "nextTier": "1200.00000000"
                 }
        """
        result = self._trading_api(command='returnFeeInfo')
        return result

    def available_account_balances(self, account=None):
        """
        Returns your balances sorted by account. You may optionally specify
        the "account" parameter if you wish to fetch only the balances of one
        account. Please note that balances in your margin account may not be
        accessible if you have any open margin positions or orders.

        :param string account: exchange, margin, lending
        :rtype: dict
        :return: {"exchange": {"BTC": "1.19042859", "BTM": "386.52379392",
                               "CHA": "0.50000000", "DASH": "120.00000000",
                               "STR": "3205.32958001", "VNL": "9673.22570147"},
                  "margin": {"BTC": "3.90015637", "DASH": "250.00238240",
                             "XMR": "497.12028113"},
                  "lending": {"DASH":"0.01174765", "LTC": "11.99936230"}
                 }
        """
        kwargs = {'command': 'returnAvailableAccountBalances'}
        if account:
            kwargs['account'] = account
        result = self._trading_api(**kwargs)
        return result

    def tradable_balances(self):
        """
        Returns your current tradable balances for each currency in each market
        for which margin trading is enabled. Please note that these balances
        may vary continually with market conditions.

        :rtype: dict
        :return: {"BTC_DASH": {"BTC": "8.50274777", "DASH":"654.05752077"},
                  "BTC_LTC": {"BTC": "8.50274777", "LTC": "1214.67825290"},
                  "BTC_XMR": {"BTC": "8.50274777", "XMR": "3696.84685650"}
                  }
        """
        results = self._trading_api(command='returnTradableBalances')
        return results

    def transfer_balance(self, currency, amount, from_account, to_account):
        """
        Transfers funds from one account to another (e.g. from your exchange
        account to your margin account). Required parameters are "currency",
        "amount", "from_account", and "to_account".

        :param string currency: BTC, LTC
        :param float amount: transfer amount
        :param string from_account: exchange, margin, lending
        :param to_account: exchange, margin, lending
        :rtype: dict
        :return: {"success": 1, "message": "Transferred 2 BTC from
                                            exchange to margin account."
                 }
        """
        result = self._trading_api(
            command='transferBalance', currency=str(currency).upper(),
            amount=amount, fromAccount=from_account, toAccount=to_account
        )
        return result

    def margin_account_summary(self):
        """
        Returns a summary of your entire margin account. This is the same
        information you will find in the Margin Account section of the Margin
        Trading page, under the Markets list.

        :rtype: dict
        :return: {"totalValue": "0.00346561", "pl": "-0.00001220",
                  "lendingFees": "0.00000000", "netValue": "0.00345341",
                  "totalBorrowedValue": "0.00123220",
                  "currentMargin": "2.80263755"
                  }
        """
        results = self._trading_api(command='returnMarginAccountSummary')
        return results

    def margin_buy(self, pair, rate, amount, lending_rate=0.1):
        """
        Places a margin buy order in a given market. Required parameters are
        "pair", "rate", and "amount". You may optionally specify a
        maximum lending rate using the "lending_rate" parameter. If successful,
        the method will return the order number and any trades immediately
        resulting from your order.

        :param string pair: LTC, BTC, ...
        :param float rate: buying price
        :param float amount: amount of coins to buy
        :param lending_rate: percentage rate like 0.0057
        :rtype: dict
        :return: {"success": 1, "message": "Margin order placed.",
                  "orderNumber": "154407998",
                  "resultingTrades": {"BTC_DASH": [
                    {"amount": "1.00000000", "date": "2015-05-10 22:47:05",
                     "rate": "0.01383692", "total": "0.01383692",
                     "tradeID": "1213556", "type": "buy"}
                     ]
                  }
                 }
        """
        result = self._trading_api(
            command='marginBuy', currencyPair=str(pair).upper(), rate=rate,
            amount=amount, lendingRate=lending_rate
        )
        return result

    def margin_sell(self, pair, rate, amount, lending_rate=0.1):
        """
        Places a margin sell order in a given market. Required parameters are
        "pair", "rate", and "amount". You may optionally specify a
        maximum lending rate using the "lending_rate" parameter. If successful,
        the method will return the order number and any trades immediately
        resulting from your order.

        :param string pair: LTC, BTC, ...
        :param float rate: buying price
        :param float amount: amount of coins to buy
        :param float lending_rate: percentage rate like 0.0057
        :rtype: dict
        :return: {"success": 1, "message": "Margin order placed.",
                  "orderNumber": "154407998",
                  "resultingTrades": {"BTC_DASH": [
                    {"amount": "1.00000000", "date": "2015-05-10 22:47:05",
                     "rate": "0.01383692", "total": "0.01383692",
                     "tradeID": "1213556", "type": "sell"}
                     ]
                  }
                 }
        """
        result = self._trading_api(
            command='marginSell', currencyPair=str(pair).upper(), rate=rate,
            amount=amount, lendingRate=lending_rate
        )
        return result

    def get_margin_position(self, pair='all'):
        """
        Returns information about your margin position in a given market,
        specified by the "pair" parameter. You may set "pair" to "all" if you
        wish to fetch all of your margin positions at once (default option).
        If you have no margin position in the specified market, "type" will
        be set to "none". "liquidationPrice" is an estimate, and does not
        necessarily represent the price at which an actual forced liquidation
        will occur. If you have no liquidation price, the value will be -1.

        :param string pair: currency pair like BTC_DASH
        :rtype: dict
        :return: {"amount": "40.94717831", "total": "-0.09671314",
                  "basePrice": "0.00236190", "liquidationPrice": -1,
                  "pl": "-0.00058655", "lendingFees":" -0.00000038",
                  "type": "long"
                  }
        """
        result = self._trading_api(
            command='getMarginPosition', currencyPair=str(pair).upper()
        )
        return result

    def close_margin_position(self, pair):
        """
        Closes your margin position in a given market (specified by the
        "pair" parameter) using a market order. This call will also return
        success if you do not have an open position in the specified market.

        :param string pair: currency pair like BTC_DASH
        :rtype: dict
        :return: {"success": 1,
                  "message": "Successfully closed margin position.",
                  "resultingTrades": {"BTC_XMR":
                    [{"amount": "7.09215901", "date": "2015-05-10 22:38:49",
                      "rate": "0.00235337", "total": "0.01669047",
                      "tradeID": "1213346", "type": "sell"},
                     {"amount": "24.00289920", "date": "2015-05-10 22:38:49",
                      "rate": "0.00235321", "total": "0.05648386",
                      "tradeID": "1213347", "type": "sell"}
                    ]
                   }
                 }
        """
        result = self._trading_api(
            command='closeMarginPosition', currencyPair=str(pair).upper()
        )
        return result

    def create_loan_offer(self, currency, amount, lending_rate, auto_renew,
                          duration=2):
        """
        Creates a loan offer for a given currency. Required parameters are
        "currency", "amount", "duration", "auto_renew" (0 or 1), and
        "lending_rate".

        :param string currency: BTC, DASH, LTC, etc
        :param float amount: lending amount
        :param float lending_rate: lending rate percentage
        :param bool auto_renew: 0 - disable, 1 - enable
        :param int duration: duration in days
        :rtype: dict
        :return: {"success": 1,"message": "Loan order placed.",
                  "orderID": 10590}
        """
        result = self._trading_api(
            command='createLoanOffer', currency=str(currency).upper(),
            amount=amount, duration=duration, lendingRate=lending_rate,
            auto_renew=int(auto_renew)
        )
        return result

    def cancel_loan_offer(self, order_number):
        """
        Cancels a loan offer specified by the "order_number" parameter.

        :param string order_number: "orderID" from create_loan call.
        :rtype: dict
        :return: {"success": 1, "message": "Loan offer canceled."}
        """
        result = self._trading_api(
            command='cancelLoanOffer', orderNumber=order_number
        )
        return result

    def open_loan_offers(self):
        """
        Returns your open loan offers for each currency.

        :rtype: dict
        :return: {"BTC": [{"id": 10595, "rate": "0.00020000",
                           "amount": "3.00000000","duration": 2,
                           "autoRenew": 1, "date":"2015-05-10 23:33:50"}
                          ],
                  "LTC":[{"id": 10598, "rate": "0.00002100",
                          "amount": "10.00000000", "duration": 2,
                          "autoRenew": 1, "date": "2015-05-10 23:34:35"
                          }
                        ]
                  }
        """
        result = self._trading_api(command='returnOpenLoanOffers')
        return result

    def active_loans(self):
        """
        Returns your active loans for each currency.

        :rtype: dict
        :return: {"provided": [{"id":75073, "currency": "LTC",
                                "rate": "0.00020000", "amount":"0.72234880",
                                "range": 2, "autoRenew": 0,
                                "date":"2015-05-10 23:45:05",
                                "fees": "0.00006000"},
                               {"id": 74961, "currency": "LTC",
                                "rate": "0.00002000", "amount": "4.43860711",
                                "range": 2, "autoRenew": 0,
                                "date":"2015-05-10 23:45:05",
                                "fees":"0.00006000"}
                               ],
                  "used": [{"id": 75238, "currency": "BTC", "rate":"0.00020000",
                            "amount": "0.04843834", "range":2,
                            "date": "2015-05-10 23:51:12",
                            "fees":"-0.00000001"}
                           ]
                  }
        """
        result = self._trading_api(command='returnActiveLoans')
        return result

    def lending_history(self, start=0, end=0, limit=0):
        """
        Returns your lending history within a time range specified by the
        "start" and "end" parameters as UNIX timestamps. "limit" may also be
        specified to limit the number of rows returned.

        :param int start: positive int representing UNIX timestamp
        :param int end: positive int representing UNIX timestamp
        :param int limit: number of entries
        :rtype: dict
        :return: [{ "id": 175589553, "currency": "BTC", "rate": "0.00057400",
                    "amount": "0.04374404", "duration": "0.47610000",
                    "interest": "0.00001196", "fee": "-0.00000179",
                    "earned": "0.00001017", "open": "2016-09-28 06:47:26",
                    "close": "2016-09-28 18:13:03"
                  }]
        """
        if start <= 0:
            start = time() - DAY * 30
        if end <= 0 or end < start:
            end = time()
        kwargs = {
            'command': 'returnLendingHistory', 'start': start, 'end': end
        }
        if limit > 0:
            kwargs['limit'] = limit

        result = self._trading_api(**kwargs)
        return result

    def toggle_loan_auto_renew(self, order_number):
        """
        Toggles the autoRenew setting on an active loan, specified by the
        "order_number" parameter. If successful, "message" will indicate the
        new auto_renew setting.

        :rtype: dict
        :param order_number: order id
        :return: {"success": 1, "message": 0}
        """
        result = self._trading_api(
            command='toggleAutoRenew', orderNumber=order_number
        )
        return result
