################################################################################
#
# Copyright (c) 2011 The MadGraph Development team and Contributors
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
"""A user friendly command line interface to access MadGraph features.
   Uses the cmd package for command interpretation and tab completion.
"""
from __future__ import division

import atexit
import glob
import logging
import math
import optparse
import os
import pydoc
import re
import shutil
import subprocess
import sys
import traceback
import time

try:
    import readline
    GNU_SPLITTING = ('GNU' in readline.__doc__)
except:
    GNU_SPLITTING = True

root_path = os.path.split(os.path.dirname(os.path.realpath( __file__ )))[0]
root_path = os.path.split(root_path)[0]
sys.path.insert(0, os.path.join(root_path,'bin'))

# usefull shortcut
pjoin = os.path.join
 
try:
    # import from madgraph directory
    import madgraph.interface.extended_cmd as cmd
    import madgraph.iolibs.misc as misc
    import madgraph.iolibs.files as files
    import madgraph.iolibs.save_load_object as save_load_object
    import madgraph.various.gen_crossxhtml as gen_crossxhtml
    import madgraph.various.cluster as cluster
    import models.check_param_card as check_param_card
    from madgraph import InvalidCmd
    MADEVENT = False
except Exception, error:
    # import from madevent directory
    import internal.extended_cmd as cmd
    import internal.misc as misc    
    from internal import InvalidCmd
    import internal.files as files
    import internal.gen_crossxhtml as gen_crossxhtml
    import internal.save_load_object as save_load_object
    import internal.cluster as cluster
    import internal.check_param_card as check_param_card
    MADEVENT = True

# Special logger for the Cmd Interface
logger = logging.getLogger('madevent.stdout') # -> stdout
logger_stderr = logging.getLogger('madevent.stderr') # ->stderr


class MadEventError(Exception):
    pass

#===============================================================================
# CmdExtended
#===============================================================================
class CmdExtended(cmd.Cmd):
    """Particularisation of the cmd command for MadEvent"""

    #suggested list of command
    next_possibility = {
        'start': [],
    }
    
    debug_output = 'ME5_debug'
    error_debug = 'Please report this bug on https://bugs.launchpad.net/madgraph5\n'
    error_debug += 'More information is found in \'%s\'.\n' 
    error_debug += 'Please attach this file to your report.'
    
    keyboard_stop_msg = """stopping all operation
            in order to quit madevent please enter exit"""
    
    # Define the Error
    InvalidCmd = InvalidCmd
    
    def __init__(self, *arg, **opt):
        """Init history and line continuation"""
        
        # If possible, build an info line with current version number 
        # and date, from the VERSION text file
        info = misc.get_pkg_info()
        info_line = ""
        if info and info.has_key('version') and  info.has_key('date'):
            len_version = len(info['version'])
            len_date = len(info['date'])
            if len_version + len_date < 30:
                info_line = "#*         VERSION %s %s %s         *\n" % \
                            (info['version'],
                            (30 - len_version - len_date) * ' ',
                            info['date'])
        else:
            version = open(pjoin(root_path,'MGMEVersion.txt')).readline().strip()
            info_line = "#*         VERSION %s %s                *\n" % \
                            (version, (24 - len(version)) * ' ')    

        # Create a header for the history file.
        # Remember to fill in time at writeout time!
        self.history_header = \
        '#************************************************************\n' + \
        '#*                    MadGraph/MadEvent 5                   *\n' + \
        '#*                                                          *\n' + \
        "#*                *                       *                 *\n" + \
        "#*                  *        * *        *                   *\n" + \
        "#*                    * * * * 5 * * * *                     *\n" + \
        "#*                  *        * *        *                   *\n" + \
        "#*                *                       *                 *\n" + \
        "#*                                                          *\n" + \
        "#*                                                          *\n" + \
        info_line + \
        "#*                                                          *\n" + \
        "#*    The MadGraph Development Team - Please visit us at    *\n" + \
        "#*    https://server06.fynu.ucl.ac.be/projects/madgraph     *\n" + \
        '#*                                                          *\n' + \
        '#************************************************************\n' + \
        '#*                                                          *\n' + \
        '#*               Command File for MadEvent                  *\n' + \
        '#*                                                          *\n' + \
        '#*     run as ./bin/madevent.py filename                    *\n' + \
        '#*                                                          *\n' + \
        '#************************************************************\n'
        
        if info_line:
            info_line = info_line[1:]

        logger.info(\
        "************************************************************\n" + \
        "*                                                          *\n" + \
        "*           W E L C O M E  to  M A D G R A P H  5          *\n" + \
        "*                      M A D E V E N T                     *\n" + \
        "*                                                          *\n" + \
        "*                 *                       *                *\n" + \
        "*                   *        * *        *                  *\n" + \
        "*                     * * * * 5 * * * *                    *\n" + \
        "*                   *        * *        *                  *\n" + \
        "*                 *                       *                *\n" + \
        "*                                                          *\n" + \
        info_line + \
        "*                                                          *\n" + \
        "*    The MadGraph Development Team - Please visit us at    *\n" + \
        "*    https://server06.fynu.ucl.ac.be/projects/madgraph     *\n" + \
        "*                                                          *\n" + \
        "*               Type 'help' for in-line help.              *\n" + \
        "*                                                          *\n" + \
        "************************************************************")
        
        cmd.Cmd.__init__(self, *arg, **opt)
        
    def get_history_header(self):
        """return the history header""" 
        return self.history_header % misc.get_time_info()
    
    def stop_on_keyboard_stop(self):
        """action to perform to close nicely on a keyboard interupt"""
        try:
            if hasattr(self, 'results'):
                self.results.update('Stop by the user', level=None, makehtml=False)
        except:
            pass
    
    def postcmd(self, stop, line):
        """ Upate the status of  the run for finishing interactive command """
        if not self.use_rawinput:
            return stop
        
        arg = line.split()
        if  len(arg) == 0:
            return stop
        if self.results.status.startswith('Error'):
            return stop
        if self.results.status == 'Stop by the user':
            self.results.update('%s Stop by the user' % arg[0], level=None)
            return stop        
        elif not self.results.status:
            return stop
        
        self.update_status('%s Done.<br> Waiting for instruction.' % arg[0], level=None)
        
    #def nice_error_handling(self, error, line):
    #    """store current result when an error occur"""
    #    cmd.Cmd.nice_error_handling(self, error, line)
    #    self.exec_cmd('quit')
    
#===============================================================================
# HelpToCmd
#===============================================================================
class HelpToCmd(object):
    """ The Series of help routine for the MadEventCmd"""
    
    def help_open(self):
        logger.info("syntax: open FILE  ")
        logger.info("-- open a file with the appropriate editor.")
        logger.info('   If FILE belongs to index.html, param_card.dat, run_card.dat')
        logger.info('   the path to the last created/used directory is used')
        logger.info('   The program used to open those files can be chosen in the')
        logger.info('   configuration file ./input/mg5_configuration.txt')   

    def help_set(self):
        logger.info("syntax: set %s argument" % "|".join(self._set_options))
        logger.info("-- set options")
        logger.info("   stdout_level DEBUG|INFO|WARNING|ERROR|CRITICAL")
        logger.info("     change the default level for printed information")
        

    def run_options_help(self, data):
        if data:
            logger.info('-- local options:')
            for name, info in data:
                logger.info('      %s : %s' % (name, info))
        
        logger.info("-- session options:")
        logger.info("      Note that those options will be kept for the current session")      
        logger.info("      --cluster : Submit to the  cluster. Current cluster: %s" % self.configuration['cluster_mode'])
        logger.info("      --multicore : Run in multi-core configuration")
        logger.info("      --nb_core=X : limit the number of core to use to X.")
        

    def help_generate_events(self):
        logger.info("syntax: generate_events [run_name] [--run_options])")
        logger.info("-- Launch the full chain of script for the generation of events")
        logger.info("   Including possible plotting, shower and detector resolution.")
        logger.info("   Those steps are performed if the related program are installed")
        logger.info("   and if the related card are present in the Cards directory.")
        self.run_options_help([])

    def help_multi_run(self):
        logger.info("syntax: multi_run NB_RUN [run_name] [--run_options])")
        logger.info("-- Launch the full chain of script for the generation of events")
        logger.info("   NB_RUN times. This chains includes possible plotting, shower")
        logger.info(" and detector resolution.")
        self.run_options_help([])


    def help_survey(self):
        logger.info("syntax: survey [run_name] [--run_options])")
        logger.info("-- evaluate the different channel associate to the process")
        self.run_options_help([])
        
    def help_refine(self):
        logger.info("syntax: refine require_precision [max_channel] [run_name] [--run_options]")
        logger.info("-- refine the LAST run to achieve a given precision.")
        logger.info("   require_precision: can be either the targeted number of events")
        logger.info('                      or the required relative error')
        logger.info('   max_channel:[5] maximal number of channel per job')
        self.run_options_help([])
        
    def help_combine_events(self):
        """ """
        logger.info("syntax: combine_events [run_name] [--run_options]")
        logger.info("-- Combine the last run in order to write the number of events")
        logger.info("   require in the run_card.")
        self.run_options_help([])
        
    def help_plot(self):
        logger.info("syntax: help [RUN] [%s] " % '|'.join(self._plot_mode))
        logger.info("-- create the plot for the RUN (current run by default)")
        logger.info("     at the different stage of the event generation")
        logger.info("     Note than more than one mode can be specified in the same command.")
        logger.info("   This require to have MadAnalysis and td require. By default")
        logger.info("     if those programs are installed correctly, the creation")
        logger.info("     will be performed automaticaly during the event generation.")
        
    def help_pythia(self):
        logger.info("syntax: pythia [RUN] [--run_options]")
        logger.info("-- run pythia on RUN (current one by default)")
        self.run_options_help([('-f','answer all question by default'),
                               ('--no_default', 'not run if pythia_card not present')])        
                
    def help_pgs(self):
        logger.info("syntax: pgs [RUN] [--run_options]")
        logger.info("-- run pgs on RUN (current one by default)")
        self.run_options_help([('-f','answer all question by default'),
                               ('--no_default', 'not run if pgs_card not present')]) 

    def help_delphes(self):
        logger.info("syntax: delphes [RUN] [--run_options]")
        logger.info("-- run delphes on RUN (current one by default)")
        self.run_options_help([('-f','answer all question by default'),
                               ('--no_default', 'not run if delphes_card not present')]) 
       
