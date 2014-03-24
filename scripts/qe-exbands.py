#!/usr/bin/env python
# Reads energy levels from qe output and plots (1d) band structure
# to file "bands.png"

import atk.format.qe as qe
from sys import argv
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pylab as plt
import argparse

# Define command line parser
parser = argparse.ArgumentParser(
    description='Extract and plot (1d) band structure from QE')
parser.add_argument('--version', action='version', version='%(prog)s 24.03.2014')
parser.add_argument(
    'prefix',
    metavar='STRING', 
    help='Prefix of .save directory to be read.')
parser.add_argument(
    '--plot',
    metavar='BOOL', 
    default=True,
    help='Whether to plot bands to bands.png.')
parser.add_argument(
    '--window',
    metavar='ENERGY',
    default=3,
    help='Plot range [-window,window] around Fermi.')

args = parser.parse_args()

prefix = args.prefix

spectrum = qe.Spectrum.from_save(args.prefix)
dispersion = spectrum.dispersions[0]

data = None
k    = None
for i in range(len(dispersion.kpoints)):
    kpt = dispersion.kpoints[i]
    E = kpt.energies
    fermi = kpt.fermi


    #k = np.array([ dispersion.kvectors[i][0] for l_ in range(len(E))])
    # QE likes to place kpoints at -0.5 instead of +0.5
    #k = [ kp if kp >= 0 else kp+1 for kp in k]
    if k is None:
        k = [0 for l_ in range(len(E))]
    else:
        d = np.linalg.norm(dispersion.kvectors[i] - dispersion.kvectors[i-1])
        k += np.array([ d for l_ in range(len(E)) ] )

    #k *= np.pi
    E -= fermi
    fermi = 0

    plt.plot(k,E, 'ko')
    window = [fermi -args.window, fermi+ args.window]
    plt.ylim(window)
    #plt.xlabel(r'k [$\frac{1}{\AA}$]')
    plt.xlabel(r'k [$\frac{2\pi}{a}$]')
    plt.ylabel('E [eV]')

    datablock = [ np.concatenate( (dispersion.kvectors[i], [e]) ) for e in E]
    if data is not None:
        data = np.concatenate( (data, datablock), axis=0 )
    else:
        data = datablock

np.savetxt('bands.dat', data, header='#kx  ky  kz  E[eV]', fmt='%.4e %.4e %.4e %.6e')
    
#plt.show()

plt.savefig('bands.png', transparent=True, dpi=150)

