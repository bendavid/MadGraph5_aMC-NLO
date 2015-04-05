from __future__ import division
import collections
import random
import re
import math
import time


if '__main__' == __name__:
    import sys
    sys.path.append('../../')
import misc
import logging
import gzip
logger = logging.getLogger("madgraph.lhe_parser")

class Particle(object):
    """ """
    pattern=re.compile(r'''^\s*
        (?P<pid>-?\d+)\s+           #PID
        (?P<status>-?\d+)\s+            #status (1 for output particle)
        (?P<mother1>-?\d+)\s+       #mother
        (?P<mother2>-?\d+)\s+       #mother
        (?P<color1>[+-e.\d]*)\s+    #color1
        (?P<color2>[+-e.\d]*)\s+    #color2
        (?P<px>[+-e.\d]*)\s+        #px
        (?P<py>[+-e.\d]*)\s+        #py
        (?P<pz>[+-e.\d]*)\s+        #pz
        (?P<E>[+-e.\d]*)\s+         #E
        (?P<mass>[+-e.\d]*)\s+      #mass
        (?P<vtim>[+-e.\d]*)\s+      #displace vertex
        (?P<helicity>[+-e.\d]*)\s*      #helicity
        ($|(?P<comment>\#[\d|D]*))  #comment/end of string
        ''',66) #verbose+ignore case
    
    
    
    def __init__(self, line=None, event=None):
        """ """
        
        if isinstance(line, Particle):
            for key in line.__dict__:
                setattr(self, key, getattr(line, key))
            if event:
                self.event = event
            return
        
        self.event = event
        self.event_id = len(event) #not yet in the event
        # LHE information
        self.pid = 0
        self.status = 0
        self.mother1 = None
        self.mother2 = None
        self.color1 = 0
        self.color2 = None
        self.px = 0
        self.py = 0 
        self.pz = 0
        self.E = 0
        self.mass = 0
        self.vtim = 0
        self.helicity = 9
        self.comment = ''

        if line:
            self.parse(line)
            
    def parse(self, line):
        """parse the line"""
    
        obj = self.pattern.search(line)
        if not obj:
            raise Exception, 'the line\n%s\n is not a valid format for LHE particle' % line
        for key, value in obj.groupdict().items():
            if key not in  ['comment','pid']:
                setattr(self, key, float(value))
            elif key in ['pid']:
                setattr(self, key, int(value))
            else:
                self.comment = value
        # assign the mother:
        if self.mother1:
            try:
                self.mother1 = self.event[int(self.mother1) -1]
            except KeyError:
                raise Exception, 'Wrong Events format: a daughter appears before it\'s mother'
        if self.mother2:
            try:
                self.mother2 = self.event[int(self.mother2) -1]
            except KeyError:
                raise Exception, 'Wrong Events format: a daughter appears before it\'s mother'
    
    
    
    
    def __str__(self):
        """string representing the particles"""
        return " %8d %2d %4d %4d %4d %4d %+13.7e %+13.7e %+13.7e %14.8e %14.8e %10.4e %10.4e" \
            % (self.pid, 
               self.status,
               self.mother1.event_id+1 if self.mother1 else 0,
               self.mother2.event_id+1 if self.mother2 else 0,
               self.color1,
               self.color2,
               self.px,
               self.py,
               self.pz,
               self.E, 
               self.mass,
               self.vtim,
               self.helicity)
            
    def __eq__(self, other):

        if not isinstance(other, Particle):
            return False        
        if self.pid == other.pid and \
           self.status == other.status and \
           self.mother1 == other.mother1 and \
           self.mother2 == other.mother2 and \
           self.color1 == other.color1 and \
           self.color2 == other.color2 and \
           self.px == other.px and \
           self.py == other.py and \
           self.pz == other.pz and \
           self.E == other.E and \
           self.mass == other.mass and \
           self.vtim == other.vtim and \
           self.helicity == other.helicity:
            return True
        return False
        
    def set_momentum(self, momentum):
        
        self.E = momentum.E
        self.px = momentum.px 
        self.py = momentum.py
        self.pz = momentum.pz

    def add_decay(self, decay_event):
        """associate to this particle the decay in the associate event"""
        
        return self.event.add_decay_to_particle(self.event_id, decay_event)
            
    def __repr__(self):
        return 'Particle("%s", event=%s)' % (str(self), self.event)


