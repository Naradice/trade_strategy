import curses

def main(stdscr):
    curses.raw()

    ch = None
    while ch != 10:
        ch = stdscr.getch(
            curses.LINES - 1, 0
        )
        print(ch)

if __name__ == '__main__':
    curses.wrapper(main)