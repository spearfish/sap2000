import sys, getopt
from inout import io

def run(input = "", output = ""):
  # use default output file if none or empty given
  if output != "":
    return io(input, output)
  else:
    return io(input)

if __name__ == "__main__":
  argv = sys.argv[1:]
  program = sys.argv[0]
  hide = False
  usage = "Correct usage is {} -i <inputfile> -o <outputfile> [--hidden]"

  # try to obtain commandline arguments for file specified
  try:
    opts, args = getopt.getopt(argv,"hi:o",["ifile=","ofile=","hidden"])
  except getopt.Getopt.Error:
    print (usage.format(program))
    sys.exit(2)

  # parse arguments
  inputfile = ""
  outputfile = ""
  for opt, arg in opts:
    if opt == '-h':
      print (usage.format(program))
      sys.exit()
    elif opt in ("--hidden"):
      hide = True
    elif opt in ("-i", "--ifile"):
      inputfile = arg
    elif opt in ("-o", "--ofile"):
      outputfile = arg

  model, program = run(inputfile,outputfile)

  # The program is hidden by default. Here it is
  # shown if the --hidden flag is not passed
  if hide:
    program.hide()