class EventFile(object):
    """A class to allow to read both gzip and not gzip file"""

    def __new__(self, path, mode='r', *args, **opt):

        if path.endswith(".gz"):
            return gzip.GzipFile.__new__(EventFileGzip, path, mode, *args, **opt)
        else:
            return file.__new__(EventFileNoGzip, path, mode, *args, **opt)
    
    def __init__(self, path, mode='r', *args, **opt):
        """open file and read the banner [if in read mode]"""
        
        super(EventFile, self).__init__(path, mode, *args, **opt)
        self.banner = ''
        if mode == 'r':
            line = ''
            while '</init>' not in line.lower():
                try:
                    line  = super(EventFile, self).next()
                except StopIteration:
                    self.seek(0)
                    self.banner = ''
                    break 
                if "<event>" in line.lower():
                    self.seek(0)
                    self.banner = ''
                    break                     

                self.banner += line

    def get_banner(self):
        """return a banner object"""
        import madgraph.various.banner as banner
        output = banner.Banner()
        output.read_banner(self.banner.split('\n'))
        return output
    
    
    def next(self):
        """get next event"""
        text = ''
        line = ''
        mode = 0
        while '</event>' not in line:
            line = super(EventFile, self).next().lower()
            if '<event' in line:
                mode = 1
                text = ''
            if mode:
                text += line
        return Event(text)
    
    def unweight(self, outputpath, wgt, max_wgt=0, trunc_error=0, event_target=0, 
                 log_level=logging.DEBUG):
        """unweight the current file according to wgt information wgt.
        which can either be a fct of the event or a tag in the rwgt list.
        max_wgt allow to do partial unweighting. 
        trunc_error allow for dynamical partial unweighting
        event_target reweight for that many event with maximal trunc_error.
        (stop to write event when target is reached)
        """
        
        if isinstance(wgt, str):
            unwgt_name =wgt 
            def get_wgt(event):
                event.parse_reweight()
                return event.reweight_data[unwgt_name]
        else:
            unwgt_name = wgt.func_name
            get_wgt = wgt
                    
        # We need to loop over the event file to get some information about the 
        # new cross-section/ wgt of event.
        all_wgt = []
        cross = collections.defaultdict(int)
        nb_event = 0
        for event in self:
            nb_event +=1
            wgt = get_wgt(event)
            cross['all'] += wgt
            cross[event.ievent] += wgt
            all_wgt.append(abs(wgt))
            # avoid all_wgt to be too large
            if nb_event % 5000 == 0:
                all_wgt.sort()
                # drop the lowest weight
                nb_keep = max(1, int(nb_event*trunc_error))
                all_wgt = all_wgt[-nb_keep:]
        
        #final selection of the interesting weight to keep
        all_wgt.sort()
        # drop the lowest weight
        nb_keep = max(1, int(nb_event*trunc_error))
        all_wgt = all_wgt[-nb_keep:]        
        
        def max_wgt_for_trunc(trunc):
            """find the weight with the maximal truncation."""
            
            xsum = 0
            i=1
            while (xsum - all_wgt[-i] * (i-1) <= cross['all'] * trunc):
                max_wgt = all_wgt[-i]
                xsum += all_wgt[-i]
                i +=1
                if i == len(all_wgt):
                    break
            print i, all_wgt[-i], xsum - all_wgt[-i] * (i-1), cross['all'] * trunc
            return max_wgt
                
        # choose the max_weight
        if not max_wgt:
            if trunc_error == 0 or len(all_wgt)<2 or event_target:
                max_wgt = all_wgt[-1]
            else:
                max_wgt = max_wgt_for_trunc(trunc_error)

        # need to modify the banner so load it to an object
        if self.banner:
            banner = self.get_banner()
            # 1. modify the cross-section
            banner.modify_init_cross(cross)
            strategy = banner.get_lha_strategy()
            # 2. modify the lha strategy
            if strategy >0:  
                banner.set_lha_strategy(4)
            else:
                banner.set_lha_strategy(-4)
            # 3. add information about change in weight
            banner["unweight"] = "unweighted by %s" % unwgt_name
        
        # Do the reweighting (up to 20 times if we have target_event)
        nb_try = 20
        for i in range(nb_try):
            self.seek(0)
            outfile = EventFile(outputpath, "w")
            # need to write banner information
            # need to see what to do with rwgt information!
            if self.banner:
                banner.write(outfile)
                        
            if event_target:
                if i==0:
                    max_wgt = max_wgt_for_trunc(trunc_error*i/nb_try)
                else:
                    #guess the correct max_wgt based on last iteration
                    efficiency = nb_keep/nb_event
                    needed_efficiency = event_target/nb_event
                    last_max_wgt = max_wgt
                    needed_max_wgt = last_max_wgt * efficiency / needed_efficiency
                    min_max_wgt = max_wgt_for_trunc(trunc_error)
                    max_wgt = max(min_max_wgt, needed_max_wgt)
                    if max_wgt == last_max_wgt:
                        logger.warning("fail to reach target")
                        break
                    
                logger.log(log_level, "Max_wgt use is %s", max_wgt)
            
            # scan the file
            nb_keep = 0
            for event in self:
                r = random.random()
                wgt = get_wgt(event)
                if abs(wgt) < r * max_wgt:
                    continue
                elif wgt > 0:
                    nb_keep += 1
                    event.wgt = max(event.wgt, max_wgt)
                    outfile.write(str(event))
                elif wgt < 0:
                    nb_keep += 1
                    event.wgt = -1 * max(event.wgt, max_wgt)
                    outfile.write(event)
            
            if nb_keep >= event_target:
                if event_target and i != nb_try-1 and nb_keep >= event_target *1.05:
                    outfile.close()
                    logger.log(log_level, "Found Too much event %s. Try to reduce truncation" % nb_keep)
                    continue
                else:
                    outfile.write("</LesHouchesEvents>\n")
                    outfile.close()
                    logger.log(log_level, "write %i event in %s (efficiency %s %%)" % 
                           (nb_keep, outputpath, nb_keep/nb_event/100))
                break
            else:
                outfile.close()
                logger.log(log_level, "Found only %s event. Reduce max_wgt" % nb_keep)
        else:
            # pass here if event_target > 0 and all the attempt fail.
            logger.warning("fail to reach target event")
        
    
