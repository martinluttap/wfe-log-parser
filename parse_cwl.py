import json
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
        self.input_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) DEBUG (\[job ([^\s]+)]) (\{.*\})"
        )
        self.filename = re.compile(r"\/[^s].*\/([^s].*).cwl")
        self.datetime = re.compile(r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\])")
        self.line = line

    def set_line(self, new_line):
        self.line = new_line

    def is_filename_line(self) -> bool:
        return self.filename_line.match(self.line)
    
    def is_input_line(self) -> bool:
        return self.input_line.match(self.line)

    def is_tool_line(self) -> bool:
        return self.tool_line.match(self.line)
    
    def has_datetime(self) -> bool:
        return self.datetime.match(self.line)

    def get_tool_to_filename(self): 
        match = self.is_filename_line()
        if match:
            toolname = match.group(10)
            filename = self.get_filename()

            return toolname, filename
        else:
            return None

    def get_toolname(self): 
        match = self.is_tool_line()
        if match:
            return match.group(10)
        else:
            return None

    def get_input(self): 
        match = self.is_input_line()
        if match:
            input_json = json.loads(match.group(10))
            return input_json
        else:
            return None

    def get_datetime(self) -> dt:
        match = self.is_tool_line()
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


def concat_same_datetime(infile):
    re_cap = RegexCapture()
    new_infile = []
    aggr_line = [] # Aggregated line based on one datetime
    for line in infile.readlines():
        line = line.strip()
        re_cap.set_line(line)

        if not aggr_line and re_cap.has_datetime():
            aggr_line.append(line)
        else: # aggr_line or not has_datetime
            if aggr_line and re_cap.has_datetime():
                new_line = ' '.join(aggr_line)
                new_infile.append(new_line)
                aggr_line = []
            elif aggr_line and not re_cap.has_datetime():
                aggr_line.append(line) 

    return new_infile

def get_tool_filename_dict(infile):
    re_cap = RegexCapture()
    tool_filename_dict = {}
    for line in infile.readlines():
        line = line.strip()
        re_cap.set_line(line)
        tuple = re_cap.get_tool_to_filename()
        if tuple:
            tool = tuple[0]
            filename = tuple[1]
            tool_filename_dict[tool] = filename

    return tool_filename_dict

if __name__ == "__main__":
    infile = open(sys.argv[1], "r")
    tool_filename_dict = get_tool_filename_dict(infile)
    infile.seek(0) # Reset for next function
    new_infile = concat_same_datetime(infile)
    # Now we have a 'new' infile where each line is a concatenation of:
    # 1.) one line starting with a datetime, and
    # 2.) subsequent lines up to a line which has a new datetime 
    # We do further processing on this new infile
    re_cap = RegexCapture()
    for line in new_infile:
        line = line.strip()
        re_cap.set_line(line)
        if re_cap.is_input_line():
            print(line)
            filename = tool_filename_dict[re_cap.get_toolname()]
            toolname = re_cap.get_toolname()
            input = re_cap.get_input()
            # print(filename, toolname, input)
        
    