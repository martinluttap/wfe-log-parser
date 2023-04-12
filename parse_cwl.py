import json
import os
import sys
import re

from argparse import ArgumentParser
from datetime import datetime as dt


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
parser.add_argument(
    "--print_exec_tree",
    default=False,
    action="store_true",
    help="""\ Print a list of executed steps. \nUsage: --print_exec_tree",
""",
)
parser.add_argument(
    "--print_step_filename",
    default=False,
    action="store_true",
    help="""\ Print a list of step and its executed CWL file name. \nUsage: --print_step_filename",
""",
)
parser.add_argument(
    "--print_input_map",
    default=False,
    action="store_true",
    help="""\ Print a JSON of input as seen in the given log. 
    \nUsage: --print_input_map",
""",
)
parser.add_argument(
    "--print_output_map",
    default=False,
    action="store_true",
    help="""\ Print a JSON of output as seen in the given log. 
    \nUsage: --print_output_map",
""",
)
parser.set_defaults(unit_test=False)
args = parser.parse_args()

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
        self.step_input_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) DEBUG (\[job ([^\s]+)]) (\{.*\})"
        )
        self.wf_input_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) DEBUG (\[workflow ([^\s]+)]) inputs (\{.*\})"
        )
        self.step_output_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) DEBUG (\[.* ([^\s]+)]) outputs (\{.*\})"
        )
        self.filename = re.compile(r"\/[^s].*\/([^s].*).cwl")
        self.datetime = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\])"
        )
        self.info_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) (INFO) (\[([^\s]+) ([^\s]*)]) (start|starting|completed)+.*"
        )
        self.debug_line = re.compile(
            r"(\[(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\]) (DEBUG) (\[([^\s]+) ([^\s]*)]) (initializing|initialized) from file\:\/\/([^\s]+)+.*"
        )

        self.line = line

    def set_line(self, new_line):
        self.line = new_line

    def is_filename_line(self) -> bool:
        return self.filename_line.match(self.line)

    def is_step_input_line(self) -> bool:
        return self.step_input_line.match(self.line)

    def is_step_output_line(self) -> bool:
        return self.step_output_line.match(self.line)

    def is_wf_input_line(self) -> bool:
        return self.wf_input_line.match(self.line)

    def is_tool_line(self) -> bool:
        return self.tool_line.match(self.line)

    def is_info_line(self) -> bool:
        return self.info_line.match(self.line)

    def is_debug_line(self) -> bool:
        return self.debug_line.match(self.line)

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

    def get_workflowname(self):
        match = self.is_wf_input_line()
        if match:
            return match.groups()[8]
        else:
            return None

    def get_step_input(self):
        match = self.is_step_input_line()
        if match:
            input_json = json.loads(match.group(10))
            return input_json
        else:
            return None
        
    def get_wf_input(self):
        match = self.is_wf_input_line()
        if match:
            input_json = json.loads(match.group(10))
            return input_json
        else:
            return None
        
    def get_step_output(self):
        match = self.is_step_output_line()
        if match:
            name, output_json = match.group(9), json.loads(match.group(10))
            return name, output_json
        else:
            return None


    def get_exec_info(self):
        match = self.is_info_line()
        if match:
            return match.groups()
        else:
            return None
        
    def get_file_info(self):
        match = self.is_debug_line()
        if match:
            return match.groups()[-3], ''.join(match.groups()[-1].split('#')[:-1])
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

