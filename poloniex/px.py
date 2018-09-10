"""
https://stackoverflow.com/questions/42436264/reading-messages-on-poloniex-trollbox-with-python-autbahn-or-other-socket-module
https://poloniex.com/js/plx_exchage.js?v=060617

async websocket:
https://github.com/aaugustin/websockets/blob/master/example/shutdown.py
https://github.com/aaugustin/websockets/blob/master/example/client.py
"""
import json
import asyncio
import websockets
import signal
import inspect
import logging
from . import settings


class PoloniexTransport:

    url = settings.ws_protocol_url

    async def listener(self):
        self.websocket = await websockets.connect(self.url)
        self.protocol.connection_made(self)

        while self.running:
            msg = await self.websocket.recv()
            self.protocol.data_received(msg)

        await self.websocket.close()
        self.stopped.set_result(True)

    def __init__(self, loop, protocol):
        self.protocol = protocol
        self.loop = loop
        self.running = True
        self.stopped = asyncio.Future()
        loop.add_signal_handler(signal.SIGTERM, self.stop)
        asyncio.ensure_future(self.listener())

    def send(self, data):
        asyncio.ensure_future(self.websocket.send(data))

    def stop(self):
        self.running = False
        self.loop.run_until_complete(self.stopped)


class PoloniexProtocol(asyncio.Protocol):
    transport = None
    subscribe = ''

    def connection_made(self, transport):
        self.transport = transport
        self.transport.send(self.subscribe)

    def data_received(self, data):
        self.frame_received(json.loads(data))

    def frame_received(self, data):
        logging.error('Not implemented')


class TickerProtocol(PoloniexProtocol):
    subscribe = '{"command" : "subscribe", "channel" : 1002}'
    fields = settings.ws_fields_in_order
    markets = ['BTC_ETH']
    exchange_ids_to_names = settings.exchange_ids_to_names

    def frame_received(self, data):
        if data[0] != 1002:
            return

        if data[1] is None:
            self.parse_ticker(data[2])
            return

        if data[1] == 1:
            logging.info('Subscribed to ticker stream.')
            return

        if data[1] == 0:
            logging.info('Unsubscribed from ticker stream.')
            return

    def parse_ticker(self, data):
        frame = {self.fields[i]: v for i, v in enumerate(data)}
        if self.exchange_ids_to_names:
            frame['name'] = self.exchange_ids_to_names.get(frame['id'])

        self.ticker_received(frame)

    def ticker_received(self, data):
        logging.info(data)


def factory(loop, protocol):
    if inspect.isclass(protocol):
        protocol = protocol()
    transport = PoloniexTransport(loop, protocol)
    return transport, protocol


def run_ticker():
    loop = asyncio.get_event_loop()
    t, p = factory(loop, TickerProtocol)
    p.markets = []
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        t.stop()
        loop.stop()
        loop.close()
