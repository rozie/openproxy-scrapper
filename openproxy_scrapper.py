#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import logging
import re
import socket
import threading
import time
from contextlib import closing

import requests
import yaml

# from typing_extensions import Required

logger = logging.getLogger(__name__)

# file_ip_port = "proxy_test.txt"
# timeout = 10
# num_threads = 128
output = {}
proxies = set()


def check_port_open(host, port, timeout):
    # print(host, port)
    res = False
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        if sock.connect_ex((host, port)) == 0:
            res = True
    return res


# with open(file_ip_port, "r", encoding="utf-8") as f:
#     lines = f.readlines()

# proxies = set()
# for line in lines:
#     m = re.search(r"(\d+\.\d+\.\d+\.\d+):(\d+)", line)
#     if m:
#         ip = m.group(1)
#         port = int(m.group(2))
#         proxies.add((ip, port))

# print(f"Have {len(proxies)} proxies")


def worker(timeout):
    # print "worker...."
    while proxies:
        # if len(proxies) % 10 == 0:
        #     print(f"{len(proxies)} left")
        proxy = proxies.pop()
        ip, port, type_ = proxy
        result = check_port_open(ip, port, timeout)
        output[proxy] = result


# print(threads)
print(f"Have {len(output)} results")

# time.sleep(2 * timeout)

for proxy in output.keys():
    ip, port = proxy
    result = output[proxy]
    print(f"{ip}:{port} {result}")

print(f"Have {len(output)} results")


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
    args = parser.parse_args()
    return args


def get_proxies(data, proxy_types, timeout):
    proxies_tmp = set()
    for type_ in proxy_types:
        print(type_)
        for url in data.get(type_):
            # print(url)
            try:
                result = requests.get(url, timeout=timeout)
                # print(result.status_code)
                for line in result.text.splitlines():
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+):(\d+)", line)
                    if m:
                        ip = m.group(1)
                        port = int(m.group(2))
                        # print(ip, port)
                        entry = (ip, port, type_)
                        proxies_tmp.add(entry)
            except Exception as e:
                print(url, e)
    return proxies_tmp


def main():
    args = parse_arguments()

    # set verbosity
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # load config file
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

    print(len(proxies))

    threads = []
    for i in range(args.threads):
        thread = threading.Thread(target=worker, name=i, args=(args.timeout,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    for proxy in output.keys():
        print(proxy, output[proxy])


if __name__ == "__main__":
    main()
