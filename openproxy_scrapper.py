#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import re
import socket
import threading
import time
from contextlib import closing

import requests
import yaml

logger = logging.getLogger(__name__)


output = {}
proxies = set()


def check_port_open(host, port, timeout):
    res = False
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        if sock.connect_ex((host, port)) == 0:
            res = True
    return res


def worker(timeout):
    while proxies:
        proxy = proxies.pop()
        ip, port, type_ = proxy
        result = check_port_open(ip, port, timeout)
        results = {
            'IP': ip,
            'port': port,
            'type': type_,
            'up': result,
            'outgoing IP': None
        }
        output[proxy] = results


def check_reachability_via_proxy(ip, port, url, timeout, type):
    if not type:
        type = "http"
    if type not in ["http", "https", "socks4", "socks5"]:
        return False
    proxy = f"{type}://{ip}:{port}/"
    proxies = {"https": proxy, "http": proxy}
    try:
        response = requests.get(url, proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            origin = response.json().get("origin")
            return origin
    except Exception as e:
        # print(proxy, e)
        return False
    return origin


# # HTTPS check
# url = "https://httpbin.org/ip"
# for proxy in output.keys():
#     ip, port = proxy
#     result = output[proxy]
#     if result:
#         type = None
#         working = check_reachability_via_proxy(ip, port, url, timeout, type)
#         print(f"{ip} :{port} {type} {working}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Openproxy checker")

    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        default=False,
        action="store_true",
        help="Provide verbose output",
    )
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        default="openproxies.yaml",
        help="Configuration file",
    )
    parser.add_argument(
        "-T",
        "--threads",
        required=False,
        type=int,
        default=32,
        help="Number of threads",
    )
    parser.add_argument(
        "-t", "--timeout", required=False, type=int, default=10, help="Timeout"
    )
    parser.add_argument(
        "-p",
        "--proxy-type",
        required=True,
        choices=["http", "https", "socks4", "socks5", "all"],
        help="Proxy type",
    )
    parser.add_argument(
        "-a",
        "--active",
        required=False,
        default=False,
        action="store_true",
        help="Display only active proxies",
    )
    args = parser.parse_args()
    return args


def get_proxies(data, proxy_types, timeout):
    proxies_tmp = set()
    for type_ in proxy_types:
        logger.debug(f"Checking proxy type {type_}")
        for url in data.get(type_):
            try:
                result = requests.get(url, timeout=timeout)
                logger.debug(f"URL: {url}, status: {result.status_code}")
                for line in result.text.splitlines():
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+):(\d+)", line)
                    if m:
                        ip = m.group(1)
                        port = int(m.group(2))
                        entry = (ip, port, type_)
                        proxies_tmp.add(entry)
            except Exception as e:
                print(url, e)
    return proxies_tmp


def display_results(results, only_active):
    output = []
    displayed_count = 0
    for proxy, data in results.items():
        if only_active:
            if data.get('up'):
                output.append(data)
                displayed_count += 1
        else:
            output.append(data)
            displayed_count += 1
    print(json.dumps(output, indent=4))
    logger.debug(f"Displayed {displayed_count} results")


def main():
    args = parse_arguments()

    # set verbosity
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # load config file
    logger.debug("Using config: {args.config}")
    try:
        with open(args.config, "r") as config:
            data = yaml.safe_load(config)
    except Exception as e:
        logger.error("Couldn't read config file %s", e)

    if args.proxy_type == "all":
        proxy_types = ["http", "https", "socks4", "socks5"]
    else:
        proxy_types = [args.proxy_type]
    for proxy in get_proxies(data=data, proxy_types=proxy_types, timeout=args.timeout):
        proxies.add(proxy)

    logger.debug(f"Found {len(proxies)} proxies to check")

    logger.debug(f"Running {args.threads} threads")
    threads = []
    for i in range(args.threads):
        thread = threading.Thread(target=worker, name=i, args=(args.timeout,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    display_results(output, args.active)


if __name__ == "__main__":
    main()
