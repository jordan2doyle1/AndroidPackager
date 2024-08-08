#
# Author Jordan Doyle.
#
# usage: seed.py [-h] -u UPPER -e EXPECTED
#
# options:
#   -h, --help                              show this help message and exit
#   -u UPPER, --upper UPPER                 upper bound
#   -e EXPECTED, --expected EXPECTED        expected random number.
#

import argparse
import logging
import random

argParser = argparse.ArgumentParser()
argParser.add_argument("-u", "--upper", type=int, required=True, help="upper bound")
argParser.add_argument("-e", "--expected", type=int, required=True, help="expected random number")
args = argParser.parse_args()

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s')

for i in range(1000):
    random.seed(i)
    random_number = random.randint(1, args.upper)

    if random_number == args.expected:
        logging.info("Seed value is " + str(i) + ".")
        break
