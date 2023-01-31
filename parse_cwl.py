import sys
import re

from datetime import datetime as dt


class RegexCapture:
    """
    Capture useful bits of information in a given CWL log.
    """

    def __init__(self, line: str = "") -> None:
        super().__init__()
        self.tool_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) (INFO|DEBUG) (\[job ([^\s]+)])+.*"
        )
        self.filename_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) (INFO|DEBUG) (\[job ([^\s]+)])+.*from file.*"
        )
        self.filename = re.compile(r"\/[^s].*\/([^s].*).cwl")
        self.line = line

    def set_line(self, new_line):
        self.line = new_line

    def is_filename_line(self) -> bool:
        return self.filename_line.match(self.line)

    def get_datetime(self) -> dt:
        match = self.tool_line.match(self.line)
        if match:
            new_dt = dt(
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                int(match.group(5)),
                int(match.group(6)),
                int(match.group(7)),
            )
            return new_dt
        else:
            return None

    def get_filename(self):
        if self.is_filename_line():
            match = self.filename.search(self.line)
            if match:
                return re.sub(r".*\/", "", match.group(1))

        return None


if __name__ == "__main__":
    # outfile = open("tool_list.txt", 'w')
    with open(sys.argv[1], "r", newline="\n\[") as infile:
        re_cap = RegexCapture()
        # print(infile)
        # data = infile.read().replace("\n\[")
        for line in infile.readlines():
            print(line)
        # for line in infile.readlines():
        #     line = line.strip()
        #     re_cap.set_line(line)
        #     filename = re_cap.get_filename()
        #     if filename:
        #         datetime = re_cap.get_datetime()
        #         print(filename, datetime)
