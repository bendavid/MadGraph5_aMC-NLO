################################################################################
#
# Copyright (c) 2010 The MadGraph Development team and Contributors
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
from madgraph import MG5DIR
import subprocess
import shutil
import unittest
import os

import madgraph.core.base_objects as base_objects
import madgraph.iolibs.convert_ufo2mg4 as ufo2mg4
import madgraph.iolibs.import_ufo as import_ufo
import madgraph.iolibs.files as files
import madgraph.iolibs.import_v4 as import_v4


file_dir_path = os.path.dirname(os.path.realpath( __file__ ))
root_path = os.path.join(file_dir_path, os.pardir, os.pardir, os.pardir)


class CompareMG4WithUFOModel(unittest.TestCase):
    """checking if the MG4 model and the UFO model are coherent when they should"""
    
    
    def test_model_equivalence(self):
        """ test the UFO and MG4 model correspond to the same model """
        
        # import UFO model
        import models.sm as model
        converter = import_ufo.converter_ufo_mg5(model)
        ufo_model = converter.load_model()
        
        # import MG4 model
        model = base_objects.Model()
        model.set('particles', files.read_from_file(
               os.path.join(MG5DIR,'tests','input_files','v4_sm_particles.dat'),
               import_v4.read_particles_v4))
        model.set('interactions', files.read_from_file(
            os.path.join(MG5DIR,'tests','input_files','v4_sm_interactions.dat'),
            import_v4.read_interactions_v4,
            model['particles']))
        
        # Checking the particles
        for particle in model['particles']:
            ufo_particle = ufo_model["particle_dict"][particle['pdg_code']]
            self.check_particles(particle, ufo_particle)
        
        # Checking the interactions
        nb_vertex = 0
        for ufo_vertex in ufo_model['interactions']:
            pdg_code_ufo = [abs(part['pdg_code']) for part in ufo_vertex['particles']]
            int_name = [part['name'] for part in ufo_vertex['particles']]
            rep = (pdg_code_ufo, int_name)
            pdg_code_ufo.sort()
            for vertex in model['interactions']:
                pdg_code_mg4 = [abs(part['pdg_code']) for part in vertex['particles']]
                pdg_code_mg4.sort()
                
                if pdg_code_mg4 == pdg_code_ufo:
                    nb_vertex += 1
                    self.check_interactions(vertex, ufo_vertex, rep )
            
        self.assertEqual(nb_vertex, 67)
            
    
    def check_particles(self, mg4_part, ufo_part):
        """ check that the internal definition for a particle comming from mg4 or
        comming from the UFO are the same """
        
        not_equiv = ['charge', 'mass','width',
                        'texname','antitexname']
        
        if abs(mg4_part['pdg_code']) != abs(ufo_part['pdg_code']):
            print '%s non equivalent particle' % mg4_part['name']
            return
        elif mg4_part['pdg_code'] != ufo_part['pdg_code']:
            self.assertFalse(mg4_part.get('is_part') == ufo_part.get('is_part'))
            not_equiv.append('is_part')
            not_equiv.append('pdg_code')
            not_equiv.append('name')
            not_equiv.append('antiname')
            self.assertTrue(mg4_part.get('name') == ufo_part.get('antiname'))
            
            
        
        for name in mg4_part.sorted_keys:
            if name in not_equiv:
                continue
            self.assertEqual(mg4_part.get(name), ufo_part.get(name), 
                    'fail for particle %s different property for %s, %s != %s' %
                    (mg4_part['name'], name, mg4_part.get(name), \
                                                            ufo_part.get(name)))
        
        
    def check_interactions(self, mg4_vertex, ufo_vertex, vname):
        """ check that the internal definition for a particle comming from mg4 or
        comming from the UFO are the same """
        
        # don't check this for the moment. Too difficult to compare
        return
        
        # Checking only the color
        name = 'color'
        self.assertEqual(mg4_vertex.get(name), ufo_vertex.get(name), 
            'fail for interactions %s different property for %s, %s != %s' % \
            (vname, name, mg4_vertex.get(name), ufo_vertex.get(name) ) )
        
