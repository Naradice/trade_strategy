import unittest, os, sys, multiprocessing, time, datetime

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
from trade_strategy import console, main


class Test(unittest.TestCase):
    def test_console(self):
        parent, child = multiprocessing.Pipe()
        logger = console.Console()
        logger.input(child)
        logger.info("start console")

        delta = datetime.timedelta(seconds=10)
        start_date = datetime.datetime.now() + delta
        end_date = start_date + delta
        timer = main.Timer(start_date=start_date, end_date=end_date, logger=logger)
        cmd = None
        timer(child, update_frame_minutes=0.1)
        while cmd != console.Command.end:
            cmd = parent.recv()
            if cmd == console.Command.update:
                logger.info("update status")
        logger.close()


if __name__ == "__main__":
    unittest.main()