#===============================================================================
# CheckValidForCmd
#===============================================================================
class CheckValidForCmd(object):
    """ The Series of check routine for the MadEventCmd"""


    def check_history(self, args):
        """check the validity of line"""
        
        if len(args) > 1:
            self.help_history()
            raise self.InvalidCmd('\"history\" command takes at most one argument')
        
        if not len(args):
            return
        elif args[0] != 'clean':
                dirpath = os.path.dirname(args[0])
                if dirpath and not os.path.exists(dirpath) or \
                       os.path.isdir(args[0]):
                    raise self.InvalidCmd("invalid path %s " % dirpath)
                
    def check_set(self, args):
        """ check the validity of the line"""
        
        if len(args) < 2:
            self.help_set()
            raise self.InvalidCmd('set needs an option and an argument')

        if args[0] not in self._set_options:
            self.help_set()
            raise self.InvalidCmd('Possible options for set are %s' % \
                                  self._set_options)
        
        if args[0] in ['stdout_level']:
            if args[1] not in ['DEBUG','INFO','WARNING','ERROR','CRITICAL']:
                raise self.InvalidCmd('output_level needs ' + \
                                      'a valid level')  
    def check_open(self, args):
        """ check the validity of the line """
        
        if len(args) != 1:
            self.help_open()
            raise self.InvalidCmd('OPEN command requires exactly one argument')

        if args[0].startswith('./'):
            if not os.path.isfile(args[0]):
                raise self.InvalidCmd('%s: not such file' % args[0])
            return True

        # if special : create the path.
        if not self.me_dir:
            if not os.path.isfile(args[0]):
                self.help_open()
                raise self.InvalidCmd('No MadEvent path defined. Impossible to associate this name to a file')
            else:
                return True
            
        path = self.me_dir
        if os.path.isfile(os.path.join(path,args[0])):
            args[0] = os.path.join(path,args[0])
        elif os.path.isfile(os.path.join(path,'Cards',args[0])):
            args[0] = os.path.join(path,'Cards',args[0])
        elif os.path.isfile(os.path.join(path,'HTML',args[0])):
            args[0] = os.path.join(path,'HTML',args[0])
        # special for card with _default define: copy the default and open it
        elif '_card.dat' in args[0]:   
            name = args[0].replace('_card.dat','_card_default.dat')
            if os.path.isfile(os.path.join(path,'Cards', name)):
                files.cp(path + '/Cards/' + name, path + '/Cards/'+ args[0])
                args[0] = os.path.join(path,'Cards', args[0])
            else:
                raise self.InvalidCmd('No default path for this file')
        elif not os.path.isfile(args[0]):
            raise self.InvalidCmd('No default path for this file') 
    
    def check_survey(self, args, cmd='survey'):
        """check that the argument for survey are valid"""
        
        if len(args) > 1:
            self.help_survey()
            raise self.InvalidCmd('Too many argument for %s command' % cmd)
        elif not args:
            # No run name assigned -> assigned one automaticaly 
            self.set_run_name(self.find_available_run_name(self.me_dir))
        else:
            self.set_run_name(args[0], True)
            args.pop(0)
            
        return True

    def check_multi_run(self, args):
        """check that the argument for survey are valid"""
        
        if not len(args):
            print self.help_multi_run()
            raise self.InvalidCmd("""multi_run command requires at least one argument for
            the number of times that it call generate_events command""")
        elif not args[0].isdigit():
            print self.help_multi_run()
            raise self.InvalidCmd("The first argument of multi_run should be a integer.")
        nb_run = args.pop(0)
        self.check_survey(args, cmd='multi_run')
        args.insert(0, int(nb_run))
        
        return True

    def check_refine(self, args):
        """check that the argument for survey are valid"""

        # if last argument is not a number -> it's the run_name
        try:
            float(args[-1])
        except ValueError:
            self.set_run_name(args[-1])
            del args[-1]
        except IndexError:
            self.help_refine()
            raise self.InvalidCmd('require_precision argument is require for refine cmd')

    
        if not self.run_name:
            raise self.InvalidCmd('No run_name currently define. Impossible to run refine')

        if len(args) > 2:
            self.help_refine()
            raise self.InvalidCmd('Too many argument for refine command')
        else:
            try:
                [float(arg) for arg in args]
            except ValueError:         
                self.help_refine()    
                raise self.InvalidCmd('refine arguments are suppose to be number')
            
        return True
    
    def check_combine_events(self, arg):
        """ Check the argument for the combine events command """
        
        if len(arg) >1:
            self.help_combine_events()
            raise self.InvalidCmd('Too many argument for combine_events command')
        
        if len(arg):
            self.set_run_name(arg[0])
        
        return True
    
    def check_pythia(self, arg):
        """Check the argument for pythia command
        syntax: pythia [NAME] 
        Note that other option are already remove at this point
        """
               
     
        if len(arg) == 0 and not self.run_name:
            self.help_pythia()
            raise self.InvalidCmd('No run name currently define. Please add this information.')             
        
        if len(arg) == 1:
            if arg[0] != self.run_name and\
             not os.path.exists(pjoin(self.me_dir,'Events','%s_unweighted_events.lhe.gz'
                                                                     % arg[0])):
                raise self.InvalidCmd('No events file corresponding to %s run. '% arg[0])
            self.set_run_name(arg[0])
        
        
        input_file = pjoin(self.me_dir,'Events', '%s_unweighted_events.lhe.gz' % self.run_name)
        output_file = pjoin(self.me_dir, 'Events', 'unweighted_events.lhe')
        os.system('gunzip -c %s > %s' % (input_file, output_file))
            
        if  not os.path.exists(pjoin(self.me_dir,'Events','%s_unweighted_events.lhe.gz' % self.run_name)):
            raise self.InvalidCmd('No events file corresponding to %s run. '% self.run_name)

        # If not pythia-pgs path
        if not self.configuration['pythia-pgs_path']:
            logger.info('Retry to read configuration file to find pythia-pgs path')
            self.set_configuration()
            
        if not self.configuration['pythia-pgs_path'] or not \
            os.path.exists(pjoin(self.configuration['pythia-pgs_path'],'src')):
            error_msg = 'No pythia-pgs path correctly set.'
            error_msg += 'Please use the set command to define the path and retry.'
            error_msg += 'You can also define it in the configuration file.'
            raise self.InvalidCmd(error_msg)
    
    def check_plot(self, args):
        """Check the argument for the plot command
        plot run_name modes"""

        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']
        
        if not madir or not td:
            logger.info('Retry to read configuration file to find madanalysis/td')
            self.set_configuration()

        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']        
        
        if not madir:
            error_msg = 'No Madanalysis path correctly set.'
            error_msg += 'Please use the set command to define the path and retry.'
            error_msg += 'You can also define it in the configuration file.'
            raise self.InvalidCmd(error_msg)  
        if not  td:
            error_msg = 'No path to td directory correctly set.'
            error_msg += 'Please use the set command to define the path and retry.'
            error_msg += 'You can also define it in the configuration file.'
            raise self.InvalidCmd(error_msg)  
                     
        if len(args) == 0:
            if not hasattr(self, 'run_name'):
                self.help_plot()
                raise self.InvalidCmd('No run name currently define. Please add this information.')             
            args.append('all')
            return
                
        if args[0] not in self._plot_mode:
            self.set_run_name(args[0])
            del args[0]
            if len(args) == 0:
                args.append('all')
        elif not self.run_name:
            self.help_plot()
            raise self.InvalidCmd('No run name currently define. Please add this information.')                             
        
        for arg in args:
            if arg not in self._plot_mode and arg != self.run_name:
                 self.help_plot()
                 raise self.InvalidCmd('unknown options %s' % arg)        
    
    def check_pgs(self, arg):
        """Check the argument for pythia command
        syntax: pgs [NAME] 
        Note that other option are already remove at this point
        """
        
        # If not pythia-pgs path
        if not self.configuration['pythia-pgs_path']:
            logger.info('Retry to read configuration file to find pythia-pgs path')
            self.set_configuration()
      
        if not self.configuration['pythia-pgs_path'] or not \
            os.path.exists(pjoin(self.configuration['pythia-pgs_path'],'src')):
            error_msg = 'No pythia-pgs path correctly set.'
            error_msg += 'Please use the set command to define the path and retry.'
            error_msg += 'You can also define it in the configuration file.'
            raise self.InvalidCmd(error_msg)  
                  
        if len(arg) == 0 and not self.run_name:
            self.help_pgs()
            raise self.InvalidCmd('No run name currently define. Please add this information.')             
        
        if len(arg) == 1 and self.run_name == arg[0]:
            arg.pop(0)
        
        if not len(arg) and \
           not os.path.exists(pjoin(self.me_dir,'Events','pythia_events.hep')):
            self.help_pgs()
            raise self.InvalidCmd('''No file file pythia_events.hep currently available
            Please specify a valid run_name''')
                              
        if len(arg) == 1:
            self.set_run_name(arg[0])
            if  not os.path.exists(pjoin(self.me_dir,'Events','%s_pythia_events.hep.gz' % self.run_name)):
                raise self.InvalidCmd('No events file corresponding to %s run. '% self.run_name)
            else:
                input_file = pjoin(self.me_dir,'Events', '%s_pythia_events.hep.gz' % self.run_name)
                output_file = pjoin(self.me_dir, 'Events', 'pythia_events.hep')
                os.system('gunzip -c %s > %s' % (input_file, output_file))

    def check_delphes(self, arg):
        """Check the argument for pythia command
        syntax: delphes [NAME] 
        Note that other option are already remove at this point
        """
        
        # If not pythia-pgs path
        if not self.configuration['delphes_path']:
            logger.info('Retry to read configuration file to find delphes path')
            self.set_configuration()
      
        if not self.configuration['delphes_path']:
            error_msg = 'No delphes path correctly set.'
            error_msg += 'Please use the set command to define the path and retry.'
            error_msg += 'You can also define it in the configuration file.'
            raise self.InvalidCmd(error_msg)  
                  
        if len(arg) == 0 and not self.run_name:
            self.help_delphes()
            raise self.InvalidCmd('No run name currently define. Please add this information.')             
        
        if len(arg) == 1 and self.run_name == arg[0]:
            arg.pop(0)
        
        if not len(arg) and \
           not os.path.exists(pjoin(self.me_dir,'Events','pythia_events.hep')):
            self.help_pgs()
            raise self.InvalidCmd('''No file file pythia_events.hep currently available
            Please specify a valid run_name''')
                              
        if len(arg) == 1:
            self.set_run_name(arg[0])
            if  not os.path.exists(pjoin(self.me_dir,'Events','%s_pythia_events.hep.gz' % self.run_name)):
                raise self.InvalidCmd('No events file corresponding to %s run. '% self.run_name)
            else:
                input_file = pjoin(self.me_dir,'Events', '%s_pythia_events.hep.gz' % self.run_name)
                output_file = pjoin(self.me_dir, 'Events', 'pythia_events.hep')
                os.system('gunzip -c %s > %s' % (input_file, output_file))



    def check_import(self, args):
        """check the validity of line"""
         
        if not args or args[0] not in ['command']:
            self.help_import()
            raise self.InvalidCmd('wrong \"import\" format')
        
        if not len(args) == 2 or not os.path.exists(args[1]):
            raise self.InvalidCmd('PATH is mandatory for import command\n')
        