class TestPythonToFrotran(unittest.TestCase):
    
    def test_convert_str(self):
        """ python to fortran expression is working"""
        
        expr = 'cmath.sqrt(2)'
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted.__class__, ufo2mg4.python_to_fortran)
        self.assertTrue(isinstance(converted, str))
        self.assertEqual(converted, 'dsqrt(2.000000d+00)')
        
        expr = 'cmath.sqrt(2.)'
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted, 'dsqrt(2.000000d+00)')
        
        expr = 'cmath.sqrt(2.5)'
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted, 'dsqrt(2.500000d+00)')

        
        expr = '(ee**2*IMAG/(2.*sw**2) * (cmath.sin(cmath.sqrt(2)*ee)/3.))'
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted, 
        '(ee**2*imag/(2.000000d+00*sw**2)*(sin(dsqrt(2.000000d+00)*ee)/3.000000d+00))')
    
    def test_convert_number(self):
        """ test it can convert number in fortran string"""
        
        expr = 2
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted.__class__, ufo2mg4.python_to_fortran)
        self.assertTrue(isinstance(converted, str))
        self.assertEqual(converted, '2.000000d+00')  
        
        expr = 0.23
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted.__class__, ufo2mg4.python_to_fortran)
        self.assertTrue(isinstance(converted, str))
        self.assertEqual(converted, '2.300000d-01')  
        
        expr = 2.5e6
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted.__class__, ufo2mg4.python_to_fortran)
        self.assertTrue(isinstance(converted, str))
        self.assertEqual(converted, '2.500000d+06')
        
        expr = 0.0000116639  
        converted = ufo2mg4.python_to_fortran(expr)
        self.assertEqual(converted.__class__, ufo2mg4.python_to_fortran)
        self.assertTrue(isinstance(converted, str))
        self.assertEqual(converted, '1.166390d-05')        
        
        
class CheckFileCreate():
    """Check that the files are correctly created"""

    output_path = '/tmp/' # work only on LINUX but that's ok for the test routine
    created_files =[]

    def assertFileContains(self, filename, solution):
        """ Check the content of a file """

        current_value = open(self.give_pos(filename)).read()
        self.assertEqual(current_value, solution)

    def FileContent(self, filename):
        return open(self.give_pos(filename)).read()

    def ReturnFile(self, filename):
        return open(self.give_pos(filename))

    def give_pos(self, filename):
        """ take a name and a change it in order to have a valid path in the output directory """
        
        return os.path.join(self.output_path, filename)

    def clean_files(self):
        """ suppress all the files linked to this test """
        
        for filename in self.created_files:
            try:
                os.remove(self.give_pos(filename))
            except OSError:
                pass
    

class TestModelCreation(unittest.TestCase, CheckFileCreate):

    created_files = ['couplings.f', 'couplings1.f', 'couplings2.f', 'couplings3.f', 
                     'couplings4.f', 'coupl.inc', 'intparam_definition.inc',
                     'input.inc', 'param_read.f', 'makefile', 'tesprog.f', 
                     'testprog', 'rw_para.f', 'lha_read.f', 'printout.f', 
                     'formats.inc', 'makeinc.inc', 'ident_card.dat', 'libmodel.a',
                     'param_write.inc','coupl_write.inc','param_read.inc',
                     'testprog.f','param_card.dat']

    # clean all the tested files before and after any test
    def setUp(self):
        """ creating the full model from scratch """
        CheckFileCreate.clean_files(self)
        
        import models.sm as model
        ufo2mg4.export_to_mg4(model, self.output_path)
        
        
