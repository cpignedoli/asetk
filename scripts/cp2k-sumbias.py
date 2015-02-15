#!/usr/bin/env python
from __future__ import division
import numpy as np
import argparse

import asetk.format.cp2k as cp2k
import asetk.util.progressbar as progressbar
import os

# Define command line parser
parser = argparse.ArgumentParser(
    description='Sums required wave functions for STM simulation \
                 from Gaussian Cube file.')
parser.add_argument('--version', action='version', version='%(prog)s 15.02.2015')
parser.add_argument(
    '--cubes',
    nargs='+',
    metavar='FILENAME',
    required=True,
    help='Cube files containing the Kohn-Sham wave functions.')
parser.add_argument(
    '--levelsfile',
    metavar='FILENAME',
    required=True,
    help='File containing the energy levels. Can be either CP2K output\
          or .MOLog file.')
parser.add_argument(
    '--vfile',
    metavar='FILENAME',
    help='Provide a file containing a list of voltages (one per line) \
          for which to perform STM simulation.\
          For regular grid, see vmin, vmax, vstep.')
parser.add_argument(
    '--vmin',
    type=float,
    metavar='U',
    help='Define voltage grid of spacing vstep from vmin to vmax.')
parser.add_argument(
    '--vmax',
    type=float,
    metavar='U',
    help='Define voltage grid of spacing vstep from vmin to vmax.')
parser.add_argument(
    '--vstep',
    type=float,
    metavar='U',
    help='Define voltage grid of spacing vstep from vmin to vmax.')
parser.add_argument(
    '--psi_squared',
    dest='psi_squared',
    action='store_true',
    default=False,
    help='Use if cube files contain square of the wave function.')

args = parser.parse_args()

# Get list of bias voltages
if args.vfile is not None:
    bias = np.genfromtxt(args.vfile, dtype=float).T
elif (args.vmin is not None) and \
     (args.vmax is not None) and \
     (args.vstep is not None):
    bias = np.arange(args.vmin, args.vmax, args.vstep)
else:
    raise ValueError("Please specify either --bias or --vmin, --vmax and --vstep")
print("Performing summation for voltages {}".format(bias))
bias = np.unique(bias)
pos_bias = np.sort(bias[np.where(bias > 0)])
neg_bias = np.sort(bias[np.where(bias <= 0)])[::-1]

# Read energy levels
lfname, lfext = os.path.splitext(args.levelsfile)
if lfext == '.MOLog':
    spectrum = cp2k.Spectrum.from_mo(args.levelsfile)
else:
    spectrum = cp2k.Spectrum.from_output(args.levelsfile)
print("Read spectrum from {f}".format(f=args.levelsfile))
print(spectrum)

# Reading headers of cube files
cubes = []
print("\nReading headers of {} cube files".format(len(args.cubes)))
bar = progressbar.ProgressBar(niter=len(args.cubes))

for fname in args.cubes:
    cubes.append( cp2k.WfnCube.from_file(fname) )
    bar.iterate()
print("\n")

# Perform summation
for vlist in [pos_bias, neg_bias]:
    # Prepare new cube file
    sumcube = cp2k.WfnCube.from_file(cubes[0].filename, read_data=True)
    sumcube.title = "STM cube"
    for v in vlist:
        print("{:+7.3f} V \n-----------------------------------".format(v))
        sumcube.comment = "Sample bias {:+4.2f} V\n".format(v)
        sumcube.filename = "stm_{:+4.2f}V.cube".format(v)

        n_to_sum = 0
        for spin, levels in zip(spectrum.spins, spectrum.energylevels):
            for index, l in enumerate(levels.levels):
                e = l.energy
                o = l.occupation

                # If we need this level
                if e*v >= 0 and e*v < v**2:
                    n_to_sum += 1
                    # find cube file
                    found = False
                    for c in cubes:
                        if c.wfn == index+1 and c.spin == spin+1:
                            found = True
                            print("Found cube file for spin {s}, energy {e:.6f} eV, occupation {o}"\
                                  .format(s=spin+1,e=e, o=o))

                            # Make local copy of cube file and then read
                            tmp = cp2k.WfnCube.from_cube(c)
                            cubes.remove(c)

                            tmp.read_cube_file(tmp.filename,read_data=True)
                            if(not args.psi_squared):
                                tmp.data = np.square(tmp.data)
                            # For STM at zero temperature, 
                            # the occupation of the level in the calculation is irrelevant
                            # tmp *= o
                            sumcube += tmp
                            break

                    if not found:
                        print("Missing cube file for spin {s}, energy {e:.6f} eV, occupation {o}"\
                               .format(s=spin+1,e=e,o=o))
            if n_to_sum == 0:
                print("No new cubes for bias {}".format(v))
            # When all required levels have been added, write sum            
        print("Writing {}".format(sumcube.filename))
        sumcube.write_cube_file()
        print("")


