import logging
import time

def initial_log(log_filename = 'log.txt'):
    logging.basicConfig(
        level=logging.INFO,
        format= '[%(name)s-%(levelname)s]-[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        filename = log_filename,
        filemode = 'w'
    )

