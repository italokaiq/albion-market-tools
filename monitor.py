"""Monitor local do fluxo público AODP Américas. Python 3.12, sem dependências."""
import json
import socket
import sqlite3
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk

DB = Path(__file__).with_name('mercado.sqlite3')
HOST = 'nats.albion-online-data.com'
TOPIC = 'marketorders.deduped'


def database(path=DB):
    con = sqlite3.connect(path, timeout=10)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT, location TEXT, item TEXT, quality INTEGER, enchantment INTEGER,
        side TEXT, price INTEGER, amount INTEGER, seen REAL,
        PRIMARY KEY(id, location))''')
    con.execute('CREATE INDEX IF NOT EXISTS orders_seen ON orders(seen)')
    con.execute('CREATE INDEX IF NOT EXISTS orders_item_seen ON orders(item,seen)')
    return con


def save_order(con, order, now=None):
    now = time.time() if now is None else now
    if not isinstance(order, dict):
        raise ValueError('Ordem inválida')
    oid, location = str(order['Id']), str(order['LocationId'])
    amount = int(order['Amount'])
    if amount <= 0:
        con.execute('DELETE FROM orders WHERE id=? AND location=?', (oid, location))
        return
    price = int(order['UnitPriceSilver'])
    side = order['AuctionType']
    if price <= 0 or side not in ('offer', 'request'):
        raise ValueError('Preço ou tipo de ordem inválido')
    con.execute('INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?)',
                (oid, location, str(order['ItemTypeId']), int(order['QualityLevel']),
                 int(order['EnchantmentLevel']), side, price, amount, now))


class Feed:
    def __init__(self, path=DB):
        self.path = path
        self.stop = threading.Event()
        self.status = 'Conectando ao servidor Américas…'
        self.count = 0
        self.invalid = 0
        self.last = None
        self.sock = None

    def run(self):
        con = database(self.path)
        delay = 2
        try:
            while not self.stop.is_set():
                try:
                    self.status = 'Conectando ao servidor Américas…'
                    with socket.create_connection((HOST, 4222), timeout=10) as sock:
                        self.sock = sock
                        sock.settimeout(45)
                        with sock.makefile('rb') as stream:
                            info = stream.readline(65536)
                            if not info.startswith(b'INFO '):
                                raise ValueError('Resposta NATS inesperada')
                            options = dict(user='public', password='thenewalbiondata')
                            connect = {'user': options['user'], 'pass': options['password'],
                                       'verbose': False, 'pedantic': False,
                                       'lang': 'python', 'version': '1.0',
                                       'name': 'Albion Americas Monitor'}
                            sock.sendall(('CONNECT ' + json.dumps(connect) + '\r\n'
                                          'SUB ' + TOPIC + ' 1\r\nPING\r\n').encode())
                            flushed = time.monotonic()
                            while not self.stop.is_set():
                                line = stream.readline(65536)
                                if not line:
                                    raise ConnectionError('Conexão encerrada')
                                if line == b'PING\r\n':
                                    sock.sendall(b'PONG\r\n')
                                elif line == b'PONG\r\n':
                                    self.status = 'Conectado ao fluxo das Américas'
                                    delay = 2
                                elif line.startswith(b'-ERR'):
                                    raise ConnectionError(line.decode(errors='replace').strip())
                                elif line.startswith(b'MSG '):
                                    size = int(line.split()[-1])
                                    if not 0 <= size <= 4_194_304:
                                        raise ValueError('Mensagem excede limite')
                                    payload = stream.read(size)
                                    if len(payload) != size or stream.read(2) != b'\r\n':
                                        raise ConnectionError('Mensagem incompleta')
                                    try:
                                        data = json.loads(payload)
                                        batch = data.get('Orders', [data]) if isinstance(data, dict) else data
                                        if not isinstance(batch, list):
                                            raise ValueError('Formato desconhecido')
                                        for order in batch:
                                            save_order(con, order)
                                            self.count += 1
                                        self.last = time.time()
                                    except (ValueError, KeyError, TypeError):
                                        self.invalid += 1
                                if time.monotonic() - flushed >= 1:
                                    con.execute('DELETE FROM orders WHERE seen < ?', (time.time()-86400,))
                                    con.commit()
                                    flushed = time.monotonic()
                except (OSError, ValueError, sqlite3.Error) as exc:
                    self.status = f'Sem conexão: {exc}. Nova tentativa em {delay}s.'
                finally:
                    self.sock = None
                    con.commit()
                if self.stop.wait(delay):
                    break
                delay = min(delay * 2, 60)
        finally:
            con.close()

    def close(self):
        self.stop.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


from dashboard import Dashboard


class App(Dashboard):
    def __init__(self, root):
        super().__init__(root, database(), Feed())


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
