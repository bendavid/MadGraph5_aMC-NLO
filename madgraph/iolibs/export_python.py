################################################################################
#
# Copyright (c) 2009 The MadGraph Development team and Contributors
#
# This file is a part of the MadGraph 5 project, an application which 
# automatically generates Feynman diagrams and matrix elements for arbitrary
# high-energy processes in the Standard Model and beyond.
#
# It is subject to the MadGraph license which should accompany this 
# distribution.
#
# For more information, please visit: http://madgraph.phys.ucl.ac.be
#
################################################################################

"""Methods and classes to export matrix elements to Python format."""

import fractions
import glob
import itertools
import logging
import os
import re
import shutil
import subprocess

import madgraph.core.color_algebra as color
import madgraph.core.helas_objects as helas_objects
import madgraph.iolibs.drawing_eps as draw
import madgraph.iolibs.files as files
import madgraph.iolibs.helas_call_writers as helas_call_writers
import madgraph.iolibs.misc as misc
import madgraph.iolibs.file_writers as writers
import madgraph.iolibs.template_files as Template
import madgraph.iolibs.ufo_expression_parsers as parsers
from madgraph import MadGraph5Error, MG5DIR

import aloha.create_aloha as create_aloha
import aloha.aloha_writers as aloha_writers

_file_path = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0] + '/'
logger = logging.getLogger('madgraph.export_python')


