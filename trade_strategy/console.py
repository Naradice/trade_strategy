import json
import logging
import os
import threading
import textwrap
from logging import getLogger, config, Handler, INFO

try:
    import curses
    _CURSES_AVAILABLE = True
    ENTER_KEY = curses.KEY_ENTER
    END_KEY = curses.KEY_END
except ImportError:
    curses = None
    _CURSES_AVAILABLE = False
    ENTER_KEY = 13  # Windows Enter
    END_KEY = 3     # Ctrl+C


def initialize_logger(log_level=INFO, name="trade_strategy.main"):
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
        except KeyError:
            pass
    try:
        config.dictConfig(logger_config)
    except Exception as e:
        print(f"fail to set configure file on strategy main: {e}")
        raise e
    return getLogger(name)


class Command:
    disable = "/disable"
    disable_long = "/disable long"
    disable_short = "/disable short"
    enable = "/enable"
    enable_long = "/enable long"
    enable_short = "/enable short"
    update = "/update"
    end = "/exit"

    @classmethod
    def all_commands(cls):
        return [cls.disable, cls.disable_long, cls.disable_short, cls.enable, cls.enable_long, cls.enable_short, cls.update, cls.end]


class CursesHandler(Handler):
    INPUT_AREA_HEIGHT = 3

    def __init__(self, stdscr, input_box):
        super().__init__()
        self.stdscr = stdscr
        self.input_box = input_box
        self.log_lines = []
        self.max_lines = max(curses.LINES - (self.INPUT_AREA_HEIGHT + 2), 1)

    def _update_layout(self):
        self.max_lines = max(curses.LINES - (self.INPUT_AREA_HEIGHT + 2), 1)
        self.log_separator_row = self.max_lines
        self.prompt_row = self.log_separator_row + 1
        self.input_rows = [self.prompt_row + offset for offset in range(1, self.INPUT_AREA_HEIGHT)]
        self.bottom_separator_row = self.prompt_row + self.INPUT_AREA_HEIGHT

    def _draw_line(self, row, text, column=0):
        if row < 0 or row >= curses.LINES or column >= curses.COLS:
            return
        available_width = max(curses.COLS - column - 1, 0)
        self.stdscr.addstr(row, column, str(text)[:available_width])

    def _get_command_lines(self, current_input):
        if current_input.startswith("/"):
            matching = [cmd for cmd in Command.all_commands() if cmd.startswith(current_input)]
            if not matching:
                return [f"No matching commands for: {current_input}"]
            available_width = max(curses.COLS - 1, 20)
            wrapped_lines = textwrap.wrap(
                "Matches: " + ", ".join(matching),
                width=available_width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            return wrapped_lines[: self.INPUT_AREA_HEIGHT - 1]
        return ["Type / to list commands"]

    def render(self):
        self._update_layout()
        if len(self.log_lines) > self.max_lines:
            self.log_lines = self.log_lines[-self.max_lines :]

        current_input = self.input_box.get_current_input()
        self.stdscr.clear()

        visible_logs = self.log_lines[-self.max_lines :]
        for idx, line in enumerate(visible_logs):
            self._draw_line(idx, line)

        separator = "-" * max(curses.COLS - 1, 1)
        self._draw_line(self.log_separator_row, separator)
        self._draw_line(self.prompt_row, f"Command: {current_input}")

        command_lines = self._get_command_lines(current_input)
        for row, text in zip(self.input_rows, command_lines):
            self._draw_line(row, text)

        self._draw_line(self.bottom_separator_row, separator)
        self.stdscr.move(self.prompt_row, min(len("Command: ") + len(current_input), max(curses.COLS - 1, 0)))
        self.stdscr.refresh()

    def emit(self, record):
        self._update_layout()
        if record is not None:
            log_entry = self.format(record)
            self.log_lines.append(log_entry)
        self.render()


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
    def __init__(self, log_level=None, log_file="trade_strategy.log", file_log_level=logging.ERROR) -> None:
        if log_level is None:
            self.log_level = INFO
        else:
            self.log_level = log_level
        self.log_file = log_file
        self.file_log_level = file_log_level
        dir = os.path.dirname(__file__)
        try:
            with open(os.path.join(dir, "./settings.json"), "r") as f:
                settings = json.load(f)
            logger_config = settings["log"]
            config.dictConfig(logger_config)
        except Exception as e:
            print(f"Console: could not load settings.json, using basic logger ({e})")
        self.logger = getLogger("trade_strategy")
        self.logger.setLevel(self.log_level)
        self.done = False
        self.thread = None
        self._curses_handler = None
        self._file_handler = None
        self._attached_loggers = []
        self._file_attached_loggers = []

    def _get_target_loggers(self):
        targets = []
        seen_names = set()

        def add_target(target_logger):
            if target_logger is None or target_logger.name in seen_names:
                return
            seen_names.add(target_logger.name)
            targets.append(target_logger)

        add_target(self.logger)
        add_target(getLogger("trade_strategy"))

        for name, logger_obj in logging.Logger.manager.loggerDict.items():
            if (
                isinstance(logger_obj, logging.Logger)
                and name.startswith("trade_strategy.")
                and (logger_obj.handlers or logger_obj.propagate is False)
            ):
                add_target(logger_obj)

        return targets

    def _attach_handler(self, handler: Handler):
        formatter = None
        for target_logger in self._get_target_loggers():
            for existing_handler in target_logger.handlers:
                if existing_handler.formatter is not None:
                    formatter = existing_handler.formatter
                    break
            if formatter is not None:
                break

        if formatter is not None:
            handler.setFormatter(formatter)

        self._attached_loggers = []
        for target_logger in self._get_target_loggers():
            if handler not in target_logger.handlers:
                target_logger.addHandler(handler)
                self._attached_loggers.append(target_logger)

    def _detach_handler(self):
        if self._curses_handler is not None:
            for target_logger in self._attached_loggers:
                if self._curses_handler in target_logger.handlers:
                    target_logger.removeHandler(self._curses_handler)
            self._attached_loggers = []

        if self._file_handler is not None:
            for target_logger in self._file_attached_loggers:
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None
            self._file_attached_loggers = []

    def _attach_file_handler(self):
        """Attach a FileHandler for the console session if one isn't already writing to log_file."""
        for target_logger in self._get_target_loggers():
            for h in target_logger.handlers:
                if isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(self.log_file):
                    return  # already covered by existing config

        formatter = None
        for target_logger in self._get_target_loggers():
            for h in target_logger.handlers:
                if h.formatter is not None:
                    formatter = h.formatter
                    break
            if formatter is not None:
                break

        fh = logging.FileHandler(self.log_file, encoding="utf-8")
        fh.setLevel(self.file_log_level)
        if formatter is not None:
            fh.setFormatter(formatter)
        self._file_handler = fh
        self._file_attached_loggers = []
        for target_logger in self._get_target_loggers():
            target_logger.addHandler(fh)
            self._file_attached_loggers.append(target_logger)

    def _start(self, pipe):
        if not _CURSES_AVAILABLE:
            raise RuntimeError("console_mode requires the 'windows-curses' package on Windows: pip install windows-curses")
        curses.wrapper(self._wait_input, pipe=pipe)

    def _wait_input(self, stdscr, pipe):
        # https://github.com/zephyrproject-rtos/windows-curses/issues/8
        curses.raw()
        if hasattr(curses, "curs_set"):
            curses.curs_set(1)
        input_box = InputBox()
        curses_handler = CursesHandler(stdscr, input_box)
        curses_handler.setLevel(self.log_level)
        self._curses_handler = curses_handler
        self._attach_handler(curses_handler)
        self._attach_file_handler()
        try:
            curses_handler.render()

            user_input = None
            stdscr.timeout(5000)

            while self.done is False:
                ch = stdscr.getch(
                    curses_handler.prompt_row,
                    len("Command: ") + len(input_box.get_current_input()),
                )
                if ch != -1:
                    stdscr.timeout(-1)
                    # enter
                    if ch == 13:
                        user_input = input_box.get_current_input()
                        try:
                            pipe.send(user_input)
                        except BrokenPipeError:
                            self.close()
                            break
                        stdscr.refresh()
                        input_box.reset()
                        curses_handler.emit(None)
                        if user_input == Command.end:
                            self.close()
                            break
                        else:
                            stdscr.timeout(5000)
                    # Ctrl+c
                    elif ch == 3:
                        self.logger.error("Keyboard Interupt on console thread")
                        pipe.send(Command.end)
                        self.close()
                        break
                    else:
                        input_box.add_char(ch)
                        curses_handler.emit(None)
        finally:
            self._detach_handler()
            self._curses_handler = None

    def input(self, pipe):
        self.done = False
        self.thread = threading.Thread(target=self._start, args=(pipe,), daemon=True)
        self.thread.start()

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def warn(self, msg):
        self.logger.warning(msg)

    def close(self):
        self.logger.debug("close console window")
        try:
            curses.endwin()
        except Exception as e:
            self.logger.error(f"failed to close console window: {e}")
        self.done = True
        if self.thread is not None:
            if self.thread is not threading.current_thread():
                self.thread.join()
