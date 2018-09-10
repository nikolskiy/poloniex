from poloniex.px import run_ticker
import logging

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Starting tracker')
    run_ticker()
