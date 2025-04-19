import argparse

# Adds arguments of the packager to given argparse.ArgumentParser()
def packager_arguments(arg_parser):
    optgroup = arg_parser.add_argument_group('optional arguments for the optimization algorithm')
    optgroup.add_argument('-a', '--algorithm',
                          action='store',
                          type=str.lower,
                          metavar='str',
                          help="optimization algorithm, LAHC (late acceptance hill climbing), DLAS (diversified late acceptance search) or ANNEAL (simulated annealing). Default: %(default)s",
                          required=False,
                          choices=["lahc", "dlas", "anneal"],
                          default="dlas")
    optgroup.add_argument('-s', '--steps', type=int, default=10000, metavar='int',
                          help='number of steps in the optimization algorithm. 0 = iterate forever (intermediate results saved). default: %(default)d')
    optgroup.add_argument('-q', '--queue-length', type=_check_positive, default=12, metavar='int',
                          help='number of parallel jobs in queue. to use all CPUs, this should be >= number of logical processors. too long queue slows down convergence. default: %(default)d')
    optgroup.add_argument('-P', '--processes', type=_check_positive, default=None, metavar='int',
                          help='number of parallel processes. 1 = no parallel processing. defaults to number of available logical processors.')
    optgroup.add_argument('-H', '--lahc-history', type=int, default=500, metavar='int',
                          help='history length in late acceptance hill climbing. default: %(default)d')
    optgroup.add_argument('-D', '--dlas-history', type=int, default=5, metavar='int',
                          help='history length in diversified late acceptance search. default: %(default)d')
    optgroup.add_argument('-m', '--margin', type=float, default=0, metavar='float',
                          help='initialize the lahc/dlas history with initial_cost + margin (in bytes). Default: %(default).0f')
    optgroup.add_argument('-t', '--start-temp', type=float, default=1, metavar='float',
                          help='starting temperature for simulated annealing, >0. default: %(default).1f')
    optgroup.add_argument('-T', '--end-temp', type=float, default=0.1, metavar='float',
                          help='ending temperature for simulated annealing, >0. default: %(default).1f')
    optgroup.add_argument('--target-size', type=int, default=0, metavar='int',
                          help='stop compression when target size is reached. default: %(default)d')
    optgroup.add_argument('--exact', action='store_const', const=True,
                          help='used with --target-size to indicate that the size should be reached exactly')
    optgroup.add_argument('--seed', type=int, default=0, metavar='int',
                          help='random seed. default: %(default)d')

def _check_positive(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue
