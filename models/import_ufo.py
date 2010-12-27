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
""" How to import a UFO model to the MG5 format """


import fractions
import logging
import os
import re
import sys

from madgraph import MadGraph5Error, MG5DIR
import madgraph.core.base_objects as base_objects
import madgraph.core.color_algebra as color
import madgraph.iolibs.files as files
import madgraph.iolibs.save_load_object as save_load_object
from madgraph.core.color_algebra import *


import aloha.create_aloha as create_aloha

import models as ufomodels
import models.model_reader as model_reader
logger = logging.getLogger('models.import_ufo')
logger_mod = logging.getLogger('madgraph.model')

class UFOImportError(MadGraph5Error):
    """ a error class for wrong import of UFO model""" 

def find_ufo_path(model_name):
    """ find the path to a model """

    if os.path.isdir(model_name):
        model_path = model_name
    elif os.path.isdir(os.path.join(MG5DIR, 'models', model_name)):
        model_path = os.path.join(MG5DIR, 'models', model_name)
    else:
        raise UFOImportError("Path %s is not a valid pathname" % model_name)

    return model_path

def import_model(model_path):
    """ a practical and efficient way to import one of those models """

    assert model_path == find_ufo_path(model_path)
            
    # Check the validity of the model
    files_list_prov = ['couplings.py','lorentz.py','parameters.py',
                       'particles.py', 'vertices.py']
    files_list = []
    for filename in files_list_prov:
        filepath = os.path.join(model_path, filename)
        if not os.path.isfile(filepath):
            raise UFOImportError,  "%s directory is not a valid UFO model: \n %s is missing" % \
                                                         (model_path, filename)
        files_list.append(filepath)
        
    # use pickle files if defined and up-to-date
    if files.is_uptodate(os.path.join(model_path, 'model.pkl'), files_list):
        try:
            model = save_load_object.load_from_file( \
                                          os.path.join(model_path, 'model.pkl'))
        except Exception:
            logger.info('failed to load model from pickle file. Try importing UFO from File')
        else:
            return model

    # Load basic information
    ufo_model = ufomodels.load_model(model_path)
    ufo2mg5_converter = UFOMG5Converter(ufo_model)
    model = ufo2mg5_converter.load_model()
    model.set('name', os.path.split(model_path)[-1])
 
    # Load the Parameter/Coupling in a convinient format.
    parameters, couplings = OrganizeModelExpression(ufo_model).main()
    model.set('parameters', parameters)
    model.set('couplings', couplings)
    model.set('functions', ufo_model.all_functions)
    
    # save in a pickle files to fasten future usage
    save_load_object.save_to_file(os.path.join(model_path, 'model.pkl'), model) 
 
    return model
    