class EventFileGzip(EventFile, gzip.GzipFile):
    """A way to read/write a gzipped lhef event"""
        
class EventFileNoGzip(EventFile, file):
    """A way to read a standard event file"""
    

           
class Event(list):
    """Class storing a single event information (list of particles + global information)"""

    def __init__(self, text=None):
        """The initialization of an empty Event (or one associate to a text file)"""
        list.__init__(self)
        
        # First line information
        self.nexternal = 0
        self.ievent = 0
        self.wgt = 0
        self.aqcd = 0 
        self.scale = 0
        self.aqed = 0
        self.aqcd = 0
        # Weight information
        self.tag = ''
        self.comment = ''
        self.reweight_data ={}
        
        if text:
            self.parse(text)
            
    def parse(self, text):
        """Take the input file and create the structured information"""
        
        text = re.sub(r'</?event>', '', text) # remove pointless tag
        status = 'first' 
        for line in text.split('\n'):
            line = line.strip()
            if not line: 
                continue
            if line.startswith('#'):
                self.comment += '%s\n' % line
                continue
            if 'first' == status:
                self.assign_scale_line(line)
                status = 'part' 
                continue
            
            if '<' in line:
                status = 'tag'
                
            if 'part' == status:
                self.append(Particle(line, event=self))
            else:
                self.tag += '%s\n' % line
                
    def parse_reweight(self):
        """Parse the re-weight information in order to return a dictionary
           {key: value}. If no group is define group should be '' """
        
        if self.reweight_data:
            return
        
        self.reweight_data = {}
        self.reweight_order = []
        start, stop = self.tag.find('<rwgt>'), self.tag.find('</rwgt>')
        if start != -1 != stop :
            pattern = re.compile(r'''<\s*wgt id=\'(?P<id>[^\']+)\'\s*>\s*(?P<val>[\ded+-.]*)\s*</wgt>''')
            data = pattern.findall(self.tag)
            try:
                self.reweight_data = dict([(pid, float(value)) for (pid, value) in data
                                           if not self.reweight_order.append(pid)])
                      # the if is to create the order file on the flight
            except ValueError, error:
                raise Exception, 'Event File has unvalid weight. %s' % error
            self.tag = self.tag[:start] + self.tag[stop+7:]


    def add_decay_to_particle(self, position, decay_event):
        """define the decay of the particle id by the event pass in argument"""
        
        this_particle = self[position]
        #change the status to internal particle
        this_particle.status = 2
        this_particle.helicity = 0
        
        # some usefull information
        decay_particle = decay_event[0]
        this_4mom = FourMomentum(this_particle)
        nb_part = len(self) #original number of particle
        
        thres = decay_particle.E*1e-10
        assert max(decay_particle.px, decay_particle.py, decay_particle.pz) < thres,\
            "not on rest particle %s %s %s %s" % (decay_particle.E, decay_particle.px,decay_particle.py,decay_particle.pz) 
        
        self.nexternal += decay_event.nexternal -1
        
        # add the particle with only handling the 4-momenta/mother
        # color information will be corrected later.
        for particle in decay_event[1:]:
            # duplicate particle to avoid border effect
            new_particle = Particle(particle, self)
            new_particle.event_id = len(self)
            self.append(new_particle)
            # compute and assign the new four_momenta
            new_momentum = this_4mom.boost(FourMomentum(new_particle))
            new_particle.set_momentum(new_momentum)
            # compute the new mother
            for tag in ['mother1', 'mother2']:
                mother = getattr(particle, tag)
                if isinstance(mother, Particle):
                    mother_id = getattr(particle, tag).event_id
                    if mother_id == 0:
                        setattr(new_particle, tag, this_particle)
                    else:
                        setattr(new_particle, tag, self[nb_part + mother_id -1]) 
                elif tag == "mother2" and isinstance(particle.mother1, Particle):
                    new_particle.mother2 = this_particle
                else:
                    print particle
            
        # Need to correct the color information of the particle
        # first find the first available color index
        max_color=501
        for particle in self[:nb_part]:
            max_color=max(max_color, particle.color1, particle.color2)
        
        # define a color mapping and assign it:
        color_mapping = {}
        color_mapping[decay_particle.color1] = this_particle.color1
        color_mapping[decay_particle.color2] = this_particle.color2
        for particle in self[nb_part:]:
            if particle.color1:
                if particle.color1 not in color_mapping:
                    max_color +=1
                    color_mapping[particle.color1] = max_color
                    particle.color1 = max_color
                else:
                    particle.color1 = color_mapping[particle.color1]
            if particle.color2:
                if particle.color2 not in color_mapping:
                    max_color +=1
                    color_mapping[particle.color2] = max_color
                    particle.color2 = max_color
                else:
                    particle.color2 = color_mapping[particle.color2]                

    def remove_decay(self, pdg_code=0, event_id=None):
        
        to_remove = []
        if event_id is not None:
            to_remove.append(self[event_id])
    
        if pdg_code:
            for particle in self:
                if particle.pid == pdg_code:
                    to_remove.append(particle) 
                    
        new_event = Event()
        # copy first line information + ...
        for tag in ['nexternal', 'ievent', 'wgt', 'aqcd', 'scale', 'aqed','tag','comment']:
            setattr(new_event, tag, getattr(self, tag))
            
        for particle in self:
            if isinstance(particle.mother1, Particle) and particle.mother1 in to_remove:
                to_remove.append(particle)
                if particle.status == 1:
                    new_event.nexternal -= 1
                continue
            elif isinstance(particle.mother2, Particle) and particle.mother2 in to_remove:
                to_remove.append(particle)
                if particle.status == 1:
                    new_event.nexternal -= 1
                continue
            else:
                new_event.append(Particle(particle))
                
        #ensure that the event_id is correct for all_particle
        # and put the status to 1 for removed particle
        for pos, particle in enumerate(new_event):
            particle.event_id = pos
            if particle in to_remove:
                particle.status = 1
                new_event.nexternal += 1
        return new_event

    def get_decay(self, pdg_code=0, event_id=None):
        
        to_start = []
        if event_id is not None:
            to_start.append(self[event_id])
    
        elif pdg_code:
            for particle in self:
                if particle.pid == pdg_code:
                    to_start.append(particle)
                    break 

        new_event = Event()
        # copy first line information + ...
        for tag in ['ievent', 'wgt', 'aqcd', 'scale', 'aqed','tag','comment']:
            setattr(new_event, tag, getattr(self, tag))
        
        # Add the decaying particle
        old2new = {}            
        new_decay_part = Particle(to_start[0])
        new_decay_part.mother1 = None
        new_decay_part.mother2 = None
        new_decay_part.status =  -1
        old2new[new_decay_part.event_id] = len(old2new) 
        new_event.append(new_decay_part)
        
        # add the other particle   
        for particle in self:
            if isinstance(particle.mother1, Particle) and particle.mother1.event_id in old2new\
            or isinstance(particle.mother2, Particle) and particle.mother2.event_id in old2new:
                old2new[particle.event_id] = len(old2new) 
                new_event.append(Particle(particle))

        #ensure that the event_id is correct for all_particle
        # and correct the mother1/mother2 by the new reference
        nexternal = 0
        for pos, particle in enumerate(new_event):
            particle.event_id = pos
            if particle.mother1:
                particle.mother1 = new_event[old2new[particle.mother1.event_id]]
            if particle.mother2:
                particle.mother2 = new_event[old2new[particle.mother2.event_id]]
            if particle.status in [-1,1]:
                nexternal +=1
        new_event.nexternal = nexternal
        
        return new_event

            
    def check(self):
        """check various property of the events"""
        
        #1. Check that the 4-momenta are conserved
        E, px, py, pz = 0,0,0,0
        absE, abspx, abspy, abspz = 0,0,0,0
        for particle in self:
            coeff = 1
            if particle.status == -1:
                coeff = -1
            elif particle.status != 1:
                continue
            E += coeff * particle.E
            absE += abs(particle.E)
            px += coeff * particle.px
            py += coeff * particle.py
            pz += coeff * particle.pz
            abspx += abs(particle.px)
            abspy += abs(particle.py)
            abspz += abs(particle.pz)
        # check that relative error is under control
        threshold = 5e-7
        if E/absE > threshold:
            logger.critical(self)
            raise Exception, "Do not conserve Energy %s, %s" % (E/absE, E)
        if px/abspx > threshold:
            logger.critical(self)
            raise Exception, "Do not conserve Px %s, %s" % (px/abspx, px)         
        if py/abspy > threshold:
            logger.critical(self)
            raise Exception, "Do not conserve Py %s, %s" % (py/abspy, py)
        if pz/abspz > threshold:
            logger.critical(self)
            raise Exception, "Do not conserve Pz %s, %s" % (pz/abspz, pz)
            
        #2. check the color of the event
        self.check_color_structure()            
         
    def assign_scale_line(self, line):
        """read the line corresponding to global event line
        format of the line is:
        Nexternal IEVENT WEIGHT SCALE AEW AS
        """
        inputs = line.split()
        assert len(inputs) == 6
        self.nexternal=int(inputs[0])
        self.ievent=int(inputs[1])
        self.wgt=float(inputs[2])
        self.scale=float(inputs[3])
        self.aqed=float(inputs[4])
        self.aqcd=float(inputs[5])
        
    def get_tag_and_order(self):
        """Return the unique tag identifying the SubProcesses for the generation.
        Usefull for program like MadSpin and Reweight module."""
        
        initial, final, order = [], [], [[], []]
        for particle in self:
            if particle.status == -1:
                initial.append(particle.pid)
                order[0].append(particle.pid)
            elif particle.status == 1: 
                final.append(particle.pid)
                order[1].append(particle.pid)
        initial.sort(), final.sort()
        tag = (tuple(initial), tuple(final))
        return tag, order
    
    def get_helicity(self, get_order, allow_reversed=True):
        """return a list with the helicities in the order asked for"""

        
        
        #avoid to modify the input
        order = [list(get_order[0]), list(get_order[1])] 
        out = [9] *(len(order[0])+len(order[1]))
        for i, part in enumerate(self):
            if part.status == 1: #final
                try:
                    ind = order[1].index(part.pid)
                except ValueError, error:
                    if not allow_reversed:
                        raise error
                    else:
                        order = [[-i for i in get_order[0]],[-i for i in get_order[1]]]
                        try:
                            return self.get_helicity(order, False)
                        except ValueError:
                            raise error     
                position = len(order[0]) + ind
                order[1][ind] = 0   
            elif part.status == -1:
                try:
                    ind = order[0].index(part.pid)
                except ValueError, error:
                    if not allow_reversed:
                        raise error
                    else:
                        order = [[-i for i in get_order[0]],[-i for i in get_order[1]]]
                        try:
                            return self.get_helicity(order, False)
                        except ValueError:
                            raise error
                 
                position =  ind
                order[0][ind] = 0
            else: #intermediate
                continue
            out[position] = int(part.helicity)
        return out  

    
    def check_color_structure(self):
        """check the validity of the color structure"""
        
        #1. check that each color is raised only once.
        color_index = collections.defaultdict(int)
        for particle in self:
            if particle.status in [-1,1]:
                if particle.color1:
                    color_index[particle.color1] +=1
                if particle.color2:
                    color_index[particle.color2] +=1     
                
        for key,value in color_index.items():
            if value > 2:
                print self
                print key, value
                raise Exception, 'Wrong color_flow'           
        
        #2. check that each parent present have coherent color-structure
        check = []
        popup_index = [] #check that the popup index are created in a unique way
        for particle in self:
            mothers = []
            childs = []
            if particle.mother1:
                mothers.append(particle.mother1)
            if particle.mother2 and particle.mother2 is not particle.mother1:
                mothers.append(particle.mother2)                 
            if not mothers:
                continue
            if (particle.mother1.event_id, particle.mother2.event_id) in check:
                continue
            check.append((particle.mother1.event_id, particle.mother2.event_id))
            
            childs = [p for p in self if p.mother1 is particle.mother1 and \
                                         p.mother2 is particle.mother2]
            
            mcolors = []
            manticolors = []
            for m in mothers:
                if m.color1:
                    if m.color1 in manticolors:
                        manticolors.remove(m.color1)
                    else:
                        mcolors.append(m.color1)
                if m.color2:
                    if m.color2 in mcolors:
                        mcolors.remove(m.color2)
                    else:
                        manticolors.append(m.color2)
            ccolors = []
            canticolors = []
            for m in childs:
                if m.color1:
                    if m.color1 in canticolors:
                        canticolors.remove(m.color1)
                    else:
                        ccolors.append(m.color1)
                if m.color2:
                    if m.color2 in ccolors:
                        ccolors.remove(m.color2)
                    else:
                        canticolors.append(m.color2)
            for index in mcolors[:]:
                if index in ccolors:
                    mcolors.remove(index)
                    ccolors.remove(index)
            for index in manticolors[:]:
                if index in canticolors:
                    manticolors.remove(index)
                    canticolors.remove(index)             
                        
            if mcolors != []:
                #only case is a epsilon_ijk structure.
                if len(canticolors) + len(mcolors) != 3:
                    logger.critical(str(self))
                    raise Exception, "Wrong color flow for %s -> %s" ([m.pid for m in mothers], [c.pid for c in childs])              
                else:
                    popup_index += canticolors
            elif manticolors != []:
                #only case is a epsilon_ijk structure.
                if len(ccolors) + len(manticolors) != 3:
                    logger.critical(str(self))
                    raise Exception, "Wrong color flow for %s -> %s" ([m.pid for m in mothers], [c.pid for c in childs])              
                else:
                    popup_index += ccolors

            # Check that color popup (from epsilon_ijk) are raised only once
            if len(popup_index) != len(set(popup_index)):
                logger.critical(self)
                raise Exception, "Wrong color flow: identical poping-up index, %s" % (popup_index)
               
    def __str__(self):
        """return a correctly formatted LHE event"""
                
        out="""<event>
%(scale)s
%(particles)s
%(comments)s
%(tag)s
%(reweight)s
</event>
""" 

        scale_str = "%2d %6d %+13.7e %14.8e %14.8e %14.8e" % \
            (self.nexternal,self.ievent,self.wgt,self.scale,self.aqed,self.aqcd)
        if self.reweight_data:
            # check that all key have an order if not add them at the end
            if set(self.reweight_data.keys()) != set(self.reweight_order):
                self.reweight_order += [k for k in self.reweight_data.keys() \
                                                if k not in self.reweight_order]
                
            reweight_str = '<rwgt>\n%s\n</rwgt>' % '\n'.join(
                        '<wgt id=\'%s\'> %+13.7e </wgt>' % (i, float(self.reweight_data[i]))
                        for i in self.reweight_order)
        else:
            reweight_str = '' 
        out = out % {'scale': scale_str, 
                      'particles': '\n'.join([str(p) for p in self]),
                      'tag': self.tag,
                      'comments': self.comment,
                      'reweight': reweight_str}
        return re.sub('[\n]+', '\n', out)
    
    def get_momenta_str(self, get_order, allow_reversed=True):
        """return the momenta str in the order asked for"""
        
        
        #avoid to modify the input
        order = [list(get_order[0]), list(get_order[1])] 
        out = [''] *(len(order[0])+len(order[1]))
        for i, part in enumerate(self):
            if part.status == 1: #final
                try:
                    ind = order[1].index(part.pid)
                except ValueError, error:
                    if not allow_reversed:
                        raise error
                    else:
                        order = [[-i for i in get_order[0]],[-i for i in get_order[1]]]
                        try:
                            return self.get_momenta_str(order, False)
                        except ValueError:
                            raise error     
                position = len(order[0]) + ind
                order[1][ind] = 0   
            elif part.status == -1:
                try:
                    ind = order[0].index(part.pid)
                except ValueError, error:
                    if not allow_reversed:
                        raise error
                    else:
                        order = [[-i for i in get_order[0]],[-i for i in get_order[1]]]
                        try:
                            return self.get_momenta_str(order, False)
                        except ValueError:
                            raise error
                 
                position =  ind
                order[0][ind] = 0
            else: #intermediate
                continue
            format = '%.12f'
            format_line = ' '.join([format]*4) + ' \n'
            out[position] = format_line % (part.E, part.px, part.py, part.pz)
            
        out = ''.join(out).replace('e','d')
        return out    


