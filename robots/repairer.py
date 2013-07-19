from helpers import helpers
from robots.worker import Worker
import construction, math, pdb,variables, random

class DumbRepairer(Worker):
  def __init__(self,name,structure,location,program):
    super(DumbRepairer,self).__init__(name,structure,location,program)
    # Number of steps we spend searching for a support beam once we encounter a
    # new beam
    self.memory['new_beam_steps'] = 0

    # Stores name of beam to be reinforced (so we know when we're no longer on it)
    self.memory['broken_beam_name'] = ''

    # Stores the previous beam we were on
    self.memory['previous_beam'] = None

    # Constains repair data so we can write it out to file in main.py
    self.repair_data = ''

    # We are searching for a support beam (done and done)
    self.search_mode = True

  def current_state(self):
    state = super(DumbRepairer,self).current_state()
    state.update({  'search_mode' : self.search_mode})
    return state

  def repairing(self):
    '''
    This is run when repairing, so as to set the right values when filtering and
    when picking directions
    '''
    # If we are at a joint, we might move up but MUST move in right x and y
    if self.at_joint():
      self.memory['pos_z'] = True
      self.memory['dir_priority'] = [1,1,1]
    else:
      self.memory['pos_z'] = False
      self.memory['dir_priority'] = [1,1,0]

  def construction_mode(self):
    '''
    Resets the robot to go back into construction mode (leaves some variables
     - such as the repair_beam_direction and the broken_beam_name available)
    '''
    self.memory['new_beam_steps'] = 0
    self.memory['previous_beam'] = None
    self.memory['pos_z'] = True
    self.memory['pos_y'] = None
    self.memory['pos_x'] = None
    self.memory['dir_priority'] = [1,1,0]
    self.repair_mode = False
    self.search_mode = False

  def add_support_mode(self):
    '''
    Sets up the construction of a support beam
    '''
    # Return to construct mode
    self.construction_mode()

    # But specify steps, and that we need to construct a support
    self.memory['broken'] = []
    self.memory['new_beam_steps'] = 1
    self.memory['construct_support'] = True

  def ground_support(self):
    '''
    Looks for a support from the ground
    '''
    if self.memory['new_beam_steps'] == 0:
      self.add_support_mode()
      self.ground_direction = helpers.scale(-1,self.ground_direction)

    self.memory['new_beam_steps'] -= 1

  def find_support(self):
    '''
    Looks for a support beam on the structure
    '''
    # We did not find a beam in the number of steps we wanted (go back to build
    # mode, but with the condition to build in exactly one timestep)
    if self.memory['new_beam_steps'] == 0:
      self.add_support_mode()

    self.memory['new_beam_steps'] -= 1


  def decide(self):
    '''
    Overwritting to allow for repair work to take place
    '''
    # Repair Mode
    if self.repair_mode:
      self.pre_decision()

      # We have moved off the structure entirely, so wander
      if self.beam is None:
        self.ground_support()

      # We've moved off the beam, so run the search support routine
      elif (self.memory['broken_beam_name'] != self.beam.name and 
        self.search_mode):
        if self.memory['previous_beam'] is None:
          self.memory['previous_beam'] = self.beam.name

        # We have found a support beam, so return to construct mode
        if self.memory['previous_beam'] != self.beam.name:
          self.construction_mode()

        self.find_support()

        # Move (don't check construction)
        self.movable_decide()

      # Simply move
      else:
        self.movable_decide()

    # Build Mode
    else:
      super(DumbRepairer,self).decide()

  def no_available_direction(self):
    '''
    No direction takes us where we want to go, so check to see if we need to 
      a) Construct
      b) Repair
    '''
    # Initialize repair mode if there are broken beams (and you can fix)
    if self.memory['broken'] != [] and self.num_beams > 0:
      beam, moment = max(self.memory['broken'],key=lambda t : t[1])
      string = "{} is starting repair of beam {} which has moment {} at {}".format(
        self.name,beam.name,str(moment),str(self.location))
      print(string)
      self.repair_data = string
      
      # Uncomment when ready!
      self.start_repair(beam)

    else:
      # Do parent's work
      super(DumbRepairer,self).no_available_direction()

  def start_repair(self,beam):
    '''
    Initializes the repair of the specified beam. Figures out which direction to
    travel in and stores it within the robot's memory, then tells it to climb
    down in a specific direction if necessary. Also sets the number of steps to
    climb down looking for a support beam.
    '''
    def set_dir(string,coord):
      '''
      Figures out what pos_var should be in order to travel in that direction
      '''
      if helpers.compare(coord,0):
        self.memory[string] = None
      if coord > 0:
        self.memory[string] = True
      else:
        self.memory[string] = False

    # Calculate direction of repair (check 0 dist, which means it is perfectly
    # vertical!)
    j = beam.endpoints.j
    # This is the xy-change, basically
    direction = helpers.make_vector(self.location,(j[0],j[1],self.location[2]))
    # Check to make sure the direction is non-zero. 
    non_zero = not helpers.compare(helpers.length(direction),0)

    # If it is zero-length, then store (0,0,1) as direction. Otherwise, give a 
    # 180 degree approace
    direction = helpers.make_unit(direction) if non_zero else (0,0,1)
    disturbance = helpers.make_unit((random.randint(-10,10),random.randint(-10,
      10),0))
    direction = helpers.make_unit(helpers.sum_vectors(disturbance,direction))
    self.memory['repair_beam_direction'] = direction

    # If vertical, give None so that it can choose a random direction. Otherwise,
    # pick a direction which within 180 degrees of the beam
    self.ground_direction = direction if non_zero else None
    
    # We want to climb down, and travel in 'direction' if possible
    set_dir('pos_x',direction[0])
    set_dir('pos_y',direction[1])
    self.memory['pos_z'] = False

    # Store name of repair beam
    self.memory['broken_beam_name'] = beam.name

    # Number of steps to search once we find a new beam that is close to
    # parallel to the beam we are repairing (going down, ie NOT support beam)
    length = construction.beam['length'] * math.cos(
      math.radians(construction.beam['support_angle']))
    self.memory['new_beam_steps'] = math.floor(length/variables.step_length)+1

    self.repair_mode = True
    self.search_mode = True

  def local_rules(self):
    '''
    Overriding so we can build support beam
    '''
    # If the program is not locked, there are no analysis results so True
    if not self.model.GetModelIsLocked():
      return False

    # Analysis results available
    elif self.memory['new_beam_steps'] == 0 and self.memory['construct_support']:
      return True
    
    return False