#===============================================================================
# CompleteForCmd
#===============================================================================
class CompleteForCmd(CheckValidForCmd):
    """ The Series of help routine for the MadGraphCmd"""
    
    def complete_history(self, text, line, begidx, endidx):
        "Complete the history command"

        args = self.split_arg(line[0:begidx])

        # Directory continuation
        if args[-1].endswith(os.path.sep):
            return self.path_completion(text,
                                        os.path.join('.',*[a for a in args \
                                                    if a.endswith(os.path.sep)]))

        if len(args) == 1:
            return self.path_completion(text)
        
    def complete_open(self, text, line, begidx, endidx): 
        """ complete the open command """

        args = self.split_arg(line[0:begidx])
        
        # Directory continuation
        if os.path.sep in args[-1] + text:
            return self.path_completion(text,
                                    os.path.join('.',*[a for a in args if \
                                                      a.endswith(os.path.sep)]))

        possibility = []
        if self.me_dir:
            path = self.me_dir
            possibility = ['index.html']
            if os.path.isfile(os.path.join(path,'README')):
                possibility.append('README')
            if os.path.isdir(os.path.join(path,'Cards')):
                possibility += [f for f in os.listdir(os.path.join(path,'Cards')) 
                                    if f.endswith('.dat')]
            if os.path.isdir(os.path.join(path,'HTML')):
                possibility += [f for f in os.listdir(os.path.join(path,'HTML')) 
                                  if f.endswith('.html') and 'default' not in f]
        else:
            possibility.extend(['./','../'])
        if os.path.exists('ME5_debug'):
            possibility.append('ME5_debug')
        if os.path.exists('MG5_debug'):
            possibility.append('MG5_debug')
        return self.list_completion(text, possibility)
    
    def complete_set(self, text, line, begidx, endidx):
        "Complete the set command"

        args = self.split_arg(line[0:begidx])

        # Format
        if len(args) == 1:
            return self.list_completion(text, self._set_options)

        if len(args) == 2:
            if args[1] == 'stdout_level':
                return self.list_completion(text, ['DEBUG','INFO','WARNING','ERROR','CRITICAL'])
    
    def complete_survey(self, text, line, begidx, endidx):
        """ Complete the survey command """
        
        if line.endswith('nb_core=') and not text:
            import multiprocessing
            max = multiprocessing.cpu_count()
            return [str(i) for i in range(2,max+1)]
            
        return  self.list_completion(text, self._run_options, line)
    
    complete_refine = complete_survey
    complete_combine_events = complete_survey
    complete_generate_events = complete_survey
    
    def complete_multi_run(self, text, line, begidx, endidx):
        """complete multi run command"""
        
        args = self.split_arg(line[0:begidx])
        if len(args) == 1:
            data = [str(i) for i in range(0,20)]
            return  self.list_completion(text, data, line)
        
        if line.endswith('nb_core=') and not text:
            import multiprocessing
            max = multiprocessing.cpu_count()
            return [str(i) for i in range(2,max+1)]
            
        return  self.list_completion(text, self._run_options, line)    
    
    def complete_plot(self, text, line, begidx, endidx):
        """ Complete the plot command """
        
        args = self.split_arg(line[0:begidx])
        if len(args) > 1:
            return self.list_completion(text, self._plot_mode)
        else:
            return self.list_completion(text, self._plot_mode + self.results.keys())
        
        
        
    def complete_pythia(self,text, line, begidx, endidx):
        "Complete the pythia command"
        
        args = cmd.Cmd.split_arg(line[0:begidx])
        if len(args) == 1:
            #return valid run_name
            data = glob.glob(pjoin(self.me_dir, 'Events', '*_unweighted_events.lhe.gz'))
            data = [n.rsplit('/',1)[1][:-25] for n in data]
            tmp1 =  self.list_completion(text, data)
            if not self.run_name:
                return tmp1
            else:
                tmp2 = self.list_completion(text, self._run_options + ['-f', '--no_default'], line)
                return tmp1 + tmp2
        else:
            return self.list_completion(text, self._run_options + ['-f', '--no_default'], line)
        
    def complete_pgs(self,text, line, begidx, endidx):
        "Complete the pythia command"
        
        args = cmd.Cmd.split_arg(line[0:begidx]) 
                
        if len(args) == 1:
            #return valid run_name
            data = glob.glob(pjoin(self.me_dir, 'Events', '*_pythia_events.hep.gz'))
            data = [n.rsplit('/',1)[1][:-21] for n in data]
            tmp1 =  self.list_completion(text, data)
            if not self.run_name:
                return tmp1
            else:
                tmp2 = self.list_completion(text, self._run_options + ['-f', '--no_default'], line)
                return tmp1 + tmp2        
        else:
            return self.list_completion(text, self._run_options + ['-f', '--no_default'], line)
    
    complete_delphes = complete_pgs        
        
