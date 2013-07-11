from helpers import helpers
from robots.builder import Builder
import construction, math, pdb,variables

class Worker(Builder):
  def __init__(self,name,structure,location,program):
    super(Worker,self).__init__(name,structure,location,program)
    # The number of beams the robot is carrying (picked up at home now)
    self.num_beams = 0

    # Smaller number gives higher priority
    self.memory['dir_priority'] = [1,1,0]

    # Move further in the x-direction?
    self.memory['pos_x'] = None

    # Move further in the y-direction?
    self.memory['pos_y'] = None

  def __at_top(self):
    '''
    Returns if we really are at the top, in which case build
    '''
    if self.beam is not None:
      for endpoint in self.beam.endpoints:
        if helpers.compare(helpers.distance(self.location,endpoint),0):
          return True

    return False

  def current_state(self):
    '''
    Returns current state of robot
    '''
    state = super(Worker,self).current_state()
    return state

  def discard_beams(self,num = 1):
    '''
    Adding ability to change memory
    '''
    super(Worker,self).discard_beams(num)
    if self.num_beams == 0:
      self.memory['pos_z'] = False

  def pickup_beams(self,num = variables.beam_capacity):
    '''
    Adding ability to change memory
    '''
    super(Worker,self).pickup_beams(num)
    self.memory['pos_z'] = True

  def filter_directions(self,dirs):
    '''
    Filters the available directions and returns those that move us in the 
    desired direction. Overwritten to take into account the directions in
    which we want to move. When climbing down, it will take the steepest path.
    '''
    def bool_fun(string):
      '''
      Returns the correct funtion depending on the information stored in memory
      '''
      if self.memory[string]:
        return (lambda a : a > 0)
      elif self.memory[string] is not None:
        return (lambda a : a < 0)
      else:
        return (lambda a : True)

    # direction functions
    funs = [bool_fun('pos_x'), bool_fun('pos_y'), bool_fun('pos_z')]

    directions =  self.filter_dict(dirs, {}, funs)

    return directions

  def pick_direction(self,directions):
    '''
    Overwritting to pick the direction of steepest descent when climbing down
    instead of just picking a direction randomly
    '''
    def min_dir(vs):
      unit_list = [helpers.make_unit(v) for v in vs]
      min_val = min(unit_list,key=lambda t : t[2])
      index = unit_list.index(min_val)
      return index,min_val
    # Pick the largest pos_z if moving down
    if not self.memory['pos_z']:
      beam, (index, unit_dir) = min([(n, min_dir(vs)) for n,vs in directions.items()],
        key=lambda t : t[1][1][2])
      return (beam, directions[beam][index])

    # Randomly moving about along whatever directions are available
    else:
      return super(Worker,self).pick_direction(directions)

  def no_available_directions(self):
    '''
    We construct if we truly are at the top of a beam
    '''
    if self.num_beams > 0 and self.__at_top():
      self.start_construction = True
      self.memory['broken'] = []

  def basic_rules(self):
    '''
    Decides whether to build or not. Uses some relatively simple rules to decide.
    Here is the basic logic it is following.
    1.  a)  If we are at the top of a beam
        OR
        b)  i)  We are at the specified construction site
            AND
            ii) There is no beginning tube
    AND
    2.  Did not build in the previous timestep
    AND
    3.  Still carrying construction material
    '''

    if (((self.at_site() and not self.structure.started)) and not 
      self.memory['built'] and 
      self.num_beams > 0):

      self.structure.started = True
      self.memory['built'] = True
      return True
    else:
      self.memory['built'] = False
      return False

  def local_rules(self):
    '''
    Uses the information from SAP2000 to decide what needs to be done. This 
    funtion returns true if we should construct, and return false otherwise.
    Also calls the function start_repair in case a repair is necessary
    '''
    # If the program is not locked, there are no analysis results so True
    if not self.model.GetModelIsLocked():
      return False

    # Analysis results available
    else:
      return False

  def construct(self):
    '''
    Decides whether the robot should construct or not based on some local rules.
    '''
    return self.basic_rules() or self.local_rules()