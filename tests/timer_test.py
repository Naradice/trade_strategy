import unittest, os, sys, multiprocessing, datetime, logging

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
from trade_strategy.main import Timer, Command


class Test(unittest.TestCase):
    def test_timer(self):
        parent, child = multiprocessing.Pipe()
        logger = logging.getLogger("test_timer")
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

        delta = datetime.timedelta(seconds=10)
        start_date = datetime.datetime.now() + delta
        end_date = start_date + delta
        timer = Timer(start_date=start_date, end_date=end_date, logger=logger)
        timer(child, update_frame_minutes=0.1)
        msg = None
        while msg != Command.end:
            start_time = datetime.datetime.now()
            msg = parent.recv()
            received_time = datetime.datetime.now()
            logger.debug(f"received: {msg} ({received_time - start_time})")


if __name__ == "__main__":
    unittest.main()