class UFOMG5Converter(object):
    """Convert a UFO model to the MG5 format"""

    use_lower_part_names = False

    def __init__(self, model, auto=False):
        """ initialize empty list for particles/interactions """
        
        self.particles = base_objects.ParticleList()
        self.interactions = base_objects.InteractionList()
        self.model = base_objects.Model()
        self.model.set('particles', self.particles)
        self.model.set('interactions', self.interactions)
        
        self.ufomodel = model
        
        if auto:
            self.load_model()

    def load_model(self):
        """load the different of the model first particles then interactions"""

        logger.info('load particles')
        # Check if multiple particles have the same name but different case.
        # Otherwise, we can use lowercase particle names.
        if len(set([p.name for p in self.ufomodel.all_particles] + \
                   [p.antiname for p in self.ufomodel.all_particles])) == \
           len(set([p.name.lower() for p in self.ufomodel.all_particles] + \
                   [p.antiname.lower() for p in self.ufomodel.all_particles])):
            self.use_lower_part_names = True

        for particle_info in self.ufomodel.all_particles:            
            self.add_particle(particle_info)
            
        logger.info('load vertices')
        for interaction_info in self.ufomodel.all_vertices:
            self.add_interaction(interaction_info)
        
        return self.model
        
    
    def add_particle(self, particle_info):
        """ convert and add a particle in the particle list """
        
        # MG5 have only one entry for particle and anti particles.
        #UFO has two. use the color to avoid duplictions
        if particle_info.pdg_code < 0:
            return
        
        # MG5 doesn't use ghost (use unitary gauges)
        if particle_info.spin < 0:
            return 
        # MG5 doesn't use goldstone boson 
        if hasattr(particle_info, 'GoldstoneBoson'):
            if particle_info.GoldstoneBoson:
                return
               
        # Initialize a particles
        particle = base_objects.Particle()

        nb_property = 0   #basic check that the UFO information is complete
        # Loop over the element defining the UFO particles
        for key,value in particle_info.__dict__.items():
            # Check if we use it in the MG5 definition of a particles
            if key in base_objects.Particle.sorted_keys:
                nb_property +=1
                if key in ['name', 'antiname']:
                    if self.use_lower_part_names:
                        particle.set(key, value.lower())
                    else:
                        particle.set(key, value)
                elif key == 'charge':
                    particle.set(key, float(value))
                else:
                    particle.set(key, value)
            
        assert(12 == nb_property) #basic check that all the information is there         
        
        # Identify self conjugate particles
        if particle_info.name == particle_info.antiname:
            particle.set('self_antipart', True)
            
        # Add the particles to the list
        self.particles.append(particle)


    def add_interaction(self, interaction_info):
        """add an interaction in the MG5 model. interaction_info is the 
        UFO vertices information."""
        
        # Import particles content:
        particles = [self.model.get_particle(particle.pdg_code) \
                                    for particle in interaction_info.particles]

        if None in particles:
            # Interaction with a ghost/goldstone
            return 
            
        particles = base_objects.ParticleList(particles)
        
        # Import Lorentz content:
        lorentz = [helas.name for helas in interaction_info.lorentz]
        
        # Import color information:
        colors = [self.treat_color(color_obj, interaction_info) for color_obj in \
                                    interaction_info.color]
        
        order_to_int={}
        
        for key, couplings in interaction_info.couplings.items():
            if not isinstance(couplings, list):
                couplings = [couplings]
            for coupling in couplings:
                order = tuple(coupling.order.items())
                if order in order_to_int:
                    order_to_int[order].get('couplings')[key] = coupling.name
                else:
                    # Initialize a new interaction with a new id tag
                    interaction = base_objects.Interaction({'id':len(self.interactions)+1})                
                    interaction.set('particles', particles)              
                    interaction.set('lorentz', lorentz)
                    interaction.set('couplings', {key: coupling.name})
                    interaction.set('orders', coupling.order)            
                    interaction.set('color', colors)
                    order_to_int[order] = interaction
                    # add to the interactions
                    self.interactions.append(interaction)

    
    _pat_T = re.compile(r'T\((?P<first>\d*),(?P<second>\d*)\)')
    _pat_id = re.compile(r'Identity\((?P<first>\d*),(?P<second>\d*)\)')
    
    def treat_color(self, data_string, interaction_info):
        """ convert the string to ColorString"""
        
        #original = copy.copy(data_string)
        #data_string = p.sub('color.T(\g<first>,\g<second>)', data_string)
        
        
        output = []
        factor = 1
        for term in data_string.split('*'):
            pattern = self._pat_id.search(term)
            if pattern:
                particle = interaction_info.particles[int(pattern.group('first'))-1]
                if particle.color == -3 :
                    output.append(self._pat_id.sub('color.T(\g<second>,\g<first>)', term))
                elif particle.color == 3:
                    output.append(self._pat_id.sub('color.T(\g<first>,\g<second>)', term))
                elif particle.color == -6 :
                    output.append(self._pat_id.sub('color.T6(\g<second>,\g<first>)', term))
                elif particle.color == 6:
                    output.append(self._pat_id.sub('color.T6(\g<first>,\g<second>)', term))
                elif particle.color == 8:
                    output.append(self._pat_id.sub('color.Tr(\g<first>,\g<second>)', term))
                    factor *= 2
                else:
                    raise MadGraph5Error, \
                          "Unknown use of Identity for particle with color %d" \
                          % particle.color
            else:
                output.append(term)
        data_string = '*'.join(output)

        # Change convention for summed indices
        p = re.compile(r'''\'\w(?P<number>\d+)\'''')
        data_string = p.sub('-\g<number>', data_string)
         
        # Shift indices by -1
        new_indices = {}
        new_indices = dict([(j,i) for (i,j) in \
                           enumerate(range(1,
                                    len(interaction_info.particles)+1))])

                        
        output = data_string.split('*')
        output = color.ColorString([eval(data) \
                                    for data in output if data !='1'])
        output.coeff = fractions.Fraction(factor)
        for col_obj in output:
            col_obj.replace_indices(new_indices)

        return output
      
