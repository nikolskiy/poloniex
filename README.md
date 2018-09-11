# Poloniex
Poloniex python API wrapper for aerials. There is already awesome [Poloniex python API client for humans](https://github.com/Aula13/poloniex).
What if aerials need a python Poloniex wrapper as well? ;)

## Description
I'm not associated with Poloniex by any means. Everything is based on their [API description](https://poloniex.com/support/api/)
and inspired by other similar projects from Github.

## Installation
`pip install git+git://github.com/nikolskiy/poloniex.git`

## Usage examples
For examples check out [jupyter notebook](examples.ipynb) and [async example](async_example.py)

## Status
Currently the project is in test drive mode. This package includes standard HTTP requests 
and separate async helpers to subscribe to websocket events. I'm not sure yet which direction to take the project. 
One option is to keep them separate. The other is to make async friendly version for everything. 
I plan to use it for a bit and see what is more practical.
