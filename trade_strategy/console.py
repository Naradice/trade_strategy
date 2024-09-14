import curses
import json
import os
import threading
from logging import getLogger, config, Handler, INFO


def initialize_logger(logger=None, log_level=INFO, name="trade_strategy.main"):
    if logger is None:
        dir = os.path.dirname(__file__)
        try:
            with open(os.path.join(dir, "./settings.json"), "r") as f:
                settings = json.load(f)
        except Exception as e:
            print(f"fail to load settings file on strategy main: {e}")
            raise e
        logger_config = settings["log"]
        if log_level is not None:
            try:
                logger_config[name]["level"] = log_level
            except:
                pass
        try:
            config.dictConfig(logger_config)
        except Exception as e:
            print(f"fail to set configure file on strategy main: {e}")
            raise e
        logger = getLogger(name)
    else:
        logger = logger
    return logger


class Command:
    disable = "disable"
    disable_long = "disable long"
    disable_short = "disable short"
    enable = "enable"
    enable_long = "enable long"
    enable_short = "enable short"
    update = "update"
    end = "exit"


class CursesHandler(Handler):
    def __init__(self, stdscr, input_box):
        super().__init__()
        self.stdscr = stdscr
        self.input_box = input_box
        self.log_lines = []
        self.max_lines = curses.LINES - 4

    def emit(self, record):
        if record is not None:
            log_entry = self.format(record)
            self.log_lines.append(log_entry)
        if len(self.log_lines) > self.max_lines:
            self.log_lines.pop(0)

        self.stdscr.clear()
        for idx, line in enumerate(self.log_lines):
            self.stdscr.addstr(idx, 0, line)
        self.stdscr.addstr(curses.LINES - 3, 0, "-" * curses.COLS)
        self.stdscr.addstr(
            curses.LINES - 1,
            0,
            f"Command: {self.input_box.get_current_input()}",
        )
        self.stdscr.refresh()


class InputBox:
    def __init__(self):
        self.current_input = ""

    def add_char(self, ch):
        if ch == curses.KEY_BACKSPACE or ch == 8:
            self.current_input = self.current_input[:-1]
        else:
            self.current_input += chr(ch)

    def get_current_input(self):
        return self.current_input

    def reset(self):
        self.current_input = ""


class Console:
    def __init__(self, logger=None, log_level=None) -> None:
        if log_level is None:
            self.log_level = INFO
        else:
            self.log_level = log_level
        if logger is None:
            dir = os.path.dirname(__file__)
            try:
                with open(os.path.join(dir, "./settings.json"), "r") as f:
                    settings = json.load(f)
            except Exception as e:
                self.logger.error(f"fail to load settings file on strategy main: {e}")
                raise e
            logger_config = settings["log"]
            try:
                config.dictConfig(logger_config)
            except Exception as e:
                self.logger.error(f"fail to set configure file on strategy main: {e}")
                raise e
            self.logger = getLogger("trade_strategy")
        else:
            self.logger = logger
        self.logger.setLevel(self.log_level)
        self.done = False

    def _start(self, stdscr, pipe):
        input_box = InputBox()
        curses_handler = CursesHandler(stdscr, input_box)
        curses_handler.setLevel(self.log_level)
        self.logger.addHandler(curses_handler)
        t = threading.Thread(
            target=self._wait_input,
            args=(stdscr, pipe, input_box, curses_handler),
        )
        t.start()

    def _wait_input(self, stdscr, pipe, input_box, curses_handler):
        user_input = None
        stdscr.timeout(5000)
        while user_input != Command.end and self.done is False:
            ch = stdscr.getch(
                curses.LINES - 1,
                len("Command: ") + len(input_box.get_current_input()),
            )
            if ch != -1:
                stdscr.timeout(-1)
                if ch == 10:
                    user_input = input_box.get_current_input()
                    try:
                        pipe.send(user_input)
                    except Exception:
                        pass
                    stdscr.refresh()
                    input_box.reset()
                    if user_input == Command.end:
                        self.close()
                        break
                    else:
                        stdscr.timeout(5000)
                else:
                    input_box.add_char(ch)

    def input(self, pipe):
        curses.wrapper(self._start, pipe=pipe)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warn(self, msg):
        self.logger.warn(msg)

    def close(self):
        self.logger.info("close console window")
        try:
            curses.endwin()
        except Exception as e:
            self.logger.error(f"failed to close console window: {e}")
            print(e)
        self.done = True