class OrganizeModelExpression:
    """Organize the couplings/parameters of a model"""
    
    track_dependant = ['aS','aEWM1'] # list of variable from which we track 
                                   #dependencies those variables should be define
                                   #as external parameters
    
    # regular expression to shorten the expressions
    complex_number = re.compile(r'''complex\((?P<real>[^,\(\)]+),(?P<imag>[^,\(\)]+)\)''')
    expo_expr = re.compile(r'''(?P<expr>[\w.]+)\s*\*\*\s*(?P<expo>\d+)''')
    cmath_expr = re.compile(r'''cmath.(?P<operation>\w+)\((?P<expr>\w+)\)''')
    #operation is usualy sqrt / sin / cos / tan
    conj_expr = re.compile(r'''complexconjugate\((?P<expr>\w+)\)''')
    
    #RE expression for is_event_dependent
    separator = re.compile(r'''[+,\-*/()]''')    
    
    def __init__(self, model):
    
        self.model = model  # UFOMODEL
        self.params = {}     # depend on -> ModelVariable
        self.couplings = {}  # depend on -> ModelVariable
        self.all_expr = {} # variable_name -> ModelVariable
    
    def main(self):
        """Launch the actual computation and return the associate 
        params/couplings."""
        
        self.analyze_parameters()
        self.analyze_couplings()
        return self.params, self.couplings


    def analyze_parameters(self):
        """ separate the parameters needed to be recomputed events by events and
        the others"""
        
        for param in self.model.all_parameters:
            if param.nature == 'external':
                parameter = base_objects.ParamCardVariable(param.name, param.value, \
                                               param.lhablock, param.lhacode)
                
            else:
                expr = self.shorten_expr(param.value)
                depend_on = self.find_dependencies(expr)
                parameter = base_objects.ModelVariable(param.name, expr, param.type, depend_on)
            
            self.add_parameter(parameter)

            
    def add_parameter(self, parameter):
        """ add consistently the parameter in params and all_expr.
        avoid duplication """
        
        assert isinstance(parameter, base_objects.ModelVariable)
        
        if parameter.name in self.all_expr.keys():
            return
        
        self.all_expr[parameter.name] = parameter
        try:
            self.params[parameter.depend].append(parameter)
        except:
            self.params[parameter.depend] = [parameter]
            
    def add_coupling(self, coupling):
        """ add consistently the coupling in couplings and all_expr.
        avoid duplication """
        
        assert isinstance(coupling, base_objects.ModelVariable)
        
        if coupling.name in self.all_expr.keys():
            return
        
        self.all_expr[coupling.value] = coupling
        try:
            self.coupling[coupling.depend].append(coupling)
        except:
            self.coupling[coupling.depend] = [coupling]            
                
                

    def analyze_couplings(self):
        """creates the shortcut for all special function/parameter
        separate the couplings dependent of track variables of the others"""
        
        for coupling in self.model.all_couplings:
            
            # shorten expression, find dependencies, create short object
            expr = self.shorten_expr(coupling.value)
            depend_on = self.find_dependencies(expr)
            parameter = base_objects.ModelVariable(coupling.name, expr, 'complex', depend_on)
            
            # Add consistently in the couplings/all_expr
            try:
                self.couplings[depend_on].append(parameter)
            except KeyError:
                self.couplings[depend_on] = [parameter]
            self.all_expr[coupling.value] = parameter
            

    def find_dependencies(self, expr):
        """check if an expression should be evaluated points by points or not
        """
        depend_on = set()

        # Treat predefined result
        #if name in self.track_dependant:  
        #    return tuple()
        
        # Split the different part of the expression in order to say if a 
        #subexpression is dependent of one of tracked variable
        expr = self.separator.sub(' ',expr)
        
        # look for each subexpression
        for subexpr in expr.split():
            if subexpr in self.track_dependant:
                depend_on.add(subexpr)
                
            elif subexpr in self.all_expr.keys() and self.all_expr[subexpr].depend:
                [depend_on.add(value) for value in self.all_expr[subexpr].depend 
                                if  self.all_expr[subexpr].depend != ('external',)]

        if depend_on:
            return tuple(depend_on)
        else:
            return tuple()


    def shorten_expr(self, expr):
        """ apply the rules of contraction and fullfill
        self.params with dependent part"""

        expr = self.complex_number.sub(self.shorten_complex, expr)
        expr = self.expo_expr.sub(self.shorten_expo, expr)
        expr = self.cmath_expr.sub(self.shorten_cmath, expr)
        expr = self.conj_expr.sub(self.shorten_conjugate, expr)
        return expr
    

    def shorten_complex(self, matchobj):
        """add the short expression, and return the nice string associate"""
        
        real = float(matchobj.group('real'))
        imag = float(matchobj.group('imag'))
        if real == 0 and imag ==1:
            new_param = base_objects.ModelVariable('complexi', 'complex(0,1)', 'complex')
            self.add_parameter(new_param)
            return 'complexi'
        else:
            return 'complex(%s, %s)' % (real, imag)
        
        
    def shorten_expo(self, matchobj):
        """add the short expression, and return the nice string associate"""
        
        expr = matchobj.group('expr')
        exponent = matchobj.group('expo')
        output = '%s__exp__%s' % (expr, exponent)
        old_expr = '%s**%s' % (expr,exponent)

        if expr.startswith('cmath'):
            return old_expr
        
        if expr.isdigit():
            output = '_' + output #prevent to start with a number
            new_param = base_objects.ModelVariable(output, old_expr,'real')
        else:
            depend_on = self.find_dependencies(expr)
            type = self.search_type(expr)
            new_param = base_objects.ModelVariable(output, old_expr, type, depend_on)
        self.add_parameter(new_param)
        return output
        
    def shorten_cmath(self, matchobj):
        """add the short expression, and return the nice string associate"""
        
        expr = matchobj.group('expr')
        operation = matchobj.group('operation')
        output = '%s__%s' % (operation, expr)
        old_expr = ' cmath.%s(%s) ' %  (operation, expr)
        if expr.isdigit():
            new_param = base_objects.ModelVariable(output, old_expr , 'real')
        else:
            depend_on = self.find_dependencies(expr)
            type = self.search_type(expr)
            new_param = base_objects.ModelVariable(output, old_expr, type, depend_on)
        self.add_parameter(new_param)
        
        return output        
        
    def shorten_conjugate(self, matchobj):
        """add the short expression, and retrun the nice string associate"""
        
        expr = matchobj.group('expr')
        output = 'conjg__%s' % (expr)
        old_expr = ' complexconjugate(%s) ' % expr
        depend_on = self.find_dependencies(expr)
        type = 'complex'
        new_param = base_objects.ModelVariable(output, old_expr, type, depend_on)
        self.add_parameter(new_param)  
                    
        return output            
    

     
    def search_type(self, expr, dep=''):
        """return the type associate to the expression if define"""
        
        try:
            return self.all_expr[expr].type
        except:
            return 'complex'
            
