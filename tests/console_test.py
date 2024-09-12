import unittest, os, sys, multiprocessing, time
from logging import DEBUG

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
from trade_strategy import console


class Test(unittest.TestCase):
    def test_console(self):
        parent, child = multiprocessing.Pipe()
        logger = console.Console(log_level=DEBUG)
        logger.input(child)
        logger.info("start testing console")
        cmd = None
        while cmd != console.Command.end:
            cmd = parent.recv()
            logger.info(f"received {cmd}")
        logger.info("finish testing console")


if __name__ == "__main__":
    unittest.main()