#    tearDown = CheckFileCreate.clean_files

    def test_all(self):
        """ test all the files"""
        self.check_intparam_definition_creation()
        self.check_compilation()
        
        
    def check_compilation(self):
        """check that the model compile return correct output"""
        #Check the cleaning
        self.assertFalse(os.path.exists(self.give_pos('testprog')))
        subprocess.call(['make', 'testprog'], cwd=self.output_path,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertTrue(os.path.exists(self.give_pos('testprog')))
        
        os.chmod(os.path.join(self.output_path, 'testprog'), 0777)
        testprog = subprocess.Popen("./testprog", stdout=subprocess.PIPE,
                            cwd=self.output_path,
                            stderr=subprocess.STDOUT, shell=True)
        
        
        solutions = {'ymtau ': [1.7769999999999999], 'GC_5 ': [0.0, 1.2135800000000001], 'MZ ': [91.188000000000002], 'GC_27 ': [-0.0, -0.35583999999999999], 'aEWM1 ': [127.90000000000001], 'GC_29 ': [0.0, 0.37035000000000001], 'ytau ': [0.010206617000654717], 'GC_16 ': [-0.0, -0.10352], 'GC_35 ': [-0.0, -0.00577], 'GC_45 ': [0.0, 0.0], 'CKM31 ': [0.0, 0.0], 'MH__EXP__2 ': [14400.0], 'COMPLEXI ': [0.0, 1.0], 'G ': [1.2135809144852661], 'ymb ': [4.7000000000000002], 'Gf ': [1.16639e-05], 'GC_21 ': [0.0, 0.45849000000000001], 'ee ': [0.31345100004952897], 'WZ ': [2.4413999999999998], 'ye ': [0.0], 'GC_4 ': [-1.2135800000000001, 0.0], 'CONJG__CKM21 ': [-0.2257725604285693, -0.0], 'WT ': [1.50834], 'GC_18 ': [0.0, 0.0], 'CONJG__CKM11 ': [0.97418004031982097, -0.0], 'GC_28 ': [0.0, 0.098250000000000004], 'GC_36 ': [-0.0, -0.0], 'GC_17 ': [0.0, 0.44666], 'ym ': [0.0], 'GC_20 ': [0.0, 0.0], 'GC_3 ': [-0.0, -0.31345000000000001], 'gw__EXP__2 ': [0.4204345654976559], 'CONJG__CKM22 ': [0.97418004031982097, -0.0], 'yd ': [0.0], 'WW ': [2.0476000000000001], 'GC_38 ': [-0.0, -0.0], 'MZ__EXP__2 ': [8315.2513440000002], 'GC_26 ': [0.0, 0.31345000000000001], 'gw ': [0.64840925772050473], 'GC_44 ': [0.0, 0.10352], 'GC_19 ': [0.0, 0.0], 'MH ': [120.0], 'GC_51 ': [0.0, 0.45849000000000001], 'GC_14 ': [0.0, 0.10352], 'GC_37 ': [-0.0, -0.0], 'yu ': [0.0], 'GC_47 ': [0.0, 0.44666], 'SQRT__aEW ': [0.088422894590285753], 'CONJG__CKM23 ': [0.0, -0.0], 'GC_2 ': [0.0, 0.20896999999999999], 'CONJG__CKM33 ': [1.0, -0.0], 'CONJG__CKM13 ': [0.0, -0.0], 'GC_49 ': [0.0, 0.0], 'GC_39 ': [-0.0, -0.0], 'v__EXP__2 ': [60623.529110035888], \
                     'SQRT__aS ': [0.34234485537247378], 'GC_30 ': [0.0, 0.27432000000000001], 'MW ': [79.825163827442964], 'ymc ': [1.4199999999999999], 'cw ': [0.87539110220032201], 'yc ': [0.008156103624608722], 'G__EXP__2 ': [1.4727786360028947], 'yt ': [1.0011330012459863], 'ee__EXP__2 ': [0.098251529432049817], 'CONJG__CKM32 ': [0.0, -0.0], 'GC_48 ': [0.0, 0.0], 'cw__EXP__2 ': [0.76630958181149467], 'GC_1 ': [-0.0, -0.10448], 'CKM11 ': [0.97418004031982097, 0.0], 'GC_12 ': [0.0, 0.45849000000000001], 'GC_25 ': [0.0, 0.086550000000000002], 'ys ': [0.0], 'GC_41 ': [-0.0, -0.0072199999999999999], 'GC_31 ': [-0.0, -175.45394999999999], 'aS ': [0.1172], 'yb ': [0.026995554250465494], 'SQRT__2 ': [1.4142135623730951], 'CKM21 ': [-0.2257725604285693, 0.0], 'WH ': [0.0057530899999999998], 'CONJG__CKM31 ': [0.0, -0.0], 'MW__EXP__2 ': [6372.0567800781082], 'CKM12 ': [0.2257725604285693, 0.0], 'GC_13 ': [0.0, 0.44666], 'sw ': [0.48341536817575986], 'CKM32 ': [0.0, 0.0], \
                     'CONJG__CKM12 ': [0.2257725604285693, -0.0], 'GC_40 ': [-0.0, -0.70791000000000004], 'GC_9 ': [0.0, 0.32218000000000002], 'cabi ': [0.22773599999999999], 'GC_24 ': [-0.0, -0.028850000000000001], 'GC_32 ': [0.0, 51.75938], 'muH ': [84.852813742385706], 'MZ__EXP__4 ': [69143404.913893804], 'GC_7 ': [0.0, 0.56760999999999995], 'aEW ': [0.0078186082877247844], 'MC ': [1.4199999999999999], 'SQRT__sw2 ': [0.48341536817575986], 'g1 ': [0.35806966653151989], 'GC_10 ': [-0.0, -0.71258999999999995], 'GC_8 ': [-0.0, -0.42043000000000003], 'CKM33 ': [1.0, 0.0], 'MTA ': [1.7769999999999999], 'CKM13 ': [0.0, 0.0], 'GC_23 ': [0.0, 0.28381000000000001], 'GC_15 ': [0.0, 0.0], 'CKM23 ': [0.0, 0.0], 'MT ': [174.30000000000001], \
                     'GC_33 ': [0.0, 67.543689999999998], 'v ': [246.21845810181634], 'GC_6 ': [0.0, 1.47278], 'CKM22 ': [0.97418004031982097, 0.0], 'sw2 ': [0.23369041818850544], 'MB ': [4.7000000000000002], 'ymt ': [174.30000000000001], 'GC_43 ': [0.0, 0.44666], 'lam ': [0.1187657681051775], 'GC_46 ': [0.0, -0.10352], 'GC_50 ': [0.0, 0.0], 'sw__EXP__2 ': [0.23369041818850547], 'GC_34 ': [-0.0, -0.019089999999999999], 'GC_11 ': [0.0, 0.21021999999999999], 'GC_22 ': [-0.0, -0.28381000000000001], 'GC_42 ': [-0.0, -0.0]}

        nb_value = 0
        for line in testprog.stdout:
            self.assertTrue('Warning' not in line)
            if '=' not in line:
                continue
            split = line.split('=')
            variable = split[0].lstrip()
            if ',' in line:
                value = eval(split[1])
            else:
                value=[float(numb) for numb in split[1].split()]
            nb_value +=1
            for i, singlevalue in enumerate(value):
#                try:
                    self.assertAlmostEqual(singlevalue, solutions[variable][i], 7, 'fail to be equal for param %s : %s != %s' % (variable, singlevalue, solutions[variable][i]))
#                except:
#                    print i, singlevalue, [variable]
#                    if i == 0:
#                        solutions[variable] = [singlevalue]
#                    else:
#                        solutions[variable].append(singlevalue)
#        print solutions
        self.assertEqual(nb_value, 123)
        
        

    def check_intparam_definition_creation(self):
        """ test the creation of a valid intparam_definition"""

        # Check that any definition appears only once:
        alreadydefine = []
        for line in self.ReturnFile('intparam_definition.inc'):
            if 'ENDIF' in line:
                self.assertEqual(len(alreadydefine), 53)
                
            if '=' not in line:
                continue
            
            new_def = line.split('=')[0].lstrip()
            # Check that is the firsttime that this definition is done
            self.assertFalse(new_def in alreadydefine)
            alreadydefine.append(new_def)
        alreadydefine.sort()
        solution = ['AEW ', 'SQRT__AS ', 'G ', 'YE ', 'YM ', 'YU ', 'YD ', 'YS ', 'CKM11 ', 'CKM12 ', 'CKM13 ', 'CKM21 ', 'CKM22 ', 'CKM23 ', 'CKM31 ', 'CKM32 ', 'CKM33 ', 'MZ__EXP__2 ', 'MZ__EXP__4 ', 'SQRT__2 ', 'MW ', 'SQRT__AEW ', 'EE ', 'MW__EXP__2 ', 'SW2 ', 'CW ', 'SQRT__SW2 ', 'SW ', 'G1 ', 'GW ', 'V ', 'MH__EXP__2 ', 'V__EXP__2 ', 'LAM ', 'YB ', 'YC ', 'YT ', 'YTAU ', 'MUH ', 'COMPLEXI ', 'GW__EXP__2 ', 'CW__EXP__2 ', 'EE__EXP__2 ', 'SW__EXP__2 ', 'CONJG__CKM11 ', 'CONJG__CKM12 ', 'CONJG__CKM13 ', 'CONJG__CKM21 ', 'CONJG__CKM22 ', 'CONJG__CKM23 ', 'CONJG__CKM31 ', 'CONJG__CKM32 ', 'CONJG__CKM33 ', 'G__EXP__2 ', 'GAL(1) ', 'GAL(2) ', 'DUM0 ', 'DUM1 ']
        solution.sort()
        self.assertEqual(alreadydefine,solution)
                                       