class FourMomentum(object):
    """a convenient object for 4-momenta operation"""
    
    def __init__(self, obj=0, px=0, py=0, pz=0, E=0):
        """initialize the four momenta"""

        if obj is 0 and E:
            obj = E
         
        if isinstance(obj, (FourMomentum, Particle)):
            px = obj.px
            py = obj.py
            pz = obj.pz
            E = obj.E
        else:
            E =obj

            
        self.E = E
        self.px = px
        self.py = py
        self.pz =pz
        
    @property
    def mass(self):
        """return the mass"""    
        return math.sqrt(self.E**2 - self.px**2 - self.py**2 - self.pz**2)

    @property
    def pt(self):
        return math.sqrt(max(0, self.pt2()))
    

    def mass_sqr(self):
        """return the mass square"""    
        return self.E**2 - self.px**2 - self.py**2 - self.pz**2
    
    def pt2(self):
        """ return the pt square """
        
        return  self.px**2 + self.py**2 + self.pz**2
    
    def __add__(self, obj):
        
        assert isinstance(obj, FourMomentum)
        new = FourMomentum(self.E+obj.E,
                           self.px + obj.px,
                           self.py + obj.py,
                           self.pz + obj.pz)
        return new
    
    def __iadd__(self, obj):
        """update the object with the sum"""
        self.E += obj.E
        self.px += obj.px
        self.py += obj.py
        self.pz += obj.pz
        return self
    
    def __pow__(self, power):
        assert power in [1,2]
        
        if power == 1:
            return FourMomentum(self)
        elif power == 2:
            return self.mass_sqr()
        
    def boost(self, mom):
        """mom 4-momenta is suppose to be given in the rest frame of this 4-momenta.
        the output is the 4-momenta in the frame of this 4-momenta
        function copied from HELAS routine."""

        
        pt = self.pt2()
        if pt:
            s3product = self.px * mom.px + self.py * mom.py + self.pz * mom.pz
            mass = self.mass()
            lf = (mom.E + (self.E - mass) * s3product / pt ) / mass
            return FourMomentum(E=(self.E*mom.E+s3product)/mass,
                           px=mom.px + self.px * lf,
                           py=mom.py + self.py * lf,
                           pz=mom.pz + self.pz * lf)
        else:
            return FourMomentum(mom)
                

