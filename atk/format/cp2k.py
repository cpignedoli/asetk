"""Classes for use with CP2K

Representation of a spectrum
"""

import re
import copy  as cp
import numpy as np
import StringIO
import atk.atomistic.fundamental as fu
import atk.atomistic.constants as atc
import cube

class Spectrum(object):

    """An collection of energy levels, grouped by spin"""

    def __init__(self, energylevels=None, spins=None):
        """Set up spectrum from a list of EnergyLevels."""
        self.energylevels = energylevels
        self.spins = spins

    @classmethod
    def from_mo(cls, fname):
        """Creates Spectrum from list of molecular occupations"""
        tmp = Spectrum()
        tmp.read_from_mo(fname)
        return tmp

    @classmethod
    def from_output(cls, fname):
        """Creates Spectrum from CP2K output"""
        tmp = Spectrum()
        tmp.read_from_output(fname)
        return tmp

    @property
    def energies(self):
        """Returns list of energy levels of all spins."""
        list = [el.energies for el in self.energylevels]
        return np.concatenate(list)

    @property
    def occupations(self):
        """Returns list of level occupations of all spins."""
        os = np.array([])
        for el in self.energylevels:
            os = np.concatenate( (os, el.occupations))
        return os

    @property
    def fermi(self):
        """Returns Fermi energy."""
        fermis = [el.fermi for el in self.energylevels]

        fermi = np.unique(fermis)

        if len( np.unique(fermis) ) != 1:
            print "There are Fermi energies {}".format(fermis)
            print "Using the mean {}".format(np.mean(fermis))

        return np.mean(fermis)

    def copy(self, spectrum):
        """Performs deep copy of spectrum."""
        self.energylevels = [ el.copy() for el in spectrum.energylevels ]
        self.spins = cp.copy(spectrum.spins)

    def shift(self, de):
        for levels in self.energylevels:
            levels.shift(de)

    def __str__(self):
        text  = "Spectrum containing {} spins\n".format(len(self.energylevels))
        for i in range(len(self.energylevels)):
            e = self.energylevels[i]
            s = self.spins[i]
            text += 'spin {} : {}\n'.format(s+1, e.__str__())
        return text

    def __getitem__(self, index):
        return self.levels[index]

    def read_from_mo(self, fname):
        """Reads Spectrum from list of molecular occupations"""
        s = open(fname, 'r').read()

        lineregex='[^\r\n]*\r?\n'
        fermiregex='.*?Fermi energy:(\s*[\-\d\.]+)'
        matches=re.findall(
                'EIGENVALUES({l}){l}{l}([\-\.\s\d]*){f}' \
                    .format(l=lineregex, f=fermiregex), 
                s, re.DOTALL)

        self.spins=[]
        self.energylevels=[]
        spin=0
        for match in matches:
            # we take only the last ones, which do not contain 'SCF'
            if not re.search('SCF', match[0]):
                data = np.genfromtxt(StringIO.StringIO(match[1]),
                             dtype=[int,float,float])
                i,E,occ = zip(*data)
                fermi = float(match[2]) * atc.Ha / atc.eV
                E     = np.array(E)     * atc.Ha / atc.eV

                levels = fu.EnergyLevels(energies=E,occupations=occ, fermi=fermi)
                self.energylevels.append(levels)
                self.spins.append(spin)

                spin = spin + 1

    def read_from_output(self, fname):
        """Reads Spectrum from CP2K output"""

        # TO IMPLEMENT (may copy from old cp2k module)

    def dos(self, sigma = 0.05, deltaE = 0.005, nsigma = 10):
        """
        Returns numpy array [energy, density of states]

        Parameters
        ----------
        sigma :  Width of Gaussian broadening [eV]
        deltaE :  spacing of energy grid [eV]
        nsigma : Gaussian distribution is cut off after nsigma*sigma
        """

        if sigma/deltaE < 10:
            print "Warning: sigma/deltaE < 10. Gaussians might not be sampled well."
        gaussian = lambda x: 1/(np.sqrt(2*np.pi)*sigma) \
                             * np.exp(-x**2/(2*sigma**2))

        # Tabulate the Gaussian in range sigma * nsigma
        limit = sigma * nsigma
        energies = np.r_[-limit:limit:deltaE]
        gprofile = gaussian(energies)

        # Encoding the discretized energy in the array index i makes the code much faster.
        energies = self.energies
        loE=energies[0] - nsigma * sigma
        hiE=energies[-1] + nsigma * sigma
        E=np.r_[loE:hiE:deltaE]

        # Create dos of delta-peaks to be folded with Gaussian
        DOSdelta = np.array([0.0 for j in E])
        for e in energies:
            # In order to be able to fold with tabulated Gaussian, we have to place
            # levels *on* the grid. I.e. level spacing cannot be smaller than deltaE.
            n = int((e-loE)/deltaE)
            # Note: DOS should be calculated for unoccupied levels as well!
            #if o is not None:
            #    DOSdelta[n] += o
            #else:
            DOSdelta[n] += 1
        # Convolve with gaussian, keeping same dimension
        # Can be made even faster by using fftconvolve
        DOS = np.convolve(DOSdelta,gprofile, mode='same')
 
        return np.array([E,DOS])
        

class WfnCube(cube.Cube):
    """Gaussian cube file written by CP2K

    CP2K writes the index of level and spin into the
    comment line of the cube file
    """

    def __init__(self, title=None, comment=None, origin=None, atoms=None, 
                 data=None, spin=None, wfn=None, energy=None, occupation=None):
        """Standard constructor, all parameters default to None.
        
        energy and occupation are not stored in the cube file,
        but can be assigned by linking the cube file with the 
        output from the calculation.
        """
        super(WfnCube, self).__init__(title,comment,origin,atoms,data)
        self.spin = spin
        self.wfn  = wfn
        self.energy = energy
        self.occupation = occupation

    @classmethod
    def from_file(cls, fname, read_data=False):
        """Creates Cube from cube file"""
        tmp = WfnCube()
        tmp.read_cube_file(fname, read_data=read_data)
        return tmp

    def read_cube_file(self, fname, read_data=False, v=1):
            """Reads header and/or data of cube file"""
            super(WfnCube, self).read_cube_file(fname, read_data, v)

            # CP2K stores information on the level/spin index
            # in the comment line
            commentregex = 'WAVEFUNCTION\s+(\d+)\s+spin\s+(\d+)'
            match = re.search(commentregex, self.comment)
            self.wfn = int(match.group(1))
            self.spin = int(match.group(2))