#===============================================================================
# MadEventCmd
#===============================================================================
class MadEventCmd(CmdExtended, HelpToCmd, CompleteForCmd):
    """The command line processor of MadGraph"""    
    
    # Truth values
    true = ['T','.true.',True,'true']
    # Options and formats available
    _run_options = ['--cluster','--multicore','--nb_core=','--nb_core=2', '-c', '-m']
    _set_options = ['stdout_level','fortran_compiler']
    _plot_mode = ['all', 'parton','pythia','pgs','delphes']
    # Variables to store object information
    true = ['T','.true.',True,'true', 1, '1']
    web = False
    prompt = 'MGME5>'
    cluster_mode = 0
    queue  = 'madgraph'
    nb_core = None
    
    ############################################################################
    def __init__(self, me_dir = None, *completekey, **stdin):
        """ add information to the cmd """

        CmdExtended.__init__(self, *completekey, **stdin)
        
        # Define current MadEvent directory
        if me_dir is None and MADEVENT:
            me_dir = root_path        
        self.me_dir = me_dir

        # usefull shortcut
        self.status = pjoin(self.me_dir, 'status')
        self.error =  pjoin(self.me_dir, 'error')
        self.dirbin = pjoin(self.me_dir, 'bin', 'internal')
        
        # Check that the directory is not currently running
        if os.path.exists(pjoin(me_dir,'RunWeb')): 
            logger.critical('''Another instance of madevent is currently running.
            Please wait that all instance of madevent are closed. If this message
            is an error in itself, you can suppress the files %s.''' % pjoin(me_dir,'RunWeb'))
            sys.exit()
        else:
            os.system('touch %s' % pjoin(me_dir,'RunWeb'))
            os.system('%s/gen_cardhtml-pl' % (self.dirbin))
      
        self.to_store = []
        self.run_name = None
        # Load the configuration file
        self.set_configuration()
        self.open_crossx = True # allow to open automatically the web browser

        if self.web:
            os.system('touch Online')

        
        # load the current status of the directory
        if os.path.exists(pjoin(self.me_dir,'HTML','results.pkl')):
            self.results = save_load_object.load_from_file(pjoin(self.me_dir,'HTML','results.pkl'))
        else:
            model = self.find_model_name()
            process = self.process # define in find_model_name
            self.results = gen_crossxhtml.AllResults(model, process, self.me_dir)
        self.results.def_web_mode(self.web)
        
        self.configured = 0 # time for reading the card
        self._options = {} # for compatibility with extended_cmd
        
    ############################################################################    
    def split_arg(self, line):
        """split argument and remove run_options"""
        
        args = CmdExtended.split_arg(line)
        
        for arg in args[:]:
            if not arg.startswith('-'):
                continue
            elif arg == '-c':
                self.cluster_mode = 1
            elif arg == '-m':
                self.cluster_mode = 2
            elif arg == '-f':
                continue
            elif not arg.startswith('--'):
                raise self.InvalidCmd('%s argument cannot start with - symbol' % arg)
            elif arg.startswith('--cluster'):
                self.cluster_mode = 1
            elif arg.startswith('--multicore'):
                self.cluster_mode = 2
            elif arg.startswith('--nb_core'):
                self.cluster_mode = 2
                self.nb_core = int(arg.split('=',1)[1])
            elif arg.startswith('--web'):
                self.web = True
                self.results.def_web_mode(True)
            else:
                continue
            args.remove(arg)
        
        if self.cluster_mode == 2 and not self.nb_core:
            import multiprocessing
            self.nb_core = multiprocessing.cpu_count()
            
        if self.cluster_mode == 1 and not hasattr(self, 'cluster'):
            cluster_name = self.configuration['cluster_type']
            self.cluster = cluster.from_name[cluster_name]()
        return args
                    
    ############################################################################            
    def check_output_type(self, path):
        """ Check that the output path is a valid madevent directory """
        
        bin_path = os.path.join(path,'bin')
        if os.path.isfile(os.path.join(bin_path,'generate_events')):
            return True
        else: 
            return False
        
    ############################################################################
    def set_configuration(self, config_path=None):
        """ assign all configuration variable from file 
            ./Cards/mg5_configuration.txt. assign to default if not define """
            
        self.configuration = {'pythia8_path': './pythia8',
                              'pythia-pgs_path': '../pythia-pgs',
                              'delphes_path': '../Delphes',
                              'madanalysis_path': '../MadAnalysis',
                              'exrootanalysis_path': '../ExRootAnalysis',
                              'td_path': '../',
                              'web_browser':None,
                              'eps_viewer':None,
                              'text_editor':None,
                              'fortran_compiler':None,
                              'cluster_mode':'pbs'}
        
        if not config_path:
            try:
                config_file = open(os.path.join(os.environ['HOME'],'.mg5','mg5_config'))
            except:
                if self.me_dir:
                    config_file = open(os.path.relpath(
                          os.path.join(self.dirbin, 'me5_configuration.txt')))
                    main = self.me_dir
                elif not MADEVENT:
                    config_file = open(os.path.relpath(
                          os.path.join(MG5DIR, 'input', 'mg5_configuration.txt')))                    
                    main = MG5DIR
        else:
            config_file = open(config_path)
            if self.me_dir:
                main = self.me_dir
            else:
                main = MG5DIR

        # read the file and extract information
        logger.info('load configuration from %s ' % config_file.name)
        for line in config_file:
            if '#' in line:
                line = line.split('#',1)[0]
            line = line.replace('\n','').replace('\r\n','')
            try:
                name, value = line.split('=')
            except ValueError:
                pass
            else:
                name = name.strip()
                value = value.strip()
                self.configuration[name] = value
                if value.lower() == "none":
                    self.configuration[name] = None

        # Treat each expected input
        # delphes/pythia/... path
        for key in self.configuration:
            if key.endswith('path'):
                path = os.path.join(self.me_dir, self.configuration[key])
                if os.path.isdir(path):
                    self.configuration[key] = os.path.realpath(path)
                    continue
                if os.path.isdir(self.configuration[key]):
                    self.configuration[key] = os.path.realpath(self.configuration[key])
                    continue
                else:
                    self.configuration[key] = ''
            elif key.startswith('cluster'):
                pass
            elif key not in ['text_editor','eps_viewer','web_browser']:
                # Default: try to set parameter
                try:
                    self.do_set("%s %s" % (key, self.configuration[key]))
                except self.InvalidCmd:
                    logger.warning("Option %s from config file not understood" \
                                   % key)
        
        # Configure the way to open a file:
        misc.open_file.configure(self.configuration)
          
        return self.configuration
  
    ############################################################################
    def do_import(self, line):
        """Import files with external formats"""

        args = self.split_arg(line)
        # Check argument's validity
        self.check_import(args)
        # Remove previous imports, generations and outputs from history
        self.clean_history()
        
        # Execute the card
        self.import_command_file(args[1])  
  
    ############################################################################ 
    def do_open(self, line):
        """Open a text file/ eps file / html file"""
        
        args = self.split_arg(line)
        # Check Argument validity and modify argument to be the real path
        self.check_open(args)
        file_path = args[0]
        
        misc.open_file(file_path)

    ############################################################################
    def do_set(self, line):
        """Set an option, which will be default for coming generations/outputs
        """

        args = self.split_arg(line) 
        # Check the validity of the arguments
        self.check_set(args)

        if args[0] == "stdout_level":
            logging.root.setLevel(eval('logging.' + args[1]))
            logging.getLogger('madgraph').setLevel(eval('logging.' + args[1]))
            logger.info('set output information to level: %s' % args[1])
        elif args[0] == "fortran_compiler":
            self.configuration['fortran_compiler'] = args[1] 
 
 
    ############################################################################
    def update_status(self, status, level, makehtml=True):
        """ update the index status """

        if isinstance(status, str):
            if '<br>' not  in status:
                logger.info(status)
        else:
            logger.info(' Idle: %s Running: %s Finish: %s' % status)
        self.results.update(status, level,makehtml=makehtml)
        
    ############################################################################      
    def do_generate_events(self, line):
        """ launch the full chain """
        
        args = self.split_arg(line)
        # Check argument's validity
        self.check_survey(args, cmd='generate_events')
        logger.info('Generating %s events with run name %s' %
                                      (self.run_card['nevents'], self.run_name))
              
        self.exec_cmd('survey %s' % line, postcmd=False)
        if not self.run_card['gridpack'] in self.true:        
            nb_event = self.run_card['nevents']
            self.exec_cmd('refine %s' % nb_event, postcmd=False)
            self.exec_cmd('refine %s' % nb_event, postcmd=False)
        
        self.exec_cmd('combine_events', postcmd=False)
        if not self.run_card['gridpack'] in self.true:
            self.exec_cmd('pythia --no_default', postcmd=False, printcmd=False)
            if os.path.exists(pjoin(self.me_dir,'Events','pythia_events.hep')):
                self.exec_cmd('pgs --no_default', postcmd=False, printcmd=False)
                self.exec_cmd('delphes --no_default', postcmd=False, printcmd=False)
        
        if self.run_card['gridpack'] in self.true:
            self.update_status('Creating gridpack', level='parton')
            os.system("sed -i.bak \"s/\s*.false.*=.*GridRun/  .true.  =  GridRun/g\" %s/Cards/grid_card.dat"\
                      % self.me_dir)
            subprocess.call(['./bin/internal/restore_data', self.run_name],
                            cwd=self.me_dir)
            subprocess.call(['./bin/internal/store4grid', 'default'],
                            cwd=self.me_dir)
            subprocess.call(['./bin/internal/clean'], cwd=self.me_dir)
            misc.compile(['gridpack.tar.gz'], cwd=self.me_dir)
            files.mv(pjoin(self.me_dir, 'gridpack.tar.gz'), 
                    pjoin(self.me_dir, '%s_gridpack.tar.gz' % self.run_name))
            self.update_status('gridpack created', level='gridpack')

        self.store_result()
    
    ############################################################################
    def do_multi_run(self, line):
        
        args = self.split_arg(line)
        # Check argument's validity
        self.check_multi_run(args)
        
        main_name = self.run_name
        nb_run = args.pop(0)
        crossoversig = 0
        inv_sq_err = 0
        for i in range(nb_run):
            self.exec_cmd('generate_events %s_%s' % (main_name, i), postcmd=False)
            # Update collected value
            if self.results[main_name]['nb_event']:
                self.results[main_name]['nb_event'] += int(self.results[self.run_name]['nb_event'])  
            else:
                self.results[main_name]['nb_event'] = int(self.results[self.run_name]['nb_event'])  
            cross = self.results[self.run_name]['cross']
            error = self.results[self.run_name]['error'] + 1e-99
            crossoversig+=cross/error**2
            inv_sq_err+=1.0/error**2
            self.results[main_name]['cross'] = crossoversig/inv_sq_err
            self.results[main_name]['error'] = math.sqrt(1.0/inv_sq_err)            
        
        self.run_name = main_name
        self.results.def_current(main_name)
        self.update_status("Merging LHE files", level='parton')
        os.system('%(bin)s/merge.pl %(event)s/%(name)s_*_unweighted_events.lhe.gz %(event)s/%(name)s_unweighted_events.lhe.gz %(event)s/%(name)s_banner.txt' 
                  % {'bin': self.dirbin, 'event': pjoin(self.me_dir,'Events'),
                     'name': self.run_name})

        


        eradir = self.configuration['exrootanalysis_path']
        if misc.is_executable(pjoin(eradir,'ExRootLHEFConverter')):
            self.update_status("Create Root file", level='parton')
            os.system('gunzip %s/%s_unweighted_events.lhe.gz' % 
                                  (pjoin(self.me_dir,'Events'), self.run_name))
            self.create_root_file('%s_unweighted_events.lhe' % self.run_name,
                                  '%s_unweighted_events.root' % self.run_name)
            
        
        self.create_plot('parton', '%s/%s_unweighted_events.lhe' %
                         (pjoin(self.me_dir, 'Events'),self.run_name))
        
        os.system('gzip %s/%s_unweighted_events.lhe' % 
                                  (pjoin(self.me_dir, 'Events'), self.run_name))

        self.update_status('', level=parton)
            
    ############################################################################      
    def do_survey(self, line):
        """ launch survey for the current process """
                
        args = self.split_arg(line)
        # Check argument's validity
        self.check_survey(args)
        # initialize / remove lhapdf mode
        self.update_status('compile directory', level=None)
        self.configure_directory()

        if self.cluster_mode:
            logger.info('Creating Jobs')

        # treat random number
        self.update_random()
        self.save_random()
        if self.open_crossx:
            misc.open_file(os.path.join(self.me_dir, 'HTML', 'crossx.html'))
            self.open_crossx = False
        logger.info('Working on SubProcesses')
        for subdir in open(pjoin(self.me_dir, 'SubProcesses', 'subproc.mg')):
            subdir = subdir.strip()
            Pdir = pjoin(self.me_dir, 'SubProcesses',subdir)
            logger.info('    %s ' % subdir)
            # clean previous run
            for match in glob.glob(pjoin(Pdir, '*ajob*')):
                if os.path.basename(match)[:4] in ['ajob', 'wait', 'run.', 'done']:
                    os.remove(pjoin(Pdir, match))
            
            #compile gensym
            misc.compile(['gensym'], cwd=Pdir)
            if not os.path.exists(pjoin(Pdir, 'gensym')):
                raise MadEventError, 'Error make gensym not successful'

            # Launch gensym
            p = subprocess.Popen(['./gensym'], stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, cwd=Pdir)
            (stdout, stderr) = p.communicate()
            if not os.path.exists(pjoin(Pdir, 'ajob1')) or p.returncode:
                logger.critical(stdout)
                raise MadEventError, 'Error gensym run not successful'
            #
            os.system("chmod +x %s/ajob*" % Pdir)
        
            misc.compile(['madevent'], cwd=Pdir)

            for job in glob.glob(pjoin(Pdir,'ajob*')):
                job = os.path.basename(job)
                os.system('touch %s/wait.%s' %(Pdir,job))
                self.launch_job('./%s' % job, cwd=Pdir)
                if os.path.exists(pjoin(self.me_dir,'error')):
                    self.monitor()
                    self.update_status('Error detected in survey', None)
                    raise MadEventError, 'Error detected Stop running'
        self.monitor()
        self.update_status('End survey', 'parton', makehtml=False)

    ############################################################################      
    def do_refine(self, line):
        """ launch survey for the current process """

        args = self.split_arg(line)
        # Check argument's validity
        self.check_refine(args)
        
        precision = args[0]
        if len(args) == 2:
            max_process = args[1]
        else:
             max_process = 5

        # initialize / remove lhapdf mode
        self.configure_directory()

        if self.cluster_mode:
            logger.info('Creating Jobs')
        self.update_status('Refine results to %s' % precision, level=None)
        logger.info("Using random number seed offset = %s" % self.random)

        for subdir in open(pjoin(self.me_dir, 'SubProcesses', 'subproc.mg')):
            subdir = subdir.strip()
            Pdir = pjoin(self.me_dir, 'SubProcesses',subdir)
            bindir = pjoin(os.path.relpath(self.dirbin, Pdir))
                           
            logger.info('    %s ' % subdir)
            # clean previous run
            for match in glob.glob(pjoin(Pdir, '*ajob*')):
                if os.path.basename(match)[:4] in ['ajob', 'wait', 'run.', 'done']:
                    os.remove(pjoin(Pdir, match))
            
            devnull = os.open(os.devnull, os.O_RDWR)
            proc = subprocess.Popen([pjoin(bindir, 'gen_ximprove')],
                                    stdout=devnull,
                                    stdin=subprocess.PIPE,
                                    cwd=Pdir)
            proc.communicate('%s %s T\n' % (precision, max_process))
            #proc.wait()
            if os.path.exists(pjoin(Pdir, 'ajob1')):
                misc.compile(['madevent'], cwd=Pdir)
                #
                os.system("chmod +x %s/ajob*" % Pdir)            
                for job in glob.glob(pjoin(Pdir,'ajob*')):
                    job = os.path.basename(job)
                    os.system('touch %s/wait.%s' %(Pdir, job))
                    self.launch_job('./%s' % job, cwd=Pdir)
        self.monitor()
        
        self.update_status("Combining runs", level='parton')
        try:
            os.remove(pjoin(Pdir, 'combine_runs.log'))
        except:
            pass
        
        bindir = pjoin(os.path.relpath(self.dirbin, pjoin(self.me_dir,'SubProcesses')))
        subprocess.call([pjoin(bindir, 'combine_runs')], 
                                          cwd=pjoin(self.me_dir,'SubProcesses'),
                                          stdout=devnull)
        
        subprocess.call([pjoin(self.dirbin, 'sumall')], 
                                         cwd=pjoin(self.me_dir,'SubProcesses'),
                                         stdout=devnull)
        self.update_status('finish refine', 'parton', makehtml=False)
        
    ############################################################################ 
    def do_combine_events(self, line):
        """Launch combine events"""

        args = self.split_arg(line)
        # Check argument's validity
        self.check_combine_events(args)


        self.update_status('Combining Events', level='parton')
        try:
            os.remove('/tmp/combine.log')
        except:
            pass
        if self.cluster_mode == 1:
            out = self.cluster.launch_and_wait('../bin/internal/run_combine', 
                                        cwd=pjoin(self.me_dir,'SubProcesses'),
                                        stdout=open(pjoin(self.me_dir,'SubProcesses', 'combine.log'),'w'))
        else:
            out = subprocess.call(['../bin/internal/run_combine'],
                         cwd=pjoin(self.me_dir,'SubProcesses'), 
                         stdout=open(pjoin(self.me_dir,'SubProcesses','combine.log'),'w'))
            
        output = open(pjoin(self.me_dir,'SubProcesses','combine.log')).read()
        # Store the number of unweighted events for the results object
        pat = re.compile(r'''\s*Unweighting selected\s*(\d+)\s*events''',re.MULTILINE)
        if output:
            nb_event = pat.search(output).groups()[0]
            self.results.add_detail('nb_event', nb_event)
        
        subprocess.call(['%s/put_banner' % self.dirbin, 'events.lhe'],
                            cwd=pjoin(self.me_dir, 'Events'))
        subprocess.call(['%s/put_banner'% self.dirbin, 'unweighted_events.lhe'],
                            cwd=pjoin(self.me_dir, 'Events'))
        
        if os.path.exists(pjoin(self.me_dir, 'Events', 'unweighted_events.lhe')):
            subprocess.call(['%s/extract_banner-pl' % self.dirbin, 
                             'unweighted_events.lhe', 'banner.txt'],
                            cwd=pjoin(self.me_dir, 'Events'))
        
        eradir = self.configuration['exrootanalysis_path']
        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']
        if misc.is_executable(pjoin(eradir,'ExRootLHEFConverter'))  and\
           os.path.exists(pjoin(self.me_dir, 'Events', 'unweighted_events.lhe')):
                self.create_root_file()
        
        self.create_plot()
            
        #
        # STORE
        #
        self.update_status('Storing parton level results', level='parton')
        subprocess.call(['%s/store' % self.dirbin, self.run_name],
                            cwd=pjoin(self.me_dir, 'Events'))
        #shutil.copy(pjoin(self.me_dir, 'Events', self.run_name+'_banner.txt'),
        #            pjoin(self.me_dir, 'Events', 'banner.txt')) 

        self.update_status('End Parton', level='parton')
        
        



    ############################################################################      
    def do_pythia(self, line):
        """launch pythia"""
        
        args = self.split_arg(line)
        # Check argument's validity
        if '-f' in args:
            force = True
            args.remove('-f')
        else:
            force = False
        if '--no_default' in args:
            no_default = True
            args.remove('--no_default')
        else:
            no_default = False
        self.check_pythia(args) 
        # initialize / remove lhapdf mode        
        self.configure_directory()
        
        
        # Check that the pythia_card exists. If not copy the default and
        # ask for edition of the card.
        if not os.path.exists(pjoin(self.me_dir, 'Cards', 'pythia_card.dat')):
            if no_default:
                logger.info('No pythia_card detected, so not run pythia')
                return
            
            files.cp(pjoin(self.me_dir, 'Cards', 'pythia_card_default.dat'),
                     pjoin(self.me_dir, 'Cards', 'pythia_card.dat'))
            logger.info('No pythia card found. Take the default one.')
            
            if not force:
                answer = self.ask('Do you want to edit this card?','n', ['y','n'],
                          timeout=20)
            else: 
                answer = 'n'
                
            if answer == 'y':
                misc.open_file(pjoin(self.me_dir, 'Cards', 'pythia_card.dat'))
        
        pythia_src = pjoin(self.configuration['pythia-pgs_path'],'src')
        
        self.update_status('Running Pythia', 'pythia')
        try:
            os.remove(pjoin(self.me_dir,'Events','pythia.done'))
        except:
            pass
        
        ## LAUNCHING PYTHIA
        pythia_log = open(pjoin(self.me_dir, 'Events', '%s_pythia.log' % self.run_name), 'w')
        if self.cluster_mode == 1:
            self.cluster.launch_and_wait('../bin/internal/run_pythia', 
                        argument= [pythia_src], stdout= pythia_log,
                        stderr=subprocess.STDOUT,
                        cwd=pjoin(self.me_dir,'Events'))
        else:
            subprocess.call(['../bin/internal/run_pythia', pythia_src],
                           stdout=pythia_log,
                           stderr=subprocess.STDOUT,
                           cwd=pjoin(self.me_dir,'Events'))

        if not os.path.exists(pjoin(self.me_dir,'Events','pythia.done')):
            logger.warning('Fail to produce pythia output')
            return
        else:
            os.remove(pjoin(self.me_dir,'Events','pythia.done'))
        
        self.to_store.append('pythia')
        
        # Find the matched cross-section
        if int(self.run_card['ickkw']):    
            pythia_log = open(pjoin(self.me_dir,'Events', '%s_pythia.log' % self.run_name))
            cs_info = misc.get_last_line(pythia_log)
            # line should be of type: Cross section (pb):    1840.20000000006 
            cs_info = cs_info.split(':')[1]
            self.results.add_detail('cross_pythia', cs_info)
        
        pydir = pjoin(self.configuration['pythia-pgs_path'], 'src')
        eradir = self.configuration['exrootanalysis_path']
        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']
        
        # Update the banner with the pythia card
        banner_path = pjoin(self.me_dir,'Events',self.run_name + '_banner.txt')
        banner = open(banner_path, 'a')
        banner.writelines('\n<MGPythiaCard>\n')
        banner.writelines(open(pjoin(self.me_dir, 'Cards','pythia_card.dat')).read())
        banner.writelines('\n</MGPythiaCard>\n')
        banner.close()
        
        # Creating LHE file
        if misc.is_executable(pjoin(pydir, 'hep2lhe')):
            self.update_status('Creating Pythia LHE File', level='pythia')
            # Write the banner to the LHE file
            out = open(pjoin(self.me_dir,'Events','pythia_events.lhe'), 'w')
            #out.writelines('<LesHouchesEvents version=\"1.0\">\n')    
            out.writelines('<!--\n')
            out.writelines('# Warning! Never use this file for detector studies!\n')
            out.writelines('-->\n<!--\n')
            out.writelines(open(banner_path).read())
            out.writelines('\n-->\n')
            out.close()
            
            if self.cluster_mode == 1:
                self.cluster.launch_and_wait(self.dirbin+'/run_hep2lhe', 
                                         argument= [pydir],
                                        cwd=pjoin(self.me_dir,'Events'))
            else:
                subprocess.call([self.dirbin+'/run_hep2lhe', pydir],
                             cwd=pjoin(self.me_dir,'Events'))
                
            # Creating ROOT file
            if misc.is_executable(pjoin(eradir, 'ExRootLHEFConverter')):
                self.update_status('Creating Pythia LHE Root File', level='pythia')
                subprocess.call([eradir+'/ExRootLHEFConverter', 
                             'pythia_events.lhe', '%s_pythia_lhe_events.root' % self.run_name],
                            cwd=pjoin(self.me_dir,'Events')) 
            

        if int(self.run_card['ickkw']):
            self.update_status('Create matching plots for Pythia', level='pythia')
            subprocess.call([self.dirbin+'/create_matching_plots.sh', self.run_name],
                            stdout = os.open(os.devnull, os.O_RDWR),
                            cwd=pjoin(self.me_dir,'Events'))
            #Clean output
            subprocess.call(['gzip','-f','events.tree'], 
                                                cwd=pjoin(self.me_dir,'Events'))          
            files.mv(pjoin(self.me_dir,'Events','events.tree.gz'), 
                     pjoin(self.me_dir,'Events',self.run_name +'_events.tree.gz'))
            subprocess.call(['gzip','-f','beforeveto.tree'], 
                                                cwd=pjoin(self.me_dir,'Events'))
            files.mv(pjoin(self.me_dir,'Events','beforeveto.tree.gz'), 
                     pjoin(self.me_dir,'Events',self.run_name +'_beforeveto.tree.gz'))
            files.mv(pjoin(self.me_dir,'Events','xsecs.tree'), 
                     pjoin(self.me_dir,'Events',self.run_name +'_xsecs.tree'))            
             

        # Plot for pythia
        self.create_plot('Pythia')

        if os.path.exists(pjoin(self.me_dir,'Events','pythia_events.lhe')):
            shutil.move(pjoin(self.me_dir,'Events','pythia_events.lhe'),
            pjoin(self.me_dir,'Events','%s_pythia_events.lhe' % self.run_name))
            os.system('gzip -f %s' % pjoin(self.me_dir,'Events',
                                        '%s_pythia_events.lhe' % self.run_name))      

        
        self.update_status('finish', level='pythia', makehtml=False)

    def do_plot(self, line):
        """Create the plot for a given run"""

        # Since in principle, all plot are already done automaticaly
        self.store_result()
        args = self.split_arg(line)
        # Check argument's validity
        self.check_plot(args)
        
        if any([arg in ['all','parton'] for arg in args]):
            filename = pjoin(self.me_dir, 'Events','%s_unweighted_events.lhe' % self.run_name)
            if os.path.exists(filename+'.gz'):
                os.system('gunzip -f %s' % (filename+'.gz') )
            if  os.path.exists(filename):
                shutil.move(filename, pjoin(self.me_dir, 'Events','unweighted_events.lhe'))
                self.create_plot('parton')
                shutil.move(pjoin(self.me_dir, 'Events','unweighted_events.lhe'), filename)
                os.system('gzip -f %s' % filename)
            else:
                logger.info('No valid files for partonic plot') 
                
        if any([arg in ['all','pythia'] for arg in args]):
            filename = pjoin(self.me_dir, 'Events','%s_pythia_events.lhe' % self.run_name)
            if os.path.exists(filename+'.gz'):
                os.system('gunzip -f %s' % (filename+'.gz') )
            if  os.path.exists(filename):
                shutil.move(filename, pjoin(self.me_dir, 'Events','pythia_events.lhe'))
                self.create_plot('pythia')
                shutil.move(pjoin(self.me_dir, 'Events','pythia_events.lhe'), filename)
                os.system('gzip -f %s' % filename)                
            else:
                logger.info('No valid files for pythia plot')
                    
        if any([arg in ['all','pgs'] for arg in args]):
            filename = pjoin(self.me_dir, 'Events','%s_pgs_events.lhco' % self.run_name)
            if os.path.exists(filename+'.gz'):
                os.system('gunzip -f %s' % (filename+'.gz') )
            if  os.path.exists(filename):
                #shutil.move(filename, pjoin(self.me_dir, 'Events','pgs_events.lhco'))
                self.create_plot('pgs')
                #shutil.move(pjoin(self.me_dir, 'Events','pgs_events.lhco'), filename)
                os.system('gzip -f %s' % filename)                
            else:
                logger.info('No valid files for pgs plot')
                
        if any([arg in ['all','delphes'] for arg in args]):
            filename = pjoin(self.me_dir, 'Events','%s_delphes_events.lhco' % self.run_name)
            if os.path.exists(filename+'.gz'):
                os.system('gunzip -f %s' % (filename+'.gz') )
            if  os.path.exists(filename):
                #shutil.move(filename, pjoin(self.me_dir, 'Events','delphes_events.lhco'))
                self.create_plot('delphes')
                #shutil.move(pjoin(self.me_dir, 'Events','delphes_events.lhco'), filename)
                os.system('gzip -f %s' % filename)                
            else:
                logger.info('No valid files for delphes plot')

                
    
    def store_result(self):
        """ tar the pythia results. This is done when we are quite sure that 
        the pythia output will not be use anymore """


        if not self.run_name:
            return
        
        self.results.save()
        
        if not self.to_store:
            return 
        
        if 'pythia' in self.to_store:
            self.update_status('Storing Pythia files of Previous run', level='pythia')
            os.system('mv -f %(path)s/pythia_events.hep %(path)s/%(name)s_pythia_events.hep' % 
                  {'name': self.run_name, 'path' : pjoin(self.me_dir,'Events')})
            os.system('gzip -f %s/%s_pythia_events.hep' % ( 
                                    pjoin(self.me_dir,'Events'),self.run_name))
            self.to_store.remove('pythia')
            self.update_status('Done', level='pythia')
        
        self.to_store = []
            
        
    ############################################################################      
    def do_pgs(self, line):
        """launch pgs"""
        
        args = self.split_arg(line)
        # Check argument's validity
        if '-f' in args:
            force = True
            args.remove('-f')
        else:
            force = False
        if '--no_default' in args:
            no_default = True
            args.remove('--no_default')
        else:
            no_default = False
        self.update_status('prepare PGS run', level=None)
        self.check_pgs(args) 
        
        pgsdir = pjoin(self.configuration['pythia-pgs_path'], 'src')
        eradir = self.configuration['exrootanalysis_path']
        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']
        
        # Compile pgs if not there       
        if not misc.is_executable(pjoin(pgsdir, 'pgs')):
            logger.info('No PGS executable -- running make')
            misc.compile(cwd=pgsdir)
        
        # Check that the pgs_card exists. If not copy the default and
        # ask for edition of the card.
        if not os.path.exists(pjoin(self.me_dir, 'Cards', 'pgs_card.dat')):
            if no_default:
                logger.info('No pgs_card detected, so not run pgs')
                return 
            
            files.cp(pjoin(self.me_dir, 'Cards', 'pgs_card_default.dat'),
                     pjoin(self.me_dir, 'Cards', 'pgs_card.dat'))
            logger.info('No pgs card found. Take the default one.')
            
            if not force:
                answer = self.ask('Do you want to edit this card?','n', ['y','n'],
                              timeout=20)
            else:
                answer = 'n'
                
            if answer == 'y':
                misc.open_file(pjoin(self.me_dir, 'Cards', 'pgs_card.dat'))
        
        
        self.update_status('Running PGS', level='pgs')
        # now pass the event to a detector simulator and reconstruct objects

        # Update the banner with the pgs card
        banner_path = pjoin(self.me_dir,'Events',self.run_name + '_banner.txt')
        banner = open(banner_path, 'a')
        banner.writelines('\n<MGPGSCard>')
        banner.writelines(open(pjoin(self.me_dir, 'Cards','pgs_card.dat')).read())
        banner.writelines('</MGPGSCard>\n')
        banner.close()
        
        # Prepare the output file with the banner
        ff = open(pjoin(self.me_dir, 'Events', 'pgs_events.lhco'), 'w')
        text = open(banner_path).read()
        text = '#%s' % text.replace('\n','\n#')
        ff.writelines(text)
        ff.close()

        try: 
            os.remove(pjoin(self.me_dir, 'Events', 'pgs.done'))
        except:
            pass
        pgs_log = open(pjoin(self.me_dir, 'Events', "%s_pgs.log" % self.run_name),'w')
        if self.cluster_mode == 1:
            self.cluster.launch_and_wait('../bin/internal/run_pgs', 
                            argument=[pgsdir], cwd=pjoin(self.me_dir,'Events'),
                            stdout=pgs_log, stderr=subprocess.STDOUT)
        else:        
            subprocess.call([self.dirbin+'/run_pgs', pgsdir], stdout= pgs_log,
                                               stderr=subprocess.STDOUT,
                                               cwd=pjoin(self.me_dir, 'Events')) 
        
        if not os.path.exists(pjoin(self.me_dir, 'Events', 'pgs.done')):
            logger.error('Fail to create LHCO events')
            return 
        else:
            os.remove(pjoin(self.me_dir, 'Events', 'pgs.done'))
            
        if os.path.getsize(banner_path) == os.path.getsize(pjoin(self.me_dir, 'Events','pgs_events.lhco')):
            subprocess.call(['cat pgs_uncleaned_events.lhco >>  pgs_events.lhco'], 
                            cwd=pjoin(self.me_dir, 'Events'))

        # Creating Root file
        if misc.is_executable(pjoin(eradir, 'ExRootLHCOlympicsConverter')):
            self.update_status('Creating PGS Root File', level='pgs')
            subprocess.call([eradir+'/ExRootLHCOlympicsConverter', 
                             'pgs_events.lhco','%s_pgs_events.root' % self.run_name],
                            cwd=pjoin(self.me_dir, 'Events')) 
        
        if os.path.exists(pjoin(self.me_dir, 'Events', 'pgs_events.lhco')):
            files.mv(pjoin(self.me_dir, 'Events', 'pgs_events.lhco'), 
                    pjoin(self.me_dir, 'Events', '%s_pgs_events.lhco' % self.run_name))
            # Creating plots
            self.create_plot('PGS')
            subprocess.call(['gzip','-f', pjoin(self.me_dir, 'Events', '%s_pgs_events.lhco' % self.run_name)])


        
        self.update_status('finish', level='pgs', makehtml=False)

    ############################################################################
    def do_delphes(self, line):
        """ run delphes and make associate root file/plot """
 
        args = self.split_arg(line)
        # Check argument's validity
        if '-f' in args:
            force = True
            args.remove('-f')
        else:
            force = False
        if '--no_default' in args:
            no_default = True
            args.remove('--no_default')
        else:
            no_default = False
            
        self.update_status('prepare delphes run', level=None)
        self.check_pgs(args) 
        
        # Check that the delphes_card exists. If not copy the default and
        # ask for edition of the card.
        if not os.path.exists(pjoin(self.me_dir, 'Cards', 'delphes_card.dat')):
            if no_default:
                logger.info('No delphes_card detected, so not run Delphes')
                return
            
            files.cp(pjoin(self.me_dir, 'Cards', 'delphes_card_default.dat'),
                     pjoin(self.me_dir, 'Cards', 'delphes_card.dat'))
            logger.info('No delphes card found. Take the default one.')
            if not force:
                answer = self.ask('Do you want to edit this card?','n', ['y','n'],
                             timeout=20)
            else:
                answer = 'n'
                
            if answer == 'y':
                misc.open_file(pjoin(self.me_dir, 'Cards', 'delphes_card.dat')) 
 
        delphes_dir = self.configuration['delphes_path']
        self.update_status('Running Delphes', level='delphes')
        
        # Update the banner with the pgs card
        banner = open(pjoin(self.me_dir,'Events',self.run_name + '_banner.txt'), 'a')
        banner.writelines('<MGDelphesCard>')
        banner.writelines(open(pjoin(self.me_dir, 'Cards','delphes_card.dat')).read())
        banner.writelines('</MGDelphesCard>')
        banner.writelines('<MGDelphesTrigger>')
        banner.writelines(open(pjoin(self.me_dir, 'Cards','delphes_trigger.dat')).read())
        banner.writelines('</MGDelphesTrigger>')        
        banner.close()
        
        delphes_log = open(pjoin(self.me_dir, 'Events', "%s_delphes.log" % self.run_name),'w')
        if self.cluster_mode == 1:
            self.cluster.launch_and_wait('../bin/internal/run_delphes', 
                        argument= [delphes_dir, self.run_name],
                        stdout=delphes_log, stderr=subprocess.STDOUT,
                        cwd=pjoin(self.me_dir,'Events'))
        else:
            subprocess.call(['../bin/internal/run_delphes', delphes_dir, 
                                self.run_name],
                                stdout= delphes_log, stderr=subprocess.STDOUT,
                                cwd=pjoin(self.me_dir,'Events'))
                
        if not os.path.exists(pjoin(self.me_dir, 'Events', '%s_delphes_events.lhco' % self.run_name)):
            logger.error('Fail to create LHCO events from DELPHES')
            return 

        #eradir = self.configuration['exrootanalysis_path']
        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']

        # Creating plots
        self.create_plot('Delphes')

        if os.path.exists(pjoin(self.me_dir, 'Events', '%s_delphes_events.lhco' % self.run_name)):
            subprocess.call(['gzip', pjoin(self.me_dir, 'Events', '%s_delphes_events.lhco' % self.run_name)])


        
        self.update_status('delphes done', level='delphes', makehtml=False)   

    def launch_job(self,exe, cwd=None, stdout=None, argument = [], **opt):
        """ """
        argument = [str(arg) for arg in argument]
        
        def launch_in_thread(exe, arguement, cwd, stdout, control_thread):
            """ way to launch for multicore"""
            
            control_thread[0] += 1 # upate the number of running thread
            start = time.time()
            subprocess.call(['./'+exe] + argument, cwd=cwd, stdout=stdout,
                        stderr=subprocess.STDOUT, **opt)
            logger.info('%s run in %f s' % (exe, time.time() -start))
            
            # release the lock for allowing to launch the next job      
            while not control_thread[1].locked():
                # check that the status is locked to avoid coincidence unlock
                if not control_thread[2]:
                    # Main is not yet locked
                    control_thread[0] -= 1
                    return 
                time.sleep(1)
            control_thread[1].release()
            control_thread[0] -= 1 # upate the number of running thread
        
        
        if self.cluster_mode == 0:
            start = time.time()
            os.system('cd %s; ./%s' % (cwd,exe))
            #subprocess.call(['./'+exe] + argument, cwd=cwd, stdout=stdout, 
            #                bufsize=-1, **opt)
            logger.info('%s run in %f s' % (exe, time.time() -start))

        elif self.cluster_mode == 1:
            self.cluster.submit(exe, stdout=stdout, cwd=cwd)

        elif self.cluster_mode == 2:
            import thread
            if not hasattr(self, 'control_thread'):
                self.control_thread = [0] # [used_thread]
                self.control_thread.append(thread.allocate_lock()) # The lock
                self.control_thread.append(False) # True if all thread submit 
                                                  #-> waiting mode

            if self.control_thread[2]:
                self.control_thread[1].acquire()
                thread.start_new_thread(launch_in_thread,(exe, argument, cwd, stdout, self.control_thread))
            elif self.control_thread[0] <  self.nb_core -1:
                thread.start_new_thread(launch_in_thread,(exe, argument, cwd, stdout, self.control_thread))
            elif self.control_thread[0] ==  self.nb_core -1:
                thread.start_new_thread(launch_in_thread,(exe, argument, cwd, stdout, self.control_thread))
                self.control_thread[2] = True
                self.control_thread[1].acquire() # Lock the next submission
                                                 # Up to a release
            
    ############################################################################
    def find_madevent_mode(self):
        """Find if Madevent is in Group mode or not"""
        
        # The strategy is too look in the files Source/run_configs.inc
        # if we found: ChanPerJob=3 then it's a group mode.
        file_path = pjoin(self.me_dir, 'Source', 'run_config.inc')
        text = open(file_path).read()
        if re.search(r'''s*parameter\s+\(ChanPerJob=2\)''', text, re.I+re.M):
            return 'group'
        else:
            return 'v4'
    
    ############################################################################
    def monitor(self):
        """ monitor the progress of running job """
        
        if self.cluster_mode == 1:
            def update_status(idle, run, finish):
                self.update_status((idle, run, finish), level='parton')
            self.cluster.wait(self.me_dir, update_status)            
            #subprocess.call([pjoin(self.dirbin, 'monitor'), self.run_name], 
            #                                                    cwd=self.me_dir)
        if self.cluster_mode == 2:
            # Wait that all thread finish
            if not self.control_thread[2]:
                while self.control_thread[0]:
                    time.sleep(5)
            else:    
                for i in range(0,self.nb_core):
                    self.control_thread[1].acquire()
                self.control_thread[2] = False
                self.control_thread[1].release()
            
        
        proc = subprocess.Popen([pjoin(self.dirbin, 'sumall')], 
                                          cwd=pjoin(self.me_dir,'SubProcesses'),
                                          stdout=subprocess.PIPE)
        
        #tee = subprocess.Popen(['tee', '/tmp/tmp.log'], stdin=proc.stdout)
        (stdout, stderr) = proc.communicate()
        for line in stdout.split('\n'): 
            if line.startswith(' Results'):
                data = line.split()
                self.results.add_detail('cross', float(data[1]))
                self.results.add_detail('error', float(data[2]))                
        
    @staticmethod
    def find_available_run_name(me_dir):
        """ find a valid run_name for the current job """
        
        name = 'run_%02d'
        data = [int(s[4:6]) for s in os.listdir(pjoin(me_dir,'Events')) if
                        s.startswith('run_') and len(s)>5 and s[4:6].isdigit()]
        return name % (max(data+[0])+1) 

    ############################################################################   
    def configure_directory(self):
        """ All action require before any type of run """   


        # Basic check
        assert os.path.exists(pjoin(self.me_dir,'SubProcesses'))
        
        #see when the last file was modified
        time_mod = max([os.path.getctime(pjoin(self.me_dir,'Cards','run_card.dat')),
                        os.path.getctime(pjoin(self.me_dir,'Cards','param_card.dat'))])
        
        if self.configured > time_mod:
            return
        else:
            self.configured = time.time()

        # Change current working directory
        self.launching_dir = os.getcwd()
        os.chdir(self.me_dir)
        
        # Check if we need the MSSM special treatment
        model = self.find_model_name()
        if model == 'mssm' or model.startswith('mssm-'):
            param_card = pjoin(self.me_dir, 'Cards','param_card.dat')
            mg5_param = pjoin(self.me_dir, 'Source', 'MODEL', 'MG5_param.dat')
            check_param_card.convert_to_mg5card(param_card, mg5_param)
            check_param_card.check_valid_param_card(mg5_param)
        
        # limit the number of event to 100k
        self.check_nb_events()

        # set environment variable for lhapdf.
        if self.run_card['pdlabel'] == "'lhapdf'":
            os.environ['lhapdf'] = True
        elif 'lhapdf' in os.environ.keys():
            del os.environ['lhapdf']
        
        # Compile
        out = subprocess.call([pjoin(self.dirbin, 'compile_Source')],
                              cwd = self.me_dir)
        if out:
            raise MadEventError, 'Impossible to compile'
        
        # set random number
        if os.path.exists(pjoin(self.me_dir,'SubProcesses','randinit')):
            for line in open(pjoin(self.me_dir,'SubProcesses','randinit')):
                data = line.split('=')
                assert len(data) ==2
                self.random = int(data[1])
                break
        else:
            self.random = random.randint(1, 30107) # 30107 maximal allow 
                                                   # random number for ME
                                                   
        if self.run_card['ickkw'] == 2:
            logger.info('Running with CKKW matching')
            self.treat_CKKW_matching()
            
    ############################################################################
    ##  HELPING ROUTINE
    ############################################################################
    def read_run_card(self, run_card):
        """ """
        output={}
        for line in file(run_card,'r'):
            line = line.split('#')[0]
            line = line.split('!')[0]
            line = line.split('=')
            if len(line) != 2:
                continue
            output[line[1].strip()] = line[0].strip()
        return output

    ############################################################################
    @staticmethod
    def check_dir(path, default=''):
        """check if the directory exists. if so return the path otherwise the 
        default"""
         
        if os.path.isdir(path):
            return path
        else:
            return default
        
    ############################################################################
    def set_run_name(self, name, reload_card=False):
        """define the run name and update the results object"""
        
        if name == self.run_name:
            if reload_card:
                run_card = pjoin(self.me_dir, 'Cards','run_card.dat')
                self.run_card = self.read_run_card(run_card)
            return # Nothing to do
        
        # save/clean previous run
        if self.run_name:
            self.store_result()
        # store new name
        self.run_name = name
        
        # Read run_card
        run_card = pjoin(self.me_dir, 'Cards','run_card.dat')
        self.run_card = self.read_run_card(run_card)
        
        if name in self.results:
            self.results.def_current(self.run_name)
        else:
            self.results.add_run(self.run_name, self.run_card)
        
        
        
        
        
        

    ############################################################################
    def find_model_name(self):
        """ return the model name """
        if hasattr(self, 'model_name'):
            return self.model_name
        
        model = 'sm'
        proc = []
        for line in open(os.path.join(self.me_dir,'Cards','proc_card_mg5.dat')):
            line = line.split('#')[0]
            line = line.split('=')[0]
            if line.startswith('import') and 'model' in line:
                model = line.split()[2]   
                proc = []
            elif line.startswith('generate'):
                proc.append(line.split(None,1)[1])
            elif line.startswith('add process'):
                proc.append(line.split(None,2)[2])
       
        self.model = model
        self.process = proc 
        return model
    
    
    ############################################################################
    def check_nb_events(self):
        """Find the number of event in the run_card, and check that this is not 
        too large"""

        
        nb_event = int(self.run_card['nevents'])
        if nb_event > 100000:
            logger.warning("Attempting to generate more than 100K events")
            logger.warning("Limiting number to 100K. Use multi_run for larger statistics.")
            path = pjoin(self.me_dir, 'Cards', 'run_card.dat')
            os.system(r"""perl -p -i.bak -e "s/\d+\s*=\s*nevents/100000 = nevents/" %s""" \
                                                                         % path)
            self.run_card['nevents'] = 100000

        return

  
    ############################################################################    
    def update_random(self):
        """ change random number"""
        
        self.random += 5
        assert self.random < 31328*30081 # cann't use too big random number

    ############################################################################
    def save_random(self):
        """save random number in appropirate file"""
        
        fsock = open(pjoin(self.me_dir, 'SubProcesses','randinit'),'w')
        fsock.writelines('r=%s\n' % self.random)

    def do_quit(self, line):
        """ """

        try:
            os.remove(pjoin(self.me_dir,'RunWeb'))
        except:
            pass
        try:
            self.update_status('', level=None)
            self.store_result()
        except:
            # If nothing runs they they are no result to update
            pass
        os.system('%s/gen_cardhtml-pl' % (self.dirbin))

        return super(MadEventCmd, self).do_quit(line)
    
    # Aliases
    do_EOF = do_quit
    do_exit = do_quit
        
    ############################################################################
    def treat_ckkw_matching(self):
        """check for ckkw"""
        
        lpp1 = self.run_card['lpp1']
        lpp2 = self.run_card['lpp2']
        e1 = self.run_card['ebeam1']
        e2 = self.run_card['ebeam2']
        pd = self.run_card['pdlabel']
        lha = self.run_card['lhaid']
        xq = self.run_card['xqcut']
        translation = {'e1': e1, 'e2':e2, 'pd':pd, 
                       'lha':lha, 'xq':xq}

        if lpp1 or lpp2:
            # Remove ':s from pd          
            if pd.startswith("'"):
                pd = pd[1:]
            if pd.endswith("'"):
                pd = pd[:-1]                

            if xq >2 or xq ==2:
                xq = 2
            
            # find data file
            if pd == "lhapdf":
                issudfile = 'lib/issudgrid-%(e1)s-%(e2)s-%(pd)s-%(lha)s-%(xq)s.dat.gz'
            else:
                issudfile = 'lib/issudgrid-%(e1)s-%(e2)s-%(pd)s-%(xq)s.dat.gz'
            if self.web:
                issudfile = pjoin(self.webbin, issudfile % translation)
            else:
                issudfile = pjoin(self.me_dir, issudfile % translation)
            
            logger.info('Sudakov grid file: %s' % issudfile)
            
            # check that filepath exists
            if os.path.exists(issudfile):
                path = pjoin(self.me_dir, 'lib', 'issudgrid.dat')
                os.system('gunzip -fc %s > %s' % (issudfile, path))
            else:
                msg = 'No sudakov grid file for parameter choice. Start to generate it. This might take a while'
                self.update_status('GENERATE SUDAKOF GRID', level='parton')
                
                for i in range(-2,6):
                    self.launch_job('%s/gensudgrid ' % self.dirbin, 
                                    arguments = [i],
                                    cwd=self.me_dir, 
                                    stdout=open('gensudgrid%s.log' % s,'w'))
                self.monitor()
                for i in range(-2,6):
                    path = pjoin(self.me_dir, 'lib', 'issudgrid.dat')
                    os.system('cat gensudgrid%s.log >> %s' % (i, path))
                    os.system('gzip -fc %s > %s' % (path, issudfile))
                                     
    ############################################################################
    def create_root_file(self, input='unweighted_events.lhe', 
                                              output='unweighted_events.root' ):
        """create the LHE root file """
        self.update_status('Creating root files', level='parton')

        eradir = self.configuration['exrootanalysis_path']
        subprocess.call(['%s/ExRootLHEFConverter' % eradir, 
                             input, output],
                            cwd=pjoin(self.me_dir, 'Events'))
        
    ############################################################################
    def create_plot(self, mode='parton', event_path=None):
        """create the plot""" 

        madir = self.configuration['madanalysis_path']
        td = self.configuration['td_path']
        if not madir or not  td or \
            not os.path.exists(pjoin(self.me_dir, 'Cards', 'plot_card.dat')):
            return False
            
        if not event_path:
            if mode == 'parton':
                event_path = pjoin(self.me_dir, 'Events','unweighted_events.lhe')
            elif mode == 'pythia':
                event_path = pjoin(self.me_dir, 'Events','pythia_events.lhe')
            elif mode == 'pgs':
                event_path = pjoin(self.me_dir, 'Events', '%s_pgs_events.lhco' % self.run_name)
            elif mode == 'delphes':
                event_path = pjoin(self.me_dir, 'Events', '%s_delphes_events.lhco' % self.run_name)
            else:
                raise MadEvent5Error, 'Invalid mode %s' % mode
        if not os.path.exists(event_path):
            print 'not path', event_path
            return False
        
        self.update_status('Creating Plots for %s level' % mode, level = mode.lower())
               
        plot_dir = pjoin(self.me_dir, 'Events', self.run_name)
        
        addon = ''
        if mode != 'parton':
            addon = '_%s' % mode.lower()
            plot_dir += addon
        
        if not os.path.isdir(plot_dir):
            os.makedirs(plot_dir) 
        



        files.ln(pjoin(self.me_dir, 'Cards','plot_card.dat'), plot_dir, 'ma_card.dat')
        proc = subprocess.Popen([os.path.join(madir, 'plot_events')],
                            stdout = open(pjoin(plot_dir, 'plot.log'),'w'),
                            stderr = subprocess.STDOUT,
                            stdin=subprocess.PIPE,
                            cwd=plot_dir)
        proc.communicate('%s\n' % event_path)
        #proc.wait()
        subprocess.call(['%s/plot' % self.dirbin, madir, td],
                            stdout = open(pjoin(plot_dir, 'plot.log'),'a'),
                            stderr = subprocess.STDOUT,
                            cwd=plot_dir)

    
        subprocess.call(['%s/plot_page-pl' % self.dirbin, 
                                os.path.basename(plot_dir),
                                mode],
                            stdout = os.open(os.devnull, os.O_RDWR),
                            stderr = subprocess.STDOUT,
                            cwd=pjoin(self.me_dir, 'Events'))
       
        shutil.move(pjoin(self.me_dir, 'Events', 'plots.html'),
                   pjoin(self.me_dir, 'Events', '%s_plots%s.html' % 
                         (self.run_name, addon)) )
        
        self.update_status('End Plots for %s level' % mode, level = mode.lower(),
                                                                 makehtml=False)
        
        return True   

#===============================================================================
# MadEventCmd
#===============================================================================
class MadEventCmdShell(MadEventCmd, cmd.CmdShell):
    """The command line processor of MadGraph"""  


     