if '__main__' == __name__:   
    
    # Example 1: adding some missing information to the event (here distance travelled)
    if False: 
        lhe = EventFile('unweighted_events.lhe')
        output = open('output_events.lhe', 'w')
        #write the banner to the output file
        output.write(lhe.banner)
        # Loop over all events
        for event in lhe:
            for particle in event:
                # modify particle attribute: here remove the mass
                particle.mass = 0
                particle.vtim = 2 # The one associate to distance travelled by the particle.
    
            #write this modify event
            output.write(str(event))
        output.write('</LesHouchesEvent>\n')
    
    # Example 2: Adding the decay of one particle (Bridge Method).
    if True:
        orig_lhe = EventFile('../../production.lhe')
        decay_lhe = EventFile('../../t_decay.lhe')
        output = open('../../production_t_decay.lhe', 'w')
        output.write(orig_lhe.banner) #need to be modified by hand!
        pid_to_decay  = 6 #which particle to decay
        bypassed_decay = {} # not yet use decay due to wrong helicity
        
        counter = 0
        start = time.time()
        for event in orig_lhe:
            if counter % 1000 == 1:
                print "decaying event number %s [%s s]" % (counter, time.time()-start)
            counter +=1
            for particle in event:
                if particle.pid == pid_to_decay:
                    #ok we have to decay this particle!
                    helicity = particle.helicity
                    # use the already parsed_event if any
                    done = False
                    if helicity in bypassed_decay and bypassed_decay[helicity]:
                        # use one of the already parsed (but not used) decay event
                        for decay in bypassed_decay[helicity]:
                            if decay[0].helicity == helicity:
                                particle.add_decay(decay)
                                bypassed_decay[helicity].remove(decay)
                                done = True
                                break
                    # read the decay event up to find one valid decay
                    while not done:
                        try:
                            decay = decay_lhe.next()
                        except StopIteration:
                            raise Exception, "not enoug event in the decay file"
                        
                        if helicity == decay[0].helicity or helicity==9:
                            particle.add_decay(decay)
                            done=True
                        elif decay[0].helicity in bypassed_decay:
                            if len(bypassed_decay[decay[0].helicity]) < 100:
                                bypassed_decay[decay[0].helicity].append(decay)
                            #limit to 100 to avoid huge increase of memory if only 
                            #one helicity is present in the production sample.
                        else:
                            bypassed_decay[decay[0].helicity] = [decay]

            output.write(str(event))
        output.write('</LesHouchesEvent>\n')
        
    # Example 3: Plotting some variable
    if False:
        lhe = EventFile('unweighted_events.lhe')
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        nbins = 100
        
        nb_pass = 0
        data = []
        for event in lhe:
            if nb_pass > 10000:
                break
            E=0
            for particle in event:
                if particle.status<0:
                    E+=particle.E

            event.parse_reweight()

            if 2 < event.reweight_data["mg_reweight_1"]/event.wgt:            
                data.append(event.reweight_data["mg_reweight_1"]/event.wgt)
                nb_pass +=1
            
        print nb_pass
        gs1 = gridspec.GridSpec(2, 1, height_ratios=[5,1])
        gs1.update(wspace=0, hspace=0) # set the spacing between axes. 
        ax = plt.subplot(gs1[0])
        
        n, bins, patches = ax.hist(data, nbins, histtype='step', label='original')
        ax_c = ax.twinx()
        ax_c.set_ylabel('MadGraph5_aMC@NLO')
        ax_c.yaxis.set_label_coords(1.01, 0.25)
        ax_c.set_yticks(ax.get_yticks())
        ax_c.set_yticklabels([])
        plt.axis('on')
        plt.xlabel('weight ratio')
        plt.show()


    # Example 4: More complex plotting example (with ratio plot)
    if False:
        lhe = EventFile('unweighted_events.lhe')
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        nbins = 100
        
        #mtau, wtau = 45, 5.1785e-06
        mtau, wtau = 1.777, 4.027000e-13
        nb_pass = 0
        data, data2, data3 = [], [], []
        for event in lhe:
            nb_pass +=1
            if nb_pass > 10000:
                break
            tau1 = FourMomentum()
            tau2 = FourMomentum()
            for part in event:
                if part.pid in [-12,11,16]:
                    momenta = FourMomentum(part)
                    tau1 += momenta
                elif part.pid == 15:
                    tau2 += FourMomentum(part)

            if abs((mtau-tau2.mass())/wtau)<1e6 and tau2.mass() >1:               
                data.append((tau1.mass()-mtau)/wtau)
                data2.append((tau2.mass()-mtau)/wtau)   
        gs1 = gridspec.GridSpec(2, 1, height_ratios=[5,1])
        gs1.update(wspace=0, hspace=0) # set the spacing between axes. 
        ax = plt.subplot(gs1[0])
        
        n, bins, patches = ax.hist(data2, nbins, histtype='step', label='original')
        n2, bins2, patches2 = ax.hist(data, bins=bins, histtype='step',label='reconstructed')
        import cmath
        
        breit = lambda m : math.sqrt(4*math.pi)*1/(((m)**2-mtau**2)**2+(mtau*wtau)**2)*wtau
        
        data3 = [breit(mtau + x*wtau)*wtau*16867622.6624*50 for x in bins]

        ax.plot(bins, data3,label='breit-wigner')
        # add the legend
        ax.legend()
        # add on the right program tag
        ax_c = ax.twinx()
        ax_c.set_ylabel('MadGraph5_aMC@NLO')
        ax_c.yaxis.set_label_coords(1.01, 0.25)
        ax_c.set_yticks(ax.get_yticks())
        ax_c.set_yticklabels([])
        
        plt.title('invariant mass of tau LHE/reconstructed')
        plt.axis('on')
        ax.set_xticklabels([])
        # ratio plot
        ax = plt.subplot(gs1[1])
        data4 = [n[i]/(data3[i]) for i in range(nbins)]
        ax.plot(bins, data4 + [0] , 'b')
        data4 = [n2[i]/(data3[i]) for i in range(nbins)]
        ax.plot(bins, data4 + [0] , 'g')
        ax.set_ylim([0,2])
        #remove last y tick to avoid overlap with above plot:
        tick = ax.get_yticks()
        ax.set_yticks(tick[:-1])
        
        
        plt.axis('on')
        plt.xlabel('(M - Mtau)/Wtau')                                                                                                                                 
        plt.show()

        

                            
                            
    
    
    