#===============================================================================
# ProcessExporterPython
#===============================================================================
class ProcessExporterPython(object):
    """Class to take care of exporting a set of matrix elements to
    Python format."""

    class ProcessExporterPythonError(Exception):
        pass
    
    def __init__(self, matrix_elements, python_helas_call_writer):
        """Initiate with matrix elements, helas call writer.
        Generate the process matrix element functions as strings."""

        if isinstance(matrix_elements, helas_objects.HelasMultiProcess):
            self.matrix_elements = matrix_elements.get('matrix_elements')
        elif isinstance(matrix_elements,
                        helas_objects.HelasMatrixElementList):
            self.matrix_elements = matrix_elements
        elif isinstance(matrix_elements,
                        helas_objects.HelasMatrixElement):
            self.matrix_elements = helas_objects.HelasMatrixElementList(\
                                                     [matrix_elements])
        if not self.matrix_elements:
            raise MadGraph5Error("No matrix elements to export")

        self.model = self.matrix_elements[0].get('processes')[0].get('model')

        self.helas_call_writer = python_helas_call_writer

        if not isinstance(self.helas_call_writer, helas_call_writers.PythonUFOHelasCallWriter):
            raise ProcessExporterPythonError, \
                "helas_call_writer not PythonUFOHelasCallWriter"

        self.matrix_methods = {}

    # Methods for generation of process file strings in Python

    #===========================================================================
    # write_python_process_cc_file
    #===========================================================================
    def get_python_matrix_methods(self, gauge_check=False):
        """Write the matrix element calculation method for the processes"""

        replace_dict = {}

        # Extract version number and date from VERSION file
        info_lines = self.get_mg5_info_lines()
        replace_dict['info_lines'] = info_lines

        for matrix_element in self.matrix_elements:
            process_string = matrix_element.get('processes')[0].shell_string()
            if process_string in self.matrix_methods:
                continue

            replace_dict['process_string'] = process_string

            # Extract number of external particles
            (nexternal, ninitial) = matrix_element.get_nexternal_ninitial()
            replace_dict['nexternal'] = nexternal

            # Extract ncomb
            ncomb = matrix_element.get_helicity_combinations()
            replace_dict['ncomb'] = ncomb

            # Extract helicity lines
            helicity_lines = self.get_helicity_matrix(matrix_element)
            replace_dict['helicity_lines'] = helicity_lines

            # Extract overall denominator
            # Averaging initial state color, spin, and identical FS particles
            den_factor_line = self.get_den_factor_line(matrix_element)
            replace_dict['den_factor_line'] = den_factor_line

            # Extract process info lines for all processes
            process_lines = self.get_process_info_lines(matrix_element)
            replace_dict['process_lines'] = process_lines
        
            # Extract ngraphs
            ngraphs = matrix_element.get_number_of_amplitudes()
            replace_dict['ngraphs'] = ngraphs

            # Extract nwavefuncs
            nwavefuncs = matrix_element.get_number_of_wavefunctions()
            replace_dict['nwavefuncs'] = nwavefuncs

            # Extract ncolor
            ncolor = max(1, len(matrix_element.get('color_basis')))
            replace_dict['ncolor'] = ncolor

            # Extract model parameter lines
            model_parameter_lines = \
                                 self.get_model_parameter_lines(matrix_element)
            replace_dict['model_parameters'] = model_parameter_lines

            # Extract color data lines
            color_matrix_lines = self.get_color_matrix_lines(matrix_element)
            replace_dict['color_matrix_lines'] = \
                                               "\n        ".join(color_matrix_lines)

            # Extract helas calls
            helas_calls = self.helas_call_writer.get_matrix_element_calls(\
                                                    matrix_element, gauge_check)
            replace_dict['helas_calls'] = "\n        ".join(helas_calls)

            # Extract JAMP lines
            jamp_lines = self.get_jamp_lines(matrix_element)
            replace_dict['jamp_lines'] = "\n        ".join(jamp_lines)

            method_file = open(os.path.join(_file_path, \
                       'iolibs/template_files/matrix_method_python.inc')).read()
            method_file = method_file % replace_dict

            self.matrix_methods[process_string] = method_file

        return self.matrix_methods

    def get_helicity_matrix(self, matrix_element):
        """Return the Helicity matrix definition lines for this matrix element"""

        helicity_line = "helicities = [ \\\n        "
        helicity_line_list = []

        for helicities in matrix_element.get_helicity_matrix():
            helicity_line_list.append("[" + ",".join(['%d'] * len(helicities)) % \
                                      tuple(helicities) + "]")
            
        return helicity_line + ",\n        ".join(helicity_line_list) + "]"


    def get_den_factor_line(self, matrix_element):
        """Return the denominator factor line for this matrix element"""

        return "denominator = %d" % \
               matrix_element.get_denominator_factor()

    def get_color_matrix_lines(self, matrix_element):
        """Return the color matrix definition lines for this matrix element. Split
        rows in chunks of size n."""

        if not matrix_element.get('color_matrix'):
            return ["denom = [1.]", "cf = [[1.]];"]
        else:
            color_denominators = matrix_element.get('color_matrix').\
                                                 get_line_denominators()
            denom_string = "denom = [%s];" % \
                           ",".join(["%i" % denom for denom in color_denominators])

            matrix_strings = []
            my_cs = color.ColorString()
            for index, denominator in enumerate(color_denominators):
                # Then write the numerators for the matrix elements
                num_list = matrix_element.get('color_matrix').\
                                            get_line_numerators(index, denominator)

                matrix_strings.append("%s" % \
                                     ",".join(["%d" % i for i in num_list]))
            matrix_string = "cf = [[" + \
                            "],\n        [".join(matrix_strings) + "]];"
            return [denom_string, matrix_string]

    def get_jamp_lines(self, matrix_element):
        """Return the jamp = sum(fermionfactor * amp[i]) lines"""

        res_list = []

        for i, coeff_list in enumerate(matrix_element.get_color_amplitudes()):

            res = "jamp[%d] = " % i

            # Optimization: if all contributions to that color basis element have
            # the same coefficient (up to a sign), put it in front
            list_fracs = [abs(coefficient[0][1]) for coefficient in coeff_list]
            common_factor = False
            diff_fracs = list(set(list_fracs))
            if len(diff_fracs) == 1 and abs(diff_fracs[0]) != 1:
                common_factor = True
                global_factor = diff_fracs[0]
                res = res + '%s(' % coeff(1, global_factor, False, 0)

            for (coefficient, amp_number) in coeff_list:
                if common_factor:
                    res = res + "%samp[%d]" % (coeff(coefficient[0],
                                               coefficient[1] / abs(coefficient[1]),
                                               coefficient[2],
                                               coefficient[3]),
                                               amp_number - 1)
                else:
                    res = res + "%samp[%d]" % (coeff(coefficient[0],
                                               coefficient[1],
                                               coefficient[2],
                                               coefficient[3]),
                                               amp_number - 1)

            if common_factor:
                res = res + ')'

            res_list.append(res)

        return res_list

    def get_mg5_info_lines(self):
        """Return info lines for MG5, suitable to place at beginning of
        Python files"""

        info = misc.get_pkg_info()
        info_lines = ""
        if info and info.has_key('version') and  info.has_key('date'):
            info_lines = "#  MadGraph 5 v. %s, %s\n" % \
                         (info['version'], info['date'])
            info_lines = info_lines + \
                         "        #  By the MadGraph Development Team\n" + \
                         "        #  Please visit us at https://launchpad.net/madgraph5"
        else:
            info_lines = "        #  by MadGraph 5\n" + \
                         "        #  By the MadGraph Development Team\n" + \
                         "        #  Please visit us at https://launchpad.net/madgraph5"        

        return info_lines

    def get_process_info_lines(self, matrix_element):
        """Return info lines describing the processes for this matrix element"""

        return"\n        ".join([ "# " + process.nice_string().replace('\n', '\n# * ') \
                         for process in matrix_element.get('processes')])


    def get_model_parameter_lines(self, matrix_element):
        """Return definitions for all model parameters used in this
        matrix element"""

        # Get all masses and widths used
        parameters = [wf.get('mass') for wf in \
                      matrix_element.get_all_wavefunctions()]
        parameters += [wf.get('width') for wf in \
                       matrix_element.get_all_wavefunctions()]
        parameters = list(set(parameters))
        if 'ZERO' in parameters:
            parameters.remove('ZERO')

        # Get all couplings used
        couplings = list(set([func.get('coupling').replace('-', '') for func \
                              in matrix_element.get_all_wavefunctions() + \
                              matrix_element.get_all_amplitudes()
                              if func.get('mothers')]))
        
        return "\n        ".join([\
                         "%(param)s = model.get(\'parameter_dict\')[\"%(param)s\"]"\
                         % {"param": param} for param in parameters]) + \
               "\n        " + "\n        ".join([\
                         "%(coup)s = model.get(\'coupling_dict\')[\"%(coup)s\"]"\
                              % {"coup": coup} for coup in couplings])

#===============================================================================
# Global helper methods
#===============================================================================

def coeff(ff_number, frac, is_imaginary, Nc_power, Nc_value=3):
    """Returns a nicely formatted string for the coefficients in JAMP lines"""

    total_coeff = ff_number * frac * fractions.Fraction(Nc_value) ** Nc_power

    if total_coeff == 1:
        if is_imaginary:
            return '+complex(0,1)*'
        else:
            return '+'
    elif total_coeff == -1:
        if is_imaginary:
            return '-complex(0,1)*'
        else:
            return '-'

    res_str = '%+i.' % total_coeff.numerator

    if total_coeff.denominator != 1:
        # Check if total_coeff is an integer
        res_str = res_str + '/%i.' % total_coeff.denominator

    if is_imaginary:
        res_str = res_str + '*complex(0,1)'

    return res_str + '*'
