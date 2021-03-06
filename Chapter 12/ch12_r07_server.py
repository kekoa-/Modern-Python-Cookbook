"""Python Cookbook

Chapter 12, recipe 7 -- server.
"""
import random
from flask import Flask, jsonify, request, abort, url_for
from ch12_r07_user import User
from ch12_r01 import Card, Deck
from http import HTTPStatus
import logging
import sys


dealer = Flask('dealer')
dealer.DEBUG=True

specification = {
    'swagger': '2.0',
    'info': {
        'title': '''Python Cookbook\nChapter 12, recipe 6.''',
        'version': '1.0'
    },
    'schemes': ['http'],
    'host': '127.0.0.1:5000',
    'basePath': '/dealer',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'paths': {
        '/players': {
            'post': {
                'parameters': [
                        {
                            'name': 'player',
                            'in': 'body',
                            'schema': {'$ref': '#/definitions/player'}
                        },
                    ],
                'responses': {
                    '201': {'description': 'Player created', },
                    '403': {'description': 'Player is invalid or a duplicate'}
                }
            },
            'get': {
                'responses': {
                    '200': {'description': 'All of the players defined so far'},
                }
            }
        },
        '/players/{id}': {
            'get': {
                'parameters': [
                    {
                        'name': 'id',
                        'in': 'path',
                        'type': 'string'
                    }
                ],
                'responses': {
                    '200': {
                        'description': 'The details of a specific player',
                        'schema': {'$ref': '#/definitions/player'},
                        'examples': {
                            'application/json': {
                                'name': 'example',
                                'email': 'example@example.com',
                                'year': 1999,
                                'twiiter': 'https://twitter.com/PacktPub',
                            }
                        }
                    },
                    '404': {'description': 'Player ID not found'}
                }
            }
            # Put
            # Delete
        },
        '/decks/{id}/hands': {
            'get': {
                'parameters': [
                    {
                        'name': 'id',
                        'in': 'path',
                        'type': 'string'
                    },
                    {
                        'name': 'cards',
                        'in': 'query',
                        'type': 'integer',
                        'default': 13,
                        'description': '''number of cards in each hand'''
                    },
                    {
                        'name': '$top',
                        'in': 'query',
                        'type': 'integer',
                        'default': 1,
                        'description': '''number of hands to deal'''
                    },
                    {
                        'name': '$skip',
                        'in': 'query',
                        'type': 'integer',
                        'default': 0,
                        'description': '''number of hands to skip before starting to deal'''
                    }
                ],
                'responses': {
                    '200': {
                        'description': '''One hand of cards for each `hand` value in the query string'''
                    },
                    '400': {
                        'description': '''Request doesn't accept a JSON response'''
                    },
                    '404': {
                        'description': '''ID not found.'''
                    }
                }
            }
        },
        '/decks': {
            'post': {
                'parameters': [
                    {
                        'name': 'size',
                        'in': 'query',
                        'type': 'integer',
                        'default': 1,
                        'description': '''number of decks to build and shuffle'''
                    }
                ],
                'responses': {
                    '200': {
                        'description': '''Create and shuffle a deck. Returns a unique deck id.'''
                    },
                    '400': {
                        'description': '''Request doesn't accept a JSON response'''
                    },
                }
            }
        }
    },
    'definitions': {
        'player': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'email': {'type': 'string', 'format': 'email'},
                'year': {'type': 'integer'},
                'twitter': {'type': 'string', 'format': 'uri'},
                'password': {
                    'type': 'string',
                    'description': 'plain password on a request. Hash on a response.'
                }
            }
        }
    }
}


import os
random.seed(os.environ.get('DEAL_APP_SEED'))
decks = {}
user_database = {}

from functools import wraps
import base64
from flask import g

def authorization_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            abort(HTTPStatus.UNAUTHORIZED)
        kind, data = request.headers['Authorization'].split()
        if kind.upper() != 'BASIC':
            abort(HTTPStatus.UNAUTHORIZED)
        credentials = base64.b64decode(data)
        username_bytes, _, password_bytes = credentials.partition(b':')
        username = username_bytes.decode('ascii')
        password = password_bytes.decode('ascii')
        if username not in user_database:
            abort(HTTPStatus.UNAUTHORIZED)
        if not user_database[username].check_password(password):
            abort(HTTPStatus.UNAUTHORIZED)
        g.user = user_database[username]
        return view_function(*args, **kwargs)
    return decorated_function

@dealer.before_request
def check_json():
    if request.path == '/dealer/swagger.json':
        return
    if 'json' in request.headers.get('Accept', '*/*'):
        return
    if 'json' == request.args.get('$format', 'html'):
        return
    return abort(HTTPStatus.BAD_REQUEST)

from flask import make_response
import json
@dealer.route('/dealer/swagger.json')
def swagger3():
    response = make_response(json.dumps(specification, indent=2).encode('utf-8'))
    response.headers['Content-Type'] = 'application/json'
    return response

from jsonschema import validate
from jsonschema.exceptions import ValidationError
import hashlib

@dealer.route('/dealer/players', methods=['POST'])
def make_player():
    try:
        document = request.json
    except Exception as ex:
        # Document wasn't even JSON. We can fine-tune
        # the error message here.
        raise
    player_schema = specification['definitions']['player']
    try:
        validate(document, player_schema)
    except ValidationError as ex:
        return make_response(ex.message, 403)

    id = hashlib.md5(document['twitter'].encode('utf-8')).hexdigest()
    if id in user_database:
        return make_response('Duplicate player', 403)

    new_user = User(**document)
    new_user.set_password(document['password'])
    user_database[id] = new_user

    response = make_response(
        jsonify(
            status='ok',
            id=id
        ),
        201
    )
    response.headers['Location'] = url_for('get_player', id=str(id))
    return response

@dealer.route('/dealer/players', methods=['GET'])
@authorization_required
def get_players():
    response = make_response(
        jsonify(
            {k: v.to_json() for k,v in user_database.items()}
        )
    )
    response.headers['Content-Type'] = 'application/json;charset=utf-8'
    return response

@dealer.route('/dealer/players/<id>', methods=['GET'])
@authorization_required
def get_player(id):
    if id not in user_database:
        return make_response("{} not found".format(id), 404)

    response = make_response(
        jsonify(
            user_database[id].to_json()
        )
    )
    response.headers['Content-Type'] = 'application/json;charset=utf-8'
    return response

import urllib.parse
import uuid
@dealer.route('/dealer/decks', methods=['POST'])
@authorization_required
def make_deck():
    id = str(uuid.uuid1())
    decks[id]= Deck()
    response_json = jsonify(
        status='ok',
        id=id
    )
    response = make_response(response_json, HTTPStatus.CREATED)
    response.headers['Location'] = url_for('get_deck', id=str(id))
    return response

@dealer.route('/dealer/decks/<id>', methods=['GET'])
@authorization_required
def get_deck(id):
    if id not in decks:
        dealer.logger.debug(id)
        dealer.logger.debug(list(decks.keys()))
        abort(404)
    response = jsonify([c.to_json() for c in decks[id].cards])
    return response

from werkzeug.exceptions import BadRequest

@dealer.route('/dealer/decks/<id>/hands', methods=['GET'])
@authorization_required
def get_hands(id):
    if id not in decks:
        dealer.logger.debug(id)
        return make_response( 'ID {} not found'.format(id), 404)
    try:
        cards = int(request.args.get('cards',13))
        top = int(request.args.get('$top',1))
        skip = int(request.args.get('$skip',0))
        assert skip*cards+top*cards <= len(decks[id].cards), "$skip, $top, and cards larger than the deck"
    except ValueError as ex:
        return BadRequest(repr(ex))
    subset = decks[id].cards[skip*cards:(skip+top)*cards]
    hands = [subset[h*cards:(h+1)*cards] for h in range(top)]
    response = jsonify(
        [
            {'hand':i, 'cards':[card.to_json() for card in hand]}
             for i, hand in enumerate(hands)
        ]
    )
    return response

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    import ssl
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain('ssl.cert', 'ssl.key')
    dealer.run(use_reloader=True, threaded=False, ssl_context=ctx)
