import asyncio
import argparse
import calendar
import datetime
import json
import logging
import random
import re
import shlex
import time
import traceback
import urllib.parse


class BufferedProtocol(asyncio.SubprocessProtocol):
    def __init__(self, exit_future, callbacks):
        self.exit_future = exit_future
        self.callbacks = callbacks
        self.buf = ""

    def pipe_data_received(self, fd, data):
        self.buf += data.decode("utf-8")

        lines = self.buf.split("\n")
        if len(lines) > 1:
            self.buf = lines[-1]
            for line in lines[:-1]:
                m = Measure(line)
                if m.is_valid():
                    for cb in self.callbacks:
                        cb(m)

    def process_exited(self):
        self.exit_future.set_result(True)


class MeasureNamer:
    # ["outputname", "model=foo", "channel=\\d+"]
    def __init__(self, fname=None):
        self.matchers = []
        if fname is None:
            return
        with open(fname) as f:
            for line in f.readlines():
                if line.startswith("#") or len(line.strip()) == 0:
                    continue
                try:
                    tokens = json.loads(line)
                    pairs = (t.split("=", maxsplit=1) for t in tokens[1:])
                    rules = (
                        lambda o, k=p[0], x=re.compile(p[1]): x.fullmatch(str(o.get(k)))
                        for p in pairs
                    )
                    self.matchers.append({"rules": list(rules), "name": tokens[0]})
                except:
                    print("cannot parse:", line)
                    traceback.print_exc()
        print("have", len(self.matchers), "naming matcher(s)")

    def name(self, raw):
        for m in self.matchers:
            if all(r(raw) is not None for r in m["rules"]):
                return m["name"]
        return None


class Measure:
    def __init__(self, raw):
        self.raw = raw
        self.timestamp = -1
        self.fields = {}
        self.values = {}

        try:
            j = json.loads(raw)
        except json.JSONDecodeError:
            logging.error("invalid json: %s", raw)
            return

        for type in ("temperature_C", "humidity", "battery"):
            value = j.get(type)
            if value is None:
                continue

            if type == "battery":
                value = int(value.lower() == "ok")

            self.values[type] = value

        try:
            name = measure_namer.name(j)
            if name is not None:
                self.fields["name"] = name

            for key in ("model", "id", "device", "channel"):
                if key in j:
                    self.fields[key] = j[key]
            self.timestamp = calendar.timegm(
                time.strptime(j.get("time"), "%Y-%m-%d %H:%M:%S")
            )
        except Exception:
            logging.warning("invalid message: %s", raw)
            traceback.print_exc()

    def is_valid(self):
        return self.timestamp != -1

    def as_payload(self):
        return "measure,{} {} {}".format(
            ",".join("{}={}".format(k, v) for k, v in self.fields.items()),
            ",".join("{}={}".format(k, v) for k, v in self.values.items()),
            self.timestamp,
        )

    def as_json(self):
        return self.__dict__


async def post_measurement(url, m):
    url = urllib.parse.urlsplit(url + "&precision=s")
    payload = m.as_payload().encode("utf-8")

    query = "POST {}?{} HTTP/1.0\r\nContent-Length: {}\r\n\r\n".format(
        url.path, url.query, len(payload)
    ).encode("utf-8")

    _, writer = await asyncio.open_connection(url.hostname, url.port)
    writer.write(query)
    writer.write(payload)
    writer.close()


async def listen_radio(args, callbacks):
    while True:
        exit_future = asyncio.Future(loop=loop)

        cmd = "{} -M utc -C si -F json -T 86400".format(args.rtl_433_bin)
        # cmd = '/home/sebastian/rtl_433/build/src/rtl_433 -U -C si -F json'
        # cmd = 'sleep 10'

        # Create the subprocess controlled by the protocol BufferedProtocol,
        # redirect the standard output into a pipe
        transport, _ = await loop.subprocess_exec(
            lambda: BufferedProtocol(exit_future, callbacks),
            *shlex.split(cmd),
            stdin=None,
            stderr=None
        )

        await exit_future

        transport.close()  # Close the stdout pipe


async def listen_random(args, callbacks):
    exit_future = asyncio.get_running_loop().create_future()
    protocol = BufferedProtocol(exit_future, callbacks)
    await asyncio.sleep(0.5)
    while True:
        protocol.pipe_data_received(
            -1,
            (
                json.dumps(
                    {
                        "id": "1",
                        "device": "foo",
                        "channel": 42,
                        "model": "unknown",
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "temperature_C": random.uniform(20, 25),
                    }
                )
                + "\n"
            ).encode("utf-8"),
        )
        await asyncio.sleep(2)
    await exit_future


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="weatherpi to influxdb adapter")
    ap.add_argument(
        "--rtl_433_bin",
        help="path to rtl_443 binary",
        default="/home/sebastian/rtl_433/build/src/rtl_433",
    )
    ap.add_argument(
        "--influxdb_url",
        help="where to send the measurements",
        default="http://localhost:8086/api/v2/write?bucket=weatherpi",
    )
    ap.add_argument(
        "--verbose", "-v", help="print more stuff", nargs="?", const=True, default=False
    )
    ap.add_argument(
        "--no_radio", help="invent random data", nargs="?", const=True, default=False
    )
    ap.add_argument(
        "--no_send", help="dont send measurements", nargs="?", const=True, default=False
    )
    ap.add_argument(
        "--naming_rules", help="/path/to/naming_rules.txt", nargs="?", action="store"
    )

    ap.print_help()
    args = ap.parse_args()

    measure_namer = MeasureNamer(args.naming_rules)

    callbacks = []
    if not args.no_send:
        callbacks.append(
            lambda m: asyncio.ensure_future(post_measurement(args.influxdb_url, m))
        )
    if args.verbose:
        callbacks.append(lambda m: print(json.dumps(m.as_json())))

    loop = asyncio.get_event_loop()
    if not args.no_radio:
        loop.run_until_complete(listen_radio(args, callbacks))
    else:
        loop.run_until_complete(listen_random(args, callbacks))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
