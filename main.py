import sys
import os
import io

from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS
from memory_profiler import profile

from opas import Opas

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

api = Flask(__name__)
CORS(api)

# TODO メモリ使用量を調べる
@profile
@api.route('/vacants', methods=['GET'])
def get_vacant(debug=False):
    opas = Opas()
    debug = int(request.args.get('debug', 0))
    res = opas.get_vacant(debug)
    # TODO https://reserve.opas.jp/osakashi/yoyaku/CalendarStatusSelect.cgi を始点に
    # debug: 1=debug, 0=no debug
    return res


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO,
    #                     format='%(levelname)s: %(message)s')
    # logging.disable(logging.CRITICAL)
    api.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
