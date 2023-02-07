import json
import os
import sys
import re

from argparse import ArgumentParser
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
        self.datetime = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\])"
        )
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
    aggr_line = []  # Aggregated line based on one datetime
    for line in infile.readlines():
        line = line.strip()
        re_cap.set_line(line)

        if not aggr_line:
            aggr_line.append(line)
        else:
            if re_cap.has_datetime():
                new_line = " ".join(aggr_line)
                new_infile.append(new_line)
                aggr_line = [line]
            else:
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


parser = ArgumentParser(
    description="A versatile WFE log parser. Currently support: CWL"
)
parser.add_argument("cwl_log", help="Source CWL log file")
parser.add_argument(
    "--generate_yaml",
    nargs="+",
    help="""\ Generate YAML input for a given <step_name>. The step name must
exist within the log. \nUsage: --generate_yaml <step_name>, \ne.g.:
--generate_yaml fastqc",
""",
)
parser.set_defaults(unit_test=False)
args = parser.parse_args()

if __name__ == "__main__":
    infile = open(sys.argv[1], "r")
    tool_filename_dict = get_tool_filename_dict(infile)
    infile.seek(0)  # Reset for next function
    new_infile = concat_same_datetime(infile)

    # Now we have a 'new' infile where each line is a concatenation of: 1.) one
    # line starting with a datetime, and 2.) subsequent lines up to a line which
    # has a new datetime We do further processing on this new infile
    re_cap = RegexCapture()
    count_input = 0
    file_inputs = {}
    for line in new_infile:
        line = line.strip()
        re_cap.set_line(line)
        # We process as follow. For now we are only interested in processing an
        # input line. If it is, we separate the list of inputs based on their
        # filename. We create a dictionary where the filename is key, and their
        # dict of inputs is val.
        if re_cap.is_input_line():
            # First extract the dict of inputs
            input = re_cap.get_input()
            # Then get the filename using the dict we constructed beforehand.
            filename = tool_filename_dict[re_cap.get_toolname()]

            file_inputs[filename] = input

    #  Here we add further processing based on given arguments.
    if args.generate_yaml:
        step_names = args.generate_yaml
        for step in step_names:
            out_yaml = open("{}/{}.yaml".format(
                    os.path.dirname(os.path.abspath(__file__)), step), 
                "w")
            inputs = file_inputs[step]

            # Now we extract the inputs of each file. For a YAML input, we might
            # give a separator if the value is not nested, e.g. key1:  val1
            # However, we consider the case where value is nested, such as a
            # file:
            # key1:
            #   class: File
            #   path: <path_to_file>
            # Here we must ensure that the colon after key1 does not have
            # separator, yet the ones, after class and path should have one.
            #
            # We also consider the case where value is list of nested values.
            # For this case we process each element like we process one nested
            # value, appending '-' for each element. But we will do this once
            # there is a workflow input which require such feature.
            separator = None
            for inp_name, inp_val in inputs.items():
                yaml_val = None
                # Case of value is nested
                if type(inp_val) is dict:
                    print(json.dumps(inp_val, indent=4))
                    if "class" in inp_val:
                        if inp_val['class'] == "File":
                            yaml_val = "\n    class: {}\n    path: /{}".format(
                                "File", inp_val["location"].lstrip("file://")
                            )
                        else:
                            assert(inp_val['class'] == "Directory")
                            yaml_val = "\n    class: {}\n    path: /{}".format(
                                "Directory", inp_val["location"].lstrip("file://")
                            )
                    separator = ""
                # Case of value is list of nested. We treat it the same as
                # one nested value for now.
                elif type(inp_val) is list:
                    elem_arr = []
                    for elem in inp_val:
                        if "class" in elem:
                            assert elem["class"] == "File"
                            elem_val = "\n  - class: {}\n    path: /{}".format(
                                "File", elem["location"].lstrip("file://")
                            )
                        separator = ""
                        elem_arr.append(elem_val)
                    yaml_val = "".join(elem_arr)
                else:
                    # There are four cases for the type of inp_val here,
                    # namely None, string, int, and bool. We deal accordingly.
                    if inp_val is None:
                        yaml_val = "null"
                    elif type(inp_val) is int:
                        yaml_val = inp_val
                    elif type(inp_val) is bool:
                        yaml_val = str(inp_val).lower()
                    else:
                        assert type(inp_val) is str
                        yaml_val = '"{}"'.format(inp_val)
                    separator = " "
                out_yaml.write("{}:{}{}\n".format(inp_name, separator, yaml_val))
            out_yaml.close()
