import re

with open("socks5.output", "r") as f:
    lines = f.read().splitlines()

ips = []
out = []

for line in lines:
    m = re.search (r'"IP": "(.*?)"', line)
    if m:
        ip = m.group(1)
        ips.append(ip)
    m = re.search (r'"outgoing IP": (.*)', line)
    if m:
        out.append(m.group(1).replace('"', '').replace(",", ""))

thesame = 0
empty = 0
different = 0

for ip, outip in zip(ips, out):
#    print(ip, outip)
    if outip == "null":
        empty += 1
    elif ip == outip:
        thesame += 1
    else:
        different +=1

print(f"{thesame=} {empty=} {different=}")