class LogParser:
    def __init__(self, log_path: str) -> None:

        self.step_inputs = {}
        self.wf_inputs = {}
        self.wf_outputs = {}
        self.exec_tree = []
        self.wf_cwl_file = {}

        infile = open(log_path, "r")
        tool_filename_dict = self.get_tool_filename_dict(infile)
        infile.seek(0)  # Reset for next function
        new_infile = self.concat_same_datetime(infile)

        # Now we have a 'new' infile where each line is a concatenation of: 1.) one
        # line starting with a datetime, and 2.) subsequent lines up to a line which
        # has a new datetime We do further processing on this new infile
        re_cap = RegexCapture()
        for line in new_infile:
            line = line.strip()
            re_cap.set_line(line)
            # Capture the inputs for step
            if re_cap.is_step_input_line():
                # First extract the dict of inputs
                input = re_cap.get_step_input()
                # Then get the filename using the dict we constructed beforehand.
                filename = tool_filename_dict[re_cap.get_toolname()]

                self.step_inputs[filename] = input
                # print(line)

            # Capture the inputs for workflow.
            # Similar logic with input extraction for step
            if re_cap.is_wf_input_line():
                input = re_cap.get_wf_input()
                filename = re_cap.get_workflowname()
                self.wf_inputs[filename] = input

            # Here we also capture the INFO lines and extract information 
            # regarding execution tree.   
            if re_cap.is_info_line():
                self.exec_tree.append(re_cap.get_exec_info())

            # Capture the DEBUG lines to get information about source file 
            if re_cap.is_debug_line():
                step, cwl_file = re_cap.get_file_info() 
                self.wf_cwl_file[step] = cwl_file

            if re_cap.is_step_output_line():
                name, output = re_cap.get_step_output()
                self.wf_outputs[str.upper(name)] = output

    def concat_same_datetime(self, infile):
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


    def get_tool_filename_dict(self, infile):
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

    def handle_yaml_unary_type(self, inp_val):
        yaml_val = None
        # There are five cases for the type of inp_val here,
        # namely None, string, int, float, and bool. We deal accordingly.
        if inp_val is None:
            yaml_val = "null"
        elif type(inp_val) is int:
            yaml_val = inp_val
        elif type(inp_val) is float:
            yaml_val = inp_val
        elif type(inp_val) is bool:
            yaml_val = str(inp_val).lower()
        else:
            assert type(inp_val) is str
            yaml_val = '"{}"'.format(inp_val)

        return yaml_val

    def handle_yaml_dict_type(self, inp_key, inp_val, pad_num: int = 4):
        assert(type(inp_val) is dict)
        ret_string = ""
        padding = ' ' * pad_num
        if "class" in inp_val:
            if inp_val['class'] == "File":
                elem_val = "\n{}class: {}\n{}path: /{}".format(
                    padding, "File", padding, inp_val["location"].lstrip("file://")
                )
            else:
                assert(inp_val['class'] == "Directory")
                elem_val = "\n{}class: {}\n{}path: /{}".format(
                    padding, "Directory", padding, inp_val["location"].lstrip("file://")
                )
            ret_string += "{}".format(elem_val)
        else:
            for k, v in inp_val.items():
                if type(v) is dict:
                    handled_k_v = self.handle_yaml_dict_type(k, v, pad_num + 4)
                    ret_string += "\n{}{}:{}".format(padding, k, handled_k_v)
                else:
                    ret_string += "\n{}{}: {}".format(padding, k, self.handle_yaml_unary_type(v))

        return ret_string

    def print_input_map(self):
        print(json.dumps(self.step_inputs, indent=4))

    def print_output_map(self):
        print(json.dumps(self.wf_outputs, indent=4))

    def print_exec_tree(self):
        exec_stack = []
        for exec_group in self.exec_tree:
            step_type = exec_group[9]
            step_name = exec_group[10]
            state = exec_group[11]
            if step_name == '':
                step_name = 'main'
            if (state == 'start'and (step_name not in exec_stack)):
                exec_stack.append(step_name) 
                tabs = "\t" * (len(exec_stack) - 1)
                # print("{: <32} {}".format(step, cwl_file))
                print("{}{: <32} {}".format(
                    tabs,
                    step_name, self.wf_cwl_file[step_name] if step_name in self.wf_cwl_file else ''))
                assert(exec_stack[0] == 'main')
            if (state == 'completed' or state == 'finished'):
                if (exec_stack[-1] == step_name):
                    exec_stack.pop()

    def print_step_filename(self):
        for step, cwl_file in self.wf_cwl_file.items():
            print("{: <32} {}".format(step, cwl_file))

    def generate_yaml(self, args):
        step_names = args.generate_yaml
        print(log_parser.step_inputs)
        for step in step_names:
            out_yaml = open("{}/{}.yaml".format(
                    os.path.dirname(os.path.abspath(__file__)), step), 
                "w")
            inputs = log_parser.step_inputs[step]

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
            print(json.dumps(inputs, indent=4))
            separator = None
            for inp_name, inp_val in inputs.items():
                yaml_val = None
                unary_types = {str, int, bool, float}
                # Case of value is nested
                if type(inp_val) is dict:
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
                    else:
                        yaml_val = log_parser.handle_yaml_dict_type(inp_name, inp_val)
                    separator = ""
                # Case of value is list of nested. 
                elif type(inp_val) is list:
                    elem_arr = []
                    for elem in inp_val:
                        if "class" in elem:
                            assert elem["class"] == "File"
                            elem_val = "\n  - class: {}\n    path: /{}".format(
                                "File", elem["location"].lstrip("file://")
                            )
                        else:
                            # So far we have seen either a list of unary types
                            # (str, int, float) or dict elements. If it is the
                            # former, we can just use the list element as is. 
                            # Else we should process the element further.
                            processed_elem = None
                            if type(elem) in unary_types:
                                processed_elem = elem
                            else:
                                processed_elem = log_parser.handle_yaml_dict_type(inp_name, elem)
                            elem_val = "\n  - {}".format(
                                processed_elem.lstrip() # This is too hacky. Need to fix
                            ) 
                        elem_arr.append(elem_val)
                    separator = ""
                    yaml_val = "".join(elem_arr)
                else:
                    assert(inp_val is None or type(inp_val) in unary_types)
                    yaml_val = log_parser.handle_yaml_unary_type(inp_val)
                    separator = " "
                out_yaml.write("{}:{}{}\n".format(inp_name, separator, yaml_val))
            out_yaml.close()

if __name__ == "__main__":

    log_path = sys.argv[1]
    log_parser = LogParser(log_path)

    #  Here we add further processing based on given arguments.
    if args.print_input_map:
        log_parser.print_input_map()
    if args.print_output_map:
        log_parser.print_output_map()
    if args.print_exec_tree:
        log_parser.print_exec_tree()
    if args.print_step_filename:
        log_parser.print_step_filename()
    if args.generate_yaml:
        log_parser.generate_yaml(args)
        print(json.dumps(log_parser.step_inputs, indent=4))