class RestrictModel(model_reader.ModelReader):
    """ A class for restricting a model for a given param_card.
    Two rules apply:
     - Vertex with zero couplings are throw away
     - external parameter with zero input are changed into internal parameter."""
     
    def restrict_model(self, param_card):
        """apply the model restriction following param_card"""
        
        # compute the value of all parameters
        self.set_parameters_and_couplings(param_card)
        
        # deal with couplings
        zero_couplings = self.detect_zero_couplings()
        self.remove_couplings(zero_couplings)
        
        # deal with parameters
        zero_parameters = self.detect_zero_parameters()
        self.put_parameters_to_zero(zero_parameters)
        
        # deal with identical parameters
        iden_parameters = self.detect_identical_parameters()
        for iden_param in iden_parameters:
            self.merge_identical_parameters(iden_param)
        

    def detect_zero_couplings(self):
        """return a list with the name of all vanishing couplings"""
        
        zero_coupling = []
        
        for name, value in self['coupling_dict'].items():
            if value == 0:
                zero_coupling.append(name)
        return zero_coupling
    
    
    def detect_zero_parameters(self):
        """ return the list of (name of) parameter which are zero """
        
        null_parameters = []
        for name, value in self['parameter_dict'].items():
            if value == 0 and name != 'ZERO':
                null_parameters.append(name)
        return null_parameters
    
    def detect_identical_parameters(self):
        """ return the list of tuple of name of parameter with the same 
        input value """

        # Extract external parameters
        external_parameters = self['parameters'][('external',)]
        
        # define usefull variable to detect identical input
        block_value_to_var={} #(lhablok, value): list_of_var
        mult_param = set([])       # key of the previous dict with more than one
                              #parameter.
                              
        #detect identical parameter and remove the duplicate parameter
        for param in external_parameters[:]:
            value = self['parameter_dict'][param.name]
            if value == 0:
                continue
            key = (param.lhablock, value) 
            if key in block_value_to_var:
                block_value_to_var[key].append(param)
                mult_param.add(key)
                #remove the duplicate parameter
                #external_parameters.remove(param)
            else: 
                block_value_to_var[key] = [param]        
        
        output=[]  
        for key in mult_param:
            output.append(block_value_to_var[key])
            
        return output
            
    def merge_identical_parameters(self, parameters):
        """ merge the identical parameters given in argument """
            
        logger_mod.info('Parameters set to identical values: %s '% \
                        ', '.join([obj.name for obj in parameters]))
        
        # Extract external parameters
        external_parameters = self['parameters'][('external',)]
        for i, obj in enumerate(parameters):
            # Keeped intact the first one and store information
            if i == 0:
                obj.info = 'set of param :' + \
                                     ', '.join([param.name for param in parameters])
                expr = obj.name
                continue
            # delete the old parameters
            external_parameters.remove(obj)
            # replace by the new one pointing of the first obj of the class
            new_param = base_objects.ModelVariable(obj.name, expr, 'real')
            self['parameters'][()].insert(0, new_param)
        
    
    def remove_couplings(self, zero_couplings):
        """ remove the interactions associated to couplings"""
        
        # clean the interactions
        for interaction in self['interactions'][:]:
            modified = False
            for key, coupling in interaction['couplings'].items()[:]:
                if coupling in zero_couplings:
                    modified = True
                    del interaction['couplings'][key]
                    
            if modified: 
                part_name = [part['name'] for part in interaction['particles']]
                orders = ['%s=%s' % (order,value) 
                               for order,value in interaction['orders'].items()]                    
            if not interaction['couplings']:
                logger_mod.info('remove interactions: %s at order: %s' % \
                                (' '.join(part_name),', '.join(orders)))
                self['interactions'].remove(interaction)
            elif modified:
                logger_mod.info('modify interactions: %s at order: %s' % \
                                (' '.join(part_name),', '.join(orders)))                
        #clean the coupling list:
        for name, data in self['couplings'].items():
            for coupling in data[:]:
                if coupling.name in zero_couplings:
                    data.remove(coupling)
        
    def put_parameters_to_zero(self, zero_parameters):
        """ Remove all instance of the parameters in the model and replace it by 
        zero when needed."""
        
        # treat specific cases for masses and width
        for particle in self['particles']:
            if particle['mass'] in zero_parameters:
                particle['mass'] = 'ZERO'
            if particle['width'] in zero_parameters:
                particle['width'] = 'ZERO'
        for pdg, particle in self['particle_dict'].items():
            if particle['mass'] in zero_parameters:
                particle['mass'] = 'ZERO'
            if particle['width'] in zero_parameters:
                particle['width'] = 'ZERO'            
        
        # check if the parameters is still usefull:
        used = set()
        # check in coupling
        for name, coupling_list in self['couplings'].items():
            for coupling in coupling_list:
                for param in zero_parameters:
                    if param in coupling.expr:
                        used.add(param)
                        
        zero_param_info = {}
        # check in parameters
        for dep, param_list in self['parameters'].items():
            for tag, parameter in enumerate(param_list):
                # update information concerning zero_parameters

                if parameter.name in zero_parameters:
                    zero_param_info[parameter.name]= {'dep': dep, 'tag': tag, 
                                                               'obj': parameter}
                    continue
                # Bypass all external parameter
                if isinstance(parameter, base_objects.ParamCardVariable):
                    continue

                # check the presence of zero parameter
                for zero_param in zero_parameters:
                    if zero_param in parameter.expr:
                        used.add(zero_param)

        # modify the object for those which are still used
        for param in used:
            data = self['parameters'][zero_param_info[param]['dep']]
            data.remove(zero_param_info[param]['obj'])
            tag = zero_param_info[param]['tag']
            data = self['parameters'][()]
            data.insert(0, base_objects.ModelVariable(param, '0.0', 'real'))
        
        # remove completely useless parameters
        for param in zero_parameters:
            #by pass parameter still in use
            if param in used:
                logger_mod.info('put parameter to zero: %s' % param)
                continue 
            logger_mod.info('remove parameters: %s' % param)
            data = self['parameters'][zero_param_info[param]['dep']]
            data.remove(zero_param_info[param]['obj'])
            
        
                
                
        
        
        
         
      
    
      
        
        
    
