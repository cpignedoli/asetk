#!/usr/bin/env python
import numpy as np
import argparse
import os.path
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from atk.format.cube import Cube
import sys

def resample(plane, cube, nsamples=1000):
    """Resamples data in cartesian coordinates.

    Assumptions:
    - data.shape == [self.data.shape[i] for i in axes]
    """
    nx,ny,nz    = cube.data.shape
    dx,dy,dz    = cube.atoms.cell / cube.data.shape

    plane = plane.flatten()
    pos   = [ i*dx+j*dy for i in range(nx) for j in range(ny) ]
    x,y,z = zip(*pos)

    extent = (np.min(x),np.max(x),np.min(y),np.max(y))
    xnew = np.linspace(extent[0], extent[1], nsamples)
    ynew = np.linspace(extent[2], extent[3], nsamples)

    resampled = mlab.griddata(x, y , plane, xnew, ynew)
    # for some reason, I need to revert the x axis for imshow
    resampled = resampled[::-1,:]

    return [resampled, extent]

# Define command line parser
parser = argparse.ArgumentParser(
    description='Performs Scanning Tunneling Microscopy Simulation.')
parser.add_argument('--version', action='version', version='%(prog)s 23.12.2013')
parser.add_argument(
    '--stmcubes',
    nargs='+',
    metavar='',
    help='Cube files containing the local density of states (s-wave tip)\
          or the appropriate matrix elements (general case).')
parser.add_argument(
    '--heights',
    nargs='+',
    metavar='heights',
    type=float,
    help='Tip-height above the topmost atom for an STM-image in constant-z\
          mode. 3-4 Angstroms is typically reasonable.')
parser.add_argument(
    '--isovalues',
    nargs='+',
    metavar='isovalues',
    type=float,
    help='Value of the isosurface for an STM-image in constant current mode.\
          1e-7 is typically a good start.')
parser.add_argument(
    '--zmin',
    metavar='zmin [Angstroms]',
    type=float,
    default=0.0,
    help='Minimum z-height for the tip inr constant-current mode.')
parser.add_argument(
    '--plot',
    default=False,
    type=bool,
    help='Whether to plot the resulting isosurface using matplotlib.')
parser.add_argument(
    '--plotrange',
    metavar='plotrange [Angstroms]',
    default=None,
    type=float,
    help='Limiting color-range for plot of constant-current STM')

args = parser.parse_args()

# Make list of jobs
jobs = []
if args.heights:
    jobs +=  zip(args.heights, ['h' for _i in range(len(args.heights))])
if args.isovalues:
    jobs += zip(args.isovalues, ['i' for _i in range(len(args.isovalues))])
if not jobs:
    print("No isovalues/heights specified. Exiting...")
    sys.exit()    

# Iterate over supplied cube files
for fname in args.stmcubes:
    print("\nReading {n} ".format(n=fname))
    c = Cube.from_file(fname, read_data=True)

    for v,kind in jobs:
        planefile = None
        header = "STM simulation based on " + fname
        if kind == 'h':
            planefile = "{f}.dz{d}".format(f=fname,d=v)
            header += ", z = {v} [A]".format(v=v)
        elif kind == 'i':
            planefile = "{f}.iso{d}".format(f=fname,d=v)
            header += ", isovalue {v}, zmin {z} [A]".format(v=v, z=args.zmin)
         
        plane = None
        if kind == 'h':
            plane = c.get_plane_above_atoms(v)
        elif kind == 'i':
            plane = c.get_isosurface_above_atoms(v, zmin=args.zmin)

        print("\nWriting {} ".format(planefile))
        np.savetxt(planefile, plane, header=header)

        if args.plot:
            plotfile = planefile + str('.png')
            print("Plotting into {} ".format(plotfile))
            fig = plt.figure()

            vmin = None
            if kind == 'i' and args.plotrange:
                vmin = np.max(plane) - args.plotrange
                plane = plane - vmin
                vmin = 0

            plane, extent = resample(plane, c)
            cax = plt.imshow(plane, extent=extent, cmap='gray', vmin=vmin)
            plt.xlabel('x [$\AA$]')
            plt.ylabel('y [$\AA$]')

            if kind == 'h':
                cbar = fig.colorbar(cax, format='%.1e')
                cbar.set_label('$|\psi|^2$ $[e/a_0^2]$')
            elif kind == 'i':
                cbar = fig.colorbar(cax, format='%.2f')
                cbar.set_label('z [$\AA$]')

            plt.savefig(plotfile, dpi=200)