class Repairer(DumbRepairer):
  def __init__(self,name,structure,location,program):
    super(Repairer,self).__init__(name,structure,location,program)

    # Robots have a tendency to return to the previous area of repair
    self.memory['ground_tendencies'] = [None,None,None]

  

  def get_disturbance(self):
    '''
    Returns the disturbance level for adding a new beam at the tip. This is
    modified so that the disturbance compensates for the angle at which the
    current beam lies (using basic math)
    '''
    # TODO
    return super(Repairer,self).get_disturbance()

  def support_beam_endpoint(self):
    # If the broken beam has one endpoint on the ground
    e1,e2 = self.structure.get_endpoints(self.memory['broken_beam_name'],
      self.location)
    if helpers.compare(e1[2],0) or helpers.compare(e2[1],0):
      # Cycle through ratios looking for one that lies on the beam we want
      min_support_ratio, max_support_ratio = self.get_ratios()
      pivot = self.location
      vertical_endpoint = helpers.sum_vectors(pivot,helpers.scale(
        variables.beam_length,
        helpers.make_unit(construction.beam['vertical_dir_set'])))
      ratios = self.local_ratios(pivot,vertical_endpoint)
      for coord,ratio in ratios:
        if (helpers.on_line(e1,e2,coord) and min_support_ratio < ratio and 
        ration < max_support_ratio):
          return coord

    # Otherwise, do default behaviour
    return super(Repairer,self).support_beam_endpoint()